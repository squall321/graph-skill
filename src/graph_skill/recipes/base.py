"""Recipe ABC. A recipe normalizes free user input into the engine-agnostic shape
``{engine, assets, options}`` for one artifact type. It is the only place that tolerates
legacy/loose input; the engine itself always receives the canonical shape (determinism).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Recipe(ABC):
    type_name: str = ""

    @abstractmethod
    def normalize(self, payload: dict, resolved) -> dict:
        """Return {"engine": str, "assets": {...}, "options": {...}}.

        ``assets`` is family-specific: xy uses ``assets.series``; a future cad family would
        use ``assets.model``. ``options`` carries only data-dependent overrides (axes,
        title, whitelisted look-and-feel); the engine fills all other defaults.
        """
        raise NotImplementedError

    def structural_requires(self, payload: dict) -> list:
        """validate-v2 hook: non-scalar gate checks (array length, referential integrity,
        asset presence, polymorphic spec) that types.json ``requires`` can't express.
        Return a list of {field, why, ask}. Default: nothing."""
        return []
