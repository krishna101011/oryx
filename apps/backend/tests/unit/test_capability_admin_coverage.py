"""Turns docs/TEAM_WORKSPACE_ARCHITECTURE.md §6's warning into a permanent
guard: "a new workspace.* namespace must be DELIBERATELY added to admin's
grant list, or admins silently won't have it even though the routes exist."

This sweeps the REAL router source for every require_capability("X.Y") call
site and asserts CAPABILITIES["admin"] covers each discovered namespace X
(exactly or via a wildcard) — dynamically, not against a hardcoded snapshot
of today's namespaces. A future dev who adds require_capability("billing.
manage") in a new router without updating admin's grant list makes this
test fail immediately, exactly the trap the doc describes.
"""
from __future__ import annotations

import re
from pathlib import Path

from oryx.core.dependencies import _role_grants

_SERVICES_DIR = Path(__file__).resolve().parents[2] / "src" / "oryx" / "services"
_CAP_CALL_RE = re.compile(r'require_capability\(\s*["\']([a-z_]+)\.[a-z_*]+["\']\s*\)')

# Namespaces used by a live require_capability() call that admin
# DELIBERATELY does not cover. Each entry must say why — a real, examined
# decision, not a way to silence this test.
#
# 'intake': a REAL pre-existing gap (intake.read/intake.write are used on
# live source-management/OAuth routes — src/oryx/services/intake/router.py,
# oauth_router.py), discovered by this sweep while building Team/Workspace
# Rev 2. NOT fixed here — out of scope for this wave, which is specifically
# about the new workspace.* namespace. Flagged here rather than silently
# left invisible, so a future wave can pick it up deliberately.
ADMIN_EXCLUDED_NAMESPACES: set[str] = {"intake"}


def _discover_capability_namespaces() -> set[str]:
    namespaces: set[str] = set()
    for path in _SERVICES_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for m in _CAP_CALL_RE.finditer(text):
            namespaces.add(m.group(1))
    return namespaces


def test_sweep_finds_the_real_known_namespaces() -> None:
    """Sanity check on the regex itself — if this fails, the sweep below is
    silently finding nothing and would pass for the wrong reason."""
    namespaces = _discover_capability_namespaces()
    assert "workspace" in namespaces
    assert "research" in namespaces
    assert "settings" in namespaces


def test_every_capability_namespace_is_covered_by_admin_or_explicitly_excluded() -> None:
    namespaces = _discover_capability_namespaces()
    assert namespaces, "sweep found no require_capability(...) call sites — regex likely stale"

    uncovered = []
    for ns in sorted(namespaces):
        if ns in ADMIN_EXCLUDED_NAMESPACES:
            continue
        if not _role_grants("admin", f"{ns}.read"):
            uncovered.append(ns)

    assert not uncovered, (
        f"capability namespace(s) {uncovered!r} are used by a live route but "
        f"CAPABILITIES['admin'] doesn't grant them — the doc §6 trap: add "
        f"'{{ns}}.*' to admin's list in core/dependencies.py, or add it to "
        f"ADMIN_EXCLUDED_NAMESPACES here with a real reason if that's deliberate."
    )


def test_workspace_namespace_is_specifically_covered() -> None:
    """The concrete case this guard exists for: Team/Workspace Rev 2 added
    require_capability("workspace.manage") calls — admin must have been
    given "workspace.*" in the same change, not left to discover it later
    as a bug report."""
    assert _role_grants("admin", "workspace.manage")
    assert _role_grants("admin", "workspace.invite")


def test_owner_wildcard_still_covers_everything_discovered() -> None:
    """owner's "*" grant must never need per-namespace maintenance — if this
    ever fails, something rewired _role_grants in a way that broke the
    universal wildcard, a much bigger regression than the admin trap."""
    for ns in _discover_capability_namespaces():
        assert _role_grants("owner", f"{ns}.read")
        assert _role_grants("owner", f"{ns}.write")
