
"""Reflection/support profile implementing Reflecti-Mate's mathematics
(Tarvirdians et al., UMAP '26, 10.1145/3774935.3806176), with ED category
semantics kept separate from the LI equations.

LI (paper-derived): profile R=(T,G); breadth B_k; depth D_i=1+|E_i|;
fixation S_k=B_k+sum|E_i|; avg depth Dbar_k=S_k/B_k (0 if B_k=0);
update rules (explore -> new node, exploit -> new elaboration).

ED (project-specific): support-signal categories; decay operationalisation
(x0.5 per unelaborated probe, floor 0.25, reset on elaboration).
"""
from dataclasses import dataclass, field


# ED: support-signal categories, not the paper's thought-topic categories.
SUPPORT_CATEGORIES = ("help_seeking", "reflection", "constraint", "other")


@dataclass
class ThoughtNode:
    text: str
    category: str
    elaborations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.category not in SUPPORT_CATEGORIES:
            raise ValueError(f"Unknown category: {self.category}")

    @property
    def depth(self) -> int:
        # LI: D_i = 1 + |E_i|
        return 1 + len(self.elaborations)


@dataclass
class Profile:
    nodes: list[ThoughtNode] = field(default_factory=list)

    # ED: per-category implicit-feedback utility decay.
    decay: dict[str, float] = field(default_factory=dict)

    # ---- LI: indicators ----

    def breadth(self, k: str) -> int:
        """B_k = |{t_i in T | C(t_i) = k}|"""
        self._validate_category(k)
        return sum(1 for node in self.nodes if node.category == k)

    def depth(self, i: int) -> int:
        """D_i = 1 + |E_i|"""
        return self._get_node(i).depth

    def fixation(self, k: str) -> int:
        """S_k = B_k + sum_{t_i: C(t_i)=k} |E_i|."""
        self._validate_category(k)
        return sum(
            node.depth for node in self.nodes if node.category == k
        )

    def avg_depth(self, k: str) -> float:
        """Dbar_k = S_k / B_k if B_k > 0, else 0."""
        breadth = self.breadth(k)
        if breadth == 0:
            return 0.0
        return self.fixation(k) / breadth

    def total_focus(self) -> int:
        """Sum fixation across the defined support categories."""
        return sum(self.fixation(k) for k in SUPPORT_CATEGORIES)

    # ---- ED: decay ----

    DECAY_RATE = 0.5
    DECAY_FLOOR = 0.25

    def decay_of(self, k: str) -> float:
        self._validate_category(k)
        return self.decay.get(k, 1.0)

    def apply_decay(self, k: str) -> None:
        """Apply one decay step for one qualifying unelaborated probe."""
        self._validate_category(k)
        self.decay[k] = max(
            self.DECAY_FLOOR,
            self.decay_of(k) * self.DECAY_RATE,
        )

    def reset_decay(self, k: str) -> None:
        """Reset category decay following user elaboration."""
        self._validate_category(k)
        self.decay[k] = 1.0

    # ---- LI: update rules ----

    def add_node(self, text: str, category: str) -> None:
        """Explore response -> new main-thought node."""
        self._validate_category(category)
        self.nodes.append(ThoughtNode(text=text, category=category))
        self.reset_decay(category)

    def add_elaboration(self, i: int, text: str) -> None:
        """Exploit response -> elaboration attached to existing thought.

        ED: user elaboration resets decay for the node's category.
        """
        node = self._get_node(i)
        node.elaborations.append(text)
        self.reset_decay(node.category)

    # ---- ED: fixation/shallow decision helpers ----

    def is_fixated(self, k: str, share: float, min_thoughts: int) -> bool:
        self._validate_category(k)

        if not 0.0 <= share <= 1.0:
            raise ValueError("share must be between 0 and 1")

        if min_thoughts < 1:
            raise ValueError("min_thoughts must be at least 1")

        if self.breadth(k) < min_thoughts:
            return False

        total = self.total_focus()
        if total == 0:
            return False

        return self.fixation(k) >= share * total

    def is_shallow(self, k: str, shallow_below: float) -> bool:
        self._validate_category(k)

        if shallow_below < 0:
            raise ValueError("shallow_below must be non-negative")

        return (
            self.breadth(k) > 0
            and self.avg_depth(k) < shallow_below
        )

    # ---- Logging / inspection support ----

    def snapshot(self, include_text: bool = False) -> dict:
        """Return a profile snapshot.

        Raw reflection text is omitted by default. If include_text=True,
        the caller must ensure the snapshot remains in an authorized,
        appropriately protected internal context.
        """
        node_snapshots = []

        for node in self.nodes:
            item = {
                "category": node.category,
                "elaborations_count": len(node.elaborations),
                "depth": node.depth,
            }

            if include_text:
                item["text"] = node.text
                item["elaborations"] = list(node.elaborations)

            node_snapshots.append(item)

        return {
            "nodes": node_snapshots,
            "decay": dict(self.decay),
            "totals": {
                k: {
                    "breadth": self.breadth(k),
                    "fixation": self.fixation(k),
                    "avg_depth": round(self.avg_depth(k), 4),
                }
                for k in SUPPORT_CATEGORIES
            },
        }

    # ---- Validation helpers ----

    @staticmethod
    def _validate_category(k: str) -> None:
        if k not in SUPPORT_CATEGORIES:
            raise ValueError(f"Unknown category: {k}")

    def _get_node(self, i: int) -> ThoughtNode:
        if not isinstance(i, int) or isinstance(i, bool):
            raise TypeError("Node index must be an integer")

        if i < 0 or i >= len(self.nodes):
            raise IndexError(f"Node index out of range: {i}")

        return self.nodes[i]
