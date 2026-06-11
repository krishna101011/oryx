"""Per-source config for the RSS provider.

The catalog vs custom origin determines what's editable:
- catalog-backed sources inherit `feed_url` and only edit polling cadence
- custom sources own the URL outright

Defaults are tuned for typical Substack / FT / RSS-feed cadence.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class RssSourceConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    feed_url: HttpUrl
    fetch_interval_minutes: int = Field(default=30, ge=5, le=1440)
    user_agent: str = Field(default="AnantIntake/1.0 (+https://anant.capital)")
    # Future-proof, defaults match the RSS 2.0 spec.
    encoding_override: str | None = None
    follow_redirect_policy: Literal["persist_301", "follow_only"] = "persist_301"
