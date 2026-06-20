"""Gmail provider entry — re-exports the concrete class."""
from oryx.services.intake.providers.gmail.sync import (
    GmailProvider,
    GmailSyncReport,
    cursor_from_report,
)

__all__ = ["GmailProvider", "GmailSyncReport", "cursor_from_report"]
