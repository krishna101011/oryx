"""Normalizer version constant.

Bumping this number triggers a backfill via the rebuilder job (Batch 2+).
Never decrement. Never reuse a previously-shipped value.

History:
  1 - Phase 3 Batch 1 initial normalizer (URL canon + text sanitizer + basic header)
"""
NORMALIZER_VERSION: int = 1
