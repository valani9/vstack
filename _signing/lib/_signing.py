"""HMAC signing for reports."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any


SIGNATURE_KEY = "_signature"
SIGNATURE_VERSION = "v1"


class VerificationError(Exception):
    """Raised when signature verification fails."""


def _canonical_json(data: dict[str, Any]) -> bytes:
    """Produce canonical JSON for hashing.

    - Excludes the signature field.
    - Sorts keys recursively for stable hashing.
    - Uses UTF-8 with no escaping.
    """
    filtered = {k: v for k, v in data.items() if k != SIGNATURE_KEY}
    return json.dumps(
        filtered,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def _hmac_hex(secret: str, body: bytes, *, algorithm: str = "sha256") -> str:
    if algorithm not in ("sha256", "sha512"):
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    hash_fn = hashlib.sha256 if algorithm == "sha256" else hashlib.sha512
    return hmac.new(
        secret.encode("utf-8"),
        body,
        hash_fn,
    ).hexdigest()


class Signer:
    """Sign and verify reports with an HMAC secret."""

    def __init__(self, secret: str, *, algorithm: str = "sha256"):
        if not secret:
            raise ValueError("Signer requires a non-empty secret.")
        self.secret = secret
        self.algorithm = algorithm

    def sign(self, report: dict[str, Any], *, timestamp: float | None = None) -> dict[str, Any]:
        """Add a signature to a report dict.

        Returns a new dict (does not mutate input).
        """
        copy = {k: v for k, v in report.items() if k != SIGNATURE_KEY}
        ts = timestamp if timestamp is not None else time.time()
        copy["_signed_at"] = ts

        body = _canonical_json(copy)
        sig_hex = _hmac_hex(self.secret, body, algorithm=self.algorithm)

        copy[SIGNATURE_KEY] = {
            "version": SIGNATURE_VERSION,
            "algorithm": self.algorithm,
            "signature": sig_hex,
            "signed_at": ts,
        }
        return copy

    def verify(self, signed: dict[str, Any]) -> dict[str, Any]:
        """Verify a signature; return the original report dict on success.

        Raises VerificationError on failure.
        """
        sig_block = signed.get(SIGNATURE_KEY)
        if not sig_block:
            raise VerificationError("No signature field present.")

        if sig_block.get("version") != SIGNATURE_VERSION:
            raise VerificationError(f"Unknown signature version: {sig_block.get('version')}")

        claimed_sig = sig_block.get("signature")
        if not claimed_sig:
            raise VerificationError("Signature value missing.")

        algorithm = sig_block.get("algorithm", "sha256")
        body = _canonical_json(signed)
        expected = _hmac_hex(self.secret, body, algorithm=algorithm)

        if not hmac.compare_digest(expected, claimed_sig):
            raise VerificationError("Signature mismatch.")

        return {k: v for k, v in signed.items() if k != SIGNATURE_KEY}


def sign_report(
    report: dict[str, Any],
    *,
    secret: str,
    algorithm: str = "sha256",
    timestamp: float | None = None,
) -> dict[str, Any]:
    """Convenience function: sign a report in one call."""
    return Signer(secret, algorithm=algorithm).sign(report, timestamp=timestamp)


def verify_report(
    signed: dict[str, Any],
    *,
    secret: str,
) -> dict[str, Any]:
    """Convenience function: verify a signed report."""
    algorithm = signed.get(SIGNATURE_KEY, {}).get("algorithm", "sha256")
    return Signer(secret, algorithm=algorithm).verify(signed)
