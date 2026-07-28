"""Shared theme primitives for the Purch Reflex shell.

Python-side aliases for the CSS custom properties defined in
`assets/purch_theme.css`. Components reference palette tokens by name
(e.g. `COLORS['coral']`) instead of hard-coding hex values, so any future
palette change lives in one file plus the CSS.
"""

# Espresso + Coral palette (kept in sync with assets/purch_theme.css)
COLORS: dict[str, str] = {
    "dark": "#1E1410",
    "dark_mid": "#2E1E14",
    "ink": "#1E1410",
    "parchment": "#F7F2EB",
    "paper": "#FDF9F4",
    "border": "#E5DDD5",
    "muted": "#9B8F82",
    "secondary_text": "#6B5F52",
    "coral": "#E8573C",
    "coral_light": "#FF7A5C",
    "teal": "#4DBFB4",
    "gold": "#F4C55A",
    "danger": "#E63946",
    "amber": "#F4A340",
}

# Reusable Tailwind class fragments for common surfaces.
CLASSES: dict[str, str] = {
    "page": "min-h-screen w-full bg-[color:var(--purch-parchment)] text-[color:var(--purch-ink)] font-['Plus_Jakarta_Sans']",
    "card": "bg-[color:var(--purch-paper)] border border-[color:var(--purch-border)] rounded-2xl shadow-sm",
    "card_dark": "bg-[color:var(--purch-dark)] text-[color:var(--purch-parchment)] rounded-2xl",
    "display_heading": "font-['Playfair_Display'] font-bold tracking-tight text-[color:var(--purch-ink)]",
    "eyebrow": "font-['DM_Mono'] text-[0.65rem] uppercase tracking-[0.12em] text-[color:var(--purch-muted)]",
    "primary_button": (
        "inline-flex items-center justify-center gap-2 rounded-xl "
        "bg-[color:var(--purch-coral)] hover:bg-[color:var(--purch-coral-light)] "
        "text-white font-semibold px-4 py-2.5 transition-colors "
        "shadow-[0_4px_14px_var(--purch-coral-shadow)]"
    ),
    "ghost_button": (
        "inline-flex items-center justify-center gap-2 rounded-xl "
        "text-[color:var(--purch-muted)] hover:text-[color:var(--purch-coral)] "
        "font-medium px-3 py-2 transition-colors"
    ),
    "outline_button": (
        "inline-flex items-center justify-center gap-2 rounded-xl "
        "border border-[color:var(--purch-border)] bg-[color:var(--purch-paper)] "
        "text-[color:var(--purch-ink)] hover:border-[color:var(--purch-coral)] "
        "hover:text-[color:var(--purch-coral)] font-medium px-4 py-2 transition-colors"
    ),
}

# Route table — single source of truth for both `add_page` and any in-app
# navigation links.
ROUTES: dict[str, str] = {
    "index": "/",
    "login": "/login",
    "chat": "/chat",
    "analytics": "/analytics",
}
