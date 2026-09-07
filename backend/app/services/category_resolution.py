"""Resolves a free-text category guess from the LLM against a user's real
categories, instead of forcing everything into the fixed CATEGORIES enum.

Example: a message mentions "Family" and the user already has a Family
budget -> resolves to "Family". If no such category exists anywhere for
this user, falls back to a fixed-list match, then "Other" as a last
resort. This is what lets "gave my mother allowance worth 200 pesos" land
under an existing "Family" budget instead of always dumping into "Other".
"""
from __future__ import annotations

import difflib

from db.models import get_user_categories
from llm.extraction import CATEGORIES


def resolve_category(user_id: str, category_hint: str) -> str:
    hint = (category_hint or "").strip().lower()
    if not hint:
        return "Other"

    existing = get_user_categories(user_id)  # e.g. ["Family", "Food", "Transport"]
    existing_lower = {c.lower(): c for c in existing}

    # Exact match against the user's own categories first.
    if hint in existing_lower:
        return existing_lower[hint]

    # Fuzzy match — catches near-misses like "familly" or "fam".
    close = difflib.get_close_matches(hint, existing_lower.keys(), n=1, cutoff=0.75)
    if close:
        return existing_lower[close[0]]

    # No user category matched — fall back to the fixed list.
    title_cased = category_hint.strip().title()
    if title_cased in CATEGORIES:
        return title_cased

    return "Other"
