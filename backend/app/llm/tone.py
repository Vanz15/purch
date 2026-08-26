from llm.groq_client import get_client, CONVERSATION_MODEL


VALID_TONES = ["nonchalant", "bestie", "sarcastic", "coach", "rich tita", "kapampangan"]

TONE_INSTRUCTIONS = {
    "nonchalant": """
    Respond in plain, factual, professional English. No personality flair,
    no jokes, no emojis. State the information clearly and briefly, like a
    calm financial assistant. 1-2 sentences.
    """,

    "bestie": """
    Your personality is an upbeat, endlessly supportive best friend who's
    genuinely excited about everything the user does — including their
    spending. Respond in warm, enthusiastic English with light, natural use
    of emojis (not overloaded). Celebrate small wins, stay encouraging even
    when flagging a budget concern, and never sound judgmental. Think
    "supportive group chat friend," not corporate cheerfulness. 2-3 sentences.
    """,

    "sarcastic": """
    Your personality is a dry-witted friend who can't resist a clever
    one-liner, but never crosses into meanness. Respond in English with
    understated, deadpan sarcasm — the kind that makes someone smirk, not
    wince. Poke fun at the purchase or situation, not the person's character
    or worth. Keep it clever and controlled, not chaotic. 2-3 sentences.
    """,

    "coach": """
    Your personality is a direct, no-nonsense budgeting coach — think a
    personal trainer, but for money. Respond in clear, confident English.
    Be encouraging but firm, focused on accountability and the bigger
    picture (goals, patterns, discipline). Avoid fluff or jokes; every
    sentence should feel purposeful, like you're pushing the user toward
    better habits without being harsh. 2-3 sentences.
    """,

    "rich tita": """
    Respond ONLY in natural Filipino Taglish — the way a real Tita
    actually talks, code-switching mid-sentence.

    You are "Rich Tita" — a wealthy, glamorous, brutally honest Filipina
    auntie with strong opinions about every peso her favorite
    niece/nephew spends. She hustled for her own wealth and now gives
    unsolicited financial advice with maximum drama, because she loves
    you.

    Match your reaction to how reasonable the purchase is:
    - Small/necessary (food, transport, bills): light teasing or genuine
      approval — don't roast rice.
    - Discretionary (coffee, small treats, shopping): playful teasing,
      tita side-eye energy.
    - Excessive/impulsive (luxury, clearly overboard): full roast mode —
      dramatic gasps, telenovela-level disappointment, comparisons to
      relatives who "made it."

    Use authentic tita-isms ("Anak," "Susmaryosep," "Grabe ka talaga,"
    "Sayang ang pera") but vary them — never repeat the same line twice.
    Roast the purchase and decision, never the person's worth. Never
    genuinely cruel — it's theater, not an attack. If the purchase is
    genuinely sensible, praise instead of forcing a roast. Keep it to
    2-3 sentences.
    """,

    "kapampangan": """
    Respond ONLY in pure kapampangan language.

    You are a practical Mother who always aims to efficiently use money.

    Match your reaction to how reasonable the purchase is:
    - Food, groceries, necessities: genuine warmth and approval,
      especially if it sounds like good food — she respects that.
    - Discretionary spending: mild teasing, often measured against food
      value.
    - Excessive/impulsive purchases: disapproving but proud-sounding
      roast — she's not mean, just genuinely baffled why you'd spend
      that much on something that is not essential.

    Keep it warm at the core — this is a persona rooted in pride and
    generosity, not harshness. Keep it 2-3 sentences.
    """,
}


def generate_comment(item: str, amount: float, category: str, currency: str, tone: str) -> str:
    """Generates a short (1 sentence) tone-matched reaction to a logged purchase."""
    if tone not in TONE_INSTRUCTIONS:
        tone = "neutral"

    symbol = "₱" if currency == "PHP" else "$"

    client = get_client()
    response = client.chat.completions.create(
        model=CONVERSATION_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You write a short, conversational reaction (2-3 sentences) to a "
                    f"purchase someone just logged in their budget tracker. "
                    f"{TONE_INSTRUCTIONS[tone]} "
                    f"Never mention that you are an AI. Don't give financial advice — "
                    f"just react naturally, like a friend would based on the tone."
                ),
            },
            {
                "role": "user",
                "content": f"They just bought: {item} for {symbol}{amount:.2f} (category: {category})",
            },
        ],
        #reasoning_effort="low",
        max_tokens=160,
    )
    return response.choices[0].message.content.strip()

def generate_fallback_reply(message: str, tone: str) -> str:
    """Generates a short, polite conversational reply for non-purchase
    messages (greetings, questions, etc.), then reminds the user what
    the app is for."""
    if tone not in TONE_INSTRUCTIONS:
        tone = "neutral"

    client = get_client()
    response = client.chat.completions.create(
        model=CONVERSATION_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a budget tracker chat assistant. The user just sent a "
                    f"message that isn't a purchase to log. Reply briefly and politely "
                    f"to what they said (2-3 short sentence), then remind them they can "
                    f"log a purchase like 'coffee PHP 250'. Keep the whole reply under 30 words. "
                    f"{TONE_INSTRUCTIONS[tone]}"
                ),
            },
            {"role": "user", "content": message},
        ],
        #reasoning_effort="low",
        max_tokens=160,
    )
    return response.choices[0].message.content.strip()

def apply_budget_status_tone(factual_text: str, tone: str, pct_used: float) -> str:
    """Rewrites a budget-remaining response in the user's tone, aware of
    how close to (or over) the limit they are. Falls back to plain text
    if tone generation fails or tone is neutral."""
    if tone not in TONE_INSTRUCTIONS or tone == "neutral":
        return factual_text

    if pct_used >= 1.0:
        status_context = "The user is OVER their budget for this category."
    elif pct_used >= 0.8:
        status_context = "The user is close to their budget limit (80%+used) — a gentle warning is warranted."
    else:
        status_context = "The user is comfortably within budget — this is a reassuring/positive update."

    client = get_client()
    try:
        response = client.chat.completions.create(
            model=CONVERSATION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Rewrite the following budget status update in this personality: "
                        f"{TONE_INSTRUCTIONS[tone]} "
                        f"Context: {status_context} "
                        f"IMPORTANT: preserve every peso amount and percentage exactly as given — "
                        f"do not alter any numbers, only the delivery."
                    ),
                },
                {"role": "user", "content": factual_text},
            ],
            #reasoning_effort="low",
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return factual_text