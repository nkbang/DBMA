"""DBMA TLI (Theology Language Intelligence) package.

This package provides protocol interfaces and adapters for TLI engines.
Current engines:
- spell_engine + hunspell_adapter (spelling checker)

Future engines (Dictionary / Style / Citation / Named Entity) will be added
as separate Task Orders per the long-term vision document.
"""

from .spell_engine import SpellEngine, create_spell_engine

__all__ = ["SpellEngine", "create_spell_engine"]