from __future__ import annotations

import hmac
from collections.abc import Mapping
from typing import Any

from .canonical_json import canonical_digest
from .manifest import OUTPUT_DIGEST_CONTRACT
from .scenario_models import CorpusRunResult
from .validation import dataclass_to_dict


_CORPUS_RESULT_KEYS = ("manifest", "scenario_results", "warnings")


def _detached_corpus_payload(result: CorpusRunResult | Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    payload = dataclass_to_dict(result)
    if not isinstance(payload, dict):
        raise TypeError("corpus result must be an object")
    missing = [key for key in _CORPUS_RESULT_KEYS if key not in payload]
    if missing:
        raise ValueError(f"corpus result is missing field(s): {', '.join(missing)}")
    manifest = payload["manifest"]
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    contract = manifest.get("output_digest_contract")
    if contract != OUTPUT_DIGEST_CONTRACT:
        raise ValueError(f"unsupported output digest contract: {contract!r}")
    stored = manifest.get("output_digest")
    if not isinstance(stored, str) or len(stored) != 64 or any(
        character not in "0123456789abcdef" for character in stored
    ):
        if stored != "":
            raise ValueError("manifest.output_digest must be empty or a lowercase SHA-256 digest")
    detached_manifest = dict(manifest)
    detached_manifest["output_digest"] = ""
    detached = {
        "manifest": detached_manifest,
        "scenario_results": payload["scenario_results"],
        "warnings": payload["warnings"],
    }
    return detached, stored


def compute_output_digest(result: CorpusRunResult | Mapping[str, Any]) -> str:
    """Hash the canonical CorpusRunResult with its embedded digest detached."""

    detached, _ = _detached_corpus_payload(result)
    return canonical_digest(detached)


def verify_output_digest(result: CorpusRunResult | Mapping[str, Any]) -> bool:
    """Verify a stored detached-corpus-result-v1 digest without rerunning scenarios."""

    detached, stored = _detached_corpus_payload(result)
    if not stored:
        return False
    return hmac.compare_digest(stored, canonical_digest(detached))
