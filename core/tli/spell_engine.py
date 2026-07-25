"""DBMA TLI — SpellEngine protocol and factory.

Module: core/tli/spell_engine.py
Interface: SpellEngine (Protocol) + create_spell_engine() factory

Design notes:
- SpellEngine is a Protocol (structural subtyping) so any adapter
  implementing `check(text: str) -> list[dict]` satisfies the interface.
- Factory `create_spell_engine()` returns the best available adapter.
  Currently only HunspellSpellEngine exists; future adapters can be added
  without changing UI code.
- UI code MUST NOT import hunspell_adapter directly — always use this
  module's interface/factory. (TLI Architecture Vision v1, §5)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    # Avoid circular import at runtime; resolved in create_spell_engine()
    from .hunspell_adapter import HunspellSpellEngine

    SpellEngine = HunspellSpellEngine  # type: ignore[misc]
else:
    # Runtime: define the Protocol for structural subtyping
    class SpellEngine(Protocol):
        """Interface for a spelling checker engine.

        Each item in the returned list:
        {"word": str, "suggestions": list[str], "offset": int}
        """

        def check(self, text: str) -> list[dict]: ...  # noqa: D102


def create_spell_engine() -> "SpellEngine":
    """Return the best available SpellEngine implementation.

    Priority:
    1. HunspellSpellEngine (real hunspell C library via PyHunSpell, ko_KR dictionary)
    2. Fallback: returns a no-op engine that always returns [] (crash-safe)
    """
    try:
        from .hunspell_adapter import HunspellSpellEngine

        engine = HunspellSpellEngine()
        logger.info("SpellEngine created: HunspellSpellEngine")
        return engine  # type: ignore[return-value]
    except ImportError as exc:
        logger.warning("hunspell_adapter not available: %s — using no-op SpellEngine", exc)
        return _NoOpSpellEngine()  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("HunspellSpellEngine initialization failed: %s — using no-op SpellEngine", exc)
        return _NoOpSpellEngine()  # type: ignore[return-value]


class _NoOpSpellEngine:
    """No-op fallback: never flags any words. Crash-safe."""

    def check(self, text: str) -> list[dict]:
        """Return empty list (no errors)."""
        return []