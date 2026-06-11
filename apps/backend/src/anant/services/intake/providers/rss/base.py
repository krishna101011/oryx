"""RSS provider entry — re-exports the concrete class.

Kept tiny so `from anant.services.intake.providers.rss import RssProvider`
just works without importing the parser / client at module load time
when only the type is needed.
"""
from anant.services.intake.providers.rss.sync import (
    RssProvider,
    RssSyncReport,
    cursor_from_report,
)

__all__ = ["RssProvider", "RssSyncReport", "cursor_from_report"]
