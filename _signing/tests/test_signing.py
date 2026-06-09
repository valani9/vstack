"""Tests for the signing module."""

from __future__ import annotations

import pytest

from vstack.signing import (
    Signer,
    VerificationError,
    sign_report,
    verify_report,
)


class TestSigner:
    def test_empty_secret_raises(self):
        with pytest.raises(ValueError):
            Signer(secret="")

    def test_sign_returns_new_dict(self):
        original = {"foo": "bar"}
        signer = Signer(secret="test-key")
        signed = signer.sign(original)
        assert "foo" in signed
        assert "_signature" in signed
        # Original unchanged.
        assert "_signature" not in original

    def test_signature_block_shape(self):
        signer = Signer(secret="test-key")
        signed = signer.sign({"foo": "bar"})
        sig_block = signed["_signature"]
        assert "version" in sig_block
        assert "algorithm" in sig_block
        assert "signature" in sig_block
        assert "signed_at" in sig_block

    def test_default_algorithm_sha256(self):
        signer = Signer(secret="test-key")
        signed = signer.sign({"foo": "bar"})
        assert signed["_signature"]["algorithm"] == "sha256"

    def test_sha512_supported(self):
        signer = Signer(secret="test-key", algorithm="sha512")
        signed = signer.sign({"foo": "bar"})
        assert signed["_signature"]["algorithm"] == "sha512"

    def test_invalid_algorithm_raises(self):
        signer = Signer(secret="test-key")
        # Forcing invalid via private API.
        with pytest.raises(ValueError):
            signer.algorithm = "md5"
            signer.sign({"foo": "bar"})


class TestVerify:
    def test_verify_valid_signature(self):
        signer = Signer(secret="test-key")
        signed = signer.sign({"foo": "bar"})
        original = signer.verify(signed)
        assert original["foo"] == "bar"
        assert "_signature" not in original

    def test_verify_missing_signature_raises(self):
        signer = Signer(secret="test-key")
        with pytest.raises(VerificationError, match="No signature"):
            signer.verify({"foo": "bar"})

    def test_verify_wrong_secret_fails(self):
        good = Signer(secret="good-key")
        bad = Signer(secret="bad-key")
        signed = good.sign({"foo": "bar"})
        with pytest.raises(VerificationError, match="mismatch"):
            bad.verify(signed)

    def test_verify_tampered_payload_fails(self):
        signer = Signer(secret="test-key")
        signed = signer.sign({"foo": "bar"})
        # Tamper with the payload.
        signed["foo"] = "baz"
        with pytest.raises(VerificationError, match="mismatch"):
            signer.verify(signed)

    def test_verify_tampered_signature_fails(self):
        signer = Signer(secret="test-key")
        signed = signer.sign({"foo": "bar"})
        signed["_signature"]["signature"] = "0" * 64
        with pytest.raises(VerificationError, match="mismatch"):
            signer.verify(signed)

    def test_verify_unknown_version_fails(self):
        signer = Signer(secret="test-key")
        signed = signer.sign({"foo": "bar"})
        signed["_signature"]["version"] = "v99"
        with pytest.raises(VerificationError, match="version"):
            signer.verify(signed)


class TestSignRoundtrip:
    def test_complex_payload(self):
        signer = Signer(secret="test-key")
        original = {
            "name": "report-1",
            "findings": [
                {"pattern": "lewin", "severity": "high"},
                {"pattern": "aar", "severity": "medium"},
            ],
            "metadata": {
                "duration_ms": 1234,
                "cost_usd": 0.05,
            },
        }
        signed = signer.sign(original)
        verified = signer.verify(signed)
        assert verified == {**original, "_signed_at": signed["_signed_at"]}

    def test_unicode_preserved(self):
        signer = Signer(secret="test-key")
        signed = signer.sign({"text": "héllo wörld"})
        verified = signer.verify(signed)
        assert verified["text"] == "héllo wörld"

    def test_nested_lists_signed_correctly(self):
        signer = Signer(secret="test-key")
        signed = signer.sign({"nested": [[1, 2], [3, 4]]})
        verified = signer.verify(signed)
        assert verified["nested"] == [[1, 2], [3, 4]]


class TestConvenienceFunctions:
    def test_sign_report_returns_signed(self):
        signed = sign_report({"foo": "bar"}, secret="test-key")
        assert "_signature" in signed

    def test_verify_report_succeeds(self):
        signed = sign_report({"foo": "bar"}, secret="test-key")
        verified = verify_report(signed, secret="test-key")
        assert verified["foo"] == "bar"

    def test_verify_report_with_wrong_secret_fails(self):
        signed = sign_report({"foo": "bar"}, secret="good")
        with pytest.raises(VerificationError):
            verify_report(signed, secret="bad")

    def test_sign_with_explicit_timestamp(self):
        signed = sign_report(
            {"foo": "bar"},
            secret="test-key",
            timestamp=1717891200.0,
        )
        assert signed["_signed_at"] == 1717891200.0


class TestKeyOrderIndependence:
    """Signatures should be stable regardless of key order in input."""

    def test_same_keys_different_order_same_signature(self):
        signer = Signer(secret="test-key")
        a = signer.sign({"x": 1, "y": 2}, timestamp=1000.0)
        b = signer.sign({"y": 2, "x": 1}, timestamp=1000.0)
        assert a["_signature"]["signature"] == b["_signature"]["signature"]
