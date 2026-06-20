"""RSS provider package — re-exports the provider for orchestrator imports."""
from oryx.services.intake.providers.rss.sync import RssProvider

__all__ = ["RssProvider"]
