"""Stable semantic fingerprint for the deployed rule set.

The hash represents rule contents, independent of JSON whitespace and ordering.
Only cached production rules are used; no network or background task is started.
"""

import hashlib
import json
from functools import lru_cache
from typing import Sequence

from app.expert_system.models import ProductionRule
from app.expert_system.rule_loader import load_rules


def fingerprint_for_rules(rules: Sequence[ProductionRule]) -> str:
    """Return the SHA-256 digest of the canonical decision-rule definitions."""
    canonical = json.dumps(
        [rule.model_dump(mode="json") for rule in sorted(rules, key=lambda rule: rule.id)],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def current_rules_fingerprint() -> str:
    """Computed once per Python process, using the same cached production rules."""
    return fingerprint_for_rules(load_rules())
