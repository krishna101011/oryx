"""Opaque public-page slug generation (§6 "URLs are opaque, not sequential,
not bearer secrets").

nanoid's default alphabet (`A-Za-z0-9_-`) is URL-safe with no escaping
needed. 12 characters keeps the address short and shareable while staying
far below any realistic collision risk for this table's write rate — the
DB-level UNIQUE(slug) constraint is still the actual guarantee, not this
size choice; PublicPagesRepository retries on a rare collision.
"""
from __future__ import annotations

from nanoid import generate

SLUG_SIZE = 12


def generate_public_page_slug() -> str:
    return generate(size=SLUG_SIZE)
