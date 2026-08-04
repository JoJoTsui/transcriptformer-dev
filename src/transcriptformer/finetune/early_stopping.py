"""Early stopping based on a validation metric."""

from __future__ import annotations


class EarlyStopping:
    """Stop training when a validation metric stops improving."""

    def __init__(self, patience: int = 3, min_delta: float = 0.0):
        self.patience = patience
        self.min_delta = min_delta
        self.best: float | None = None
        self.wait = 0

    def should_stop(self, metric: float) -> bool:
        """Update state with the latest metric and return whether to stop."""
        if self.best is None or metric < self.best - self.min_delta:
            self.best = metric
            self.wait = 0
            return False
        self.wait += 1
        return self.wait >= self.patience
