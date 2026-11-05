
"""Seeded epsilon-greedy explore/exploit selection.

LI (literature implementation):
- Explore with probability epsilon.
- Exploit with probability 1 - epsilon.
- Explore targets the least-covered category.
- Exploit targets a low-depth thought in a low-average-depth category.

ED (engineering decisions):
- Seeded RNG for reproducibility.
- Decay-weighted category utility.
- Deterministic tie-breaking.
- Explicit validation and empty-profile fallback.
"""

import random

from app.adaptation.profile import Profile, SUPPORT_CATEGORIES


class ModeSelector:
    """Select an explore/exploit mode and its target."""

    def __init__(self, epsilon: float, seed: int):
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError(
                f"epsilon must be between 0 and 1, got {epsilon}"
            )

        self.epsilon = epsilon
        self.seed = seed
        self.rng = random.Random(seed)

    def select_mode(self) -> str:
        """LI: Explore with probability epsilon; exploit otherwise."""

        return (
            "explore"
            if self.rng.random() < self.epsilon
            else "exploit"
        )

    def select_target(self, mode: str, profile: Profile) -> dict:
        """Select a category and, for exploit, a thought node."""

        if mode not in ("explore", "exploit"):
            raise ValueError(
                f"Unknown selection mode: {mode}"
            )

        if mode == "explore":
            # LI: Least-covered category.
            # Empty categories have breadth 0 and are selected first.
            # ED: Alphabetical tie-breaking is deterministic.
            category = min(
                SUPPORT_CATEGORIES,
                key=lambda k: (profile.breadth(k), k),
            )

            return {
                "mode": "explore",
                "category": category,
            }

        # Exploit requires at least one existing thought.
        categories = [
            category
            for category in SUPPORT_CATEGORIES
            if profile.breadth(category) > 0
        ]

        if not categories:
            # ED: Empty profile falls back to exploration.
            category = min(SUPPORT_CATEGORIES)

            return {
                "mode": "explore",
                "category": category,
            }

        # LI: Low average-depth category.
        # ED: Utility is weighted by implicit-feedback decay.
        def utility(category: str) -> float:
            return (
                profile.avg_depth(category)
                * profile.decay_of(category)
            )

        category = min(
            categories,
            key=lambda k: (utility(k), k),
        )

        # LI: Select the lowest-depth thought in that category.
        node_indices = [
            index
            for index, node in enumerate(profile.nodes)
            if node.category == category
        ]

        node_index = min(
            node_indices,
            key=lambda index: (
                profile.depth(index),
                index,
            ),
        )

        return {
            "mode": "exploit",
            "category": category,
            "node_index": node_index,
        }