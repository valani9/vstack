"""vstack.signing — HMAC-based integrity signing for reports.

Sign a vstack report (or any JSON-serializable payload) so
downstream consumers can verify the report was emitted by this
service and hasn't been modified in transit.

Use cases
---------

* **Audit trail**. Sign every production report with a service
  secret; auditors verify chain-of-custody.
* **Multi-service trust**. Diagnostic service signs; consumer
  service verifies with shared HMAC key.
* **Tamper detection**. Modified reports fail verification.

Quick start
-----------

    from vstack.signing import (
        Signer,
        sign_report,
        verify_report,
        VerificationError,
    )

    # Sign with HMAC secret:
    signer = Signer(secret="prod-secret-2026-Q2")
    signed = signer.sign(report_dict)

    # signed is the original dict + a "_signature" field.
    # ... transmit ...

    # Downstream verification:
    try:
        verified = verify_report(signed, secret="prod-secret-2026-Q2")
    except VerificationError as e:
        print(f"Verification failed: {e}")
"""

from __future__ import annotations

from ._signing import (
    Signer,
    VerificationError,
    sign_report,
    verify_report,
)

__all__ = [
    "Signer",
    "VerificationError",
    "sign_report",
    "verify_report",
]
