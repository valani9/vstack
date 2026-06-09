"""Tests for the redaction module."""

from __future__ import annotations


from vstack.redaction import (
    DEFAULT_PATTERNS,
    RedactionPattern,
    Redactor,
    redact_text,
    redact_trace,
)


class TestDefaultPatterns:
    def test_default_patterns_nonempty(self):
        assert len(DEFAULT_PATTERNS) > 0

    def test_each_pattern_has_name_and_regex(self):
        for p in DEFAULT_PATTERNS:
            assert p.name
            assert p.pattern
            assert p.replacement


class TestEmailRedaction:
    def test_email_removed(self):
        text = "Contact alice@example.com for details"
        result = redact_text(text)
        assert "alice@example.com" not in result
        assert "[EMAIL]" in result


class TestPhoneRedaction:
    def test_us_phone_redacted(self):
        text = "Call me at (415) 555-2671 tomorrow"
        result = redact_text(text)
        assert "555-2671" not in result
        assert "[PHONE]" in result

    def test_e164_phone_redacted(self):
        text = "Reach me at +1-415-555-2671"
        result = redact_text(text)
        assert "[PHONE]" in result


class TestSSN:
    def test_ssn_redacted(self):
        text = "SSN is 123-45-6789"
        result = redact_text(text)
        assert "123-45-6789" not in result
        assert "[SSN]" in result


class TestAPIKey:
    def test_sk_key_redacted(self):
        text = "use this: sk-abc123XYZdef456GHIjkl789MNO"
        result = redact_text(text)
        assert "sk-abc123" not in result
        assert "[API_KEY]" in result

    def test_aws_key_redacted(self):
        text = "key: AKIAIOSFODNN7EXAMPLE"
        result = redact_text(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result


class TestBearerToken:
    def test_bearer_redacted(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = redact_text(text)
        assert "Bearer [TOKEN]" in result


class TestJWT:
    def test_jwt_redacted(self):
        text = "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4iLCJpYXQiOjE1MTYyMzkwMjJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        result = redact_text(text)
        assert "[JWT]" in result


class TestIPV4:
    def test_ipv4_redacted(self):
        text = "Server at 192.168.1.1 went down"
        result = redact_text(text)
        assert "192.168.1.1" not in result


class TestURLCredentials:
    def test_url_creds_redacted(self):
        text = "Connect to https://admin:hunter2@db.example.com/data"
        result = redact_text(text)
        assert "hunter2" not in result
        assert "[URL_WITH_CREDS]" in result


class TestRedactor:
    def test_empty_text(self):
        r = Redactor(patterns=DEFAULT_PATTERNS)
        assert r.scrub("") == ""

    def test_no_patterns(self):
        r = Redactor(patterns=[])
        assert r.scrub("hello alice@example.com") == "hello alice@example.com"

    def test_match_counts_tracked(self):
        r = Redactor(patterns=DEFAULT_PATTERNS)
        r.scrub("a@b.com c@d.com e@f.com")
        counts = r.match_counts()
        assert counts["email"] == 3

    def test_reset_counts(self):
        r = Redactor(patterns=DEFAULT_PATTERNS)
        r.scrub("a@b.com")
        r.reset_counts()
        assert r.match_counts()["email"] == 0

    def test_add_pattern_immutable(self):
        r1 = Redactor(patterns=[])
        custom = RedactionPattern(name="foo", pattern=r"foo", replacement="[FOO]")
        r2 = r1.add_pattern(custom)
        assert len(r1.patterns) == 0
        assert len(r2.patterns) == 1

    def test_custom_pattern_applied(self):
        custom = RedactionPattern(
            name="internal_id",
            pattern=r"\bINT-\d+\b",
            replacement="[INTERNAL_ID]",
        )
        r = Redactor(patterns=[custom])
        result = r.scrub("Issue INT-12345 is open")
        assert "INT-12345" not in result
        assert "[INTERNAL_ID]" in result


class TestTraceScrubbing:
    def _trace(self, goal="g", outcome="o", steps=None):
        return {
            "goal": goal,
            "outcome": outcome,
            "steps": steps or [],
            "success": False,
        }

    def test_goal_scrubbed(self):
        trace = self._trace(goal="Find alice@example.com")
        scrubbed = redact_trace(trace)
        assert "alice@example.com" not in scrubbed["goal"]

    def test_outcome_scrubbed(self):
        trace = self._trace(outcome="Returned secret sk-abcdef123456789012345")
        scrubbed = redact_trace(trace)
        assert "sk-abcdef" not in scrubbed["outcome"]

    def test_step_content_scrubbed(self):
        trace = self._trace(
            steps=[
                {"type": "message", "content": "Contact alice@example.com"},
                {"type": "tool_call", "content": "echo 'safe'"},
            ]
        )
        scrubbed = redact_trace(trace)
        assert "alice@example.com" not in scrubbed["steps"][0]["content"]
        assert "safe" in scrubbed["steps"][1]["content"]

    def test_original_not_mutated(self):
        original_text = "Email alice@example.com"
        trace = self._trace(goal=original_text)
        redact_trace(trace)
        # Original unchanged.
        assert trace["goal"] == original_text

    def test_non_dict_step_passthrough(self):
        trace = self._trace(steps=[{"type": "thought", "content": "x"}, "raw"])
        scrubbed = redact_trace(trace)
        assert scrubbed["steps"][1] == "raw"


class TestPatternIsolation:
    def test_separate_redactors_have_separate_counts(self):
        r1 = Redactor(patterns=DEFAULT_PATTERNS)
        r2 = Redactor(patterns=DEFAULT_PATTERNS)
        r1.scrub("a@b.com")
        # r2 should still report 0 emails.
        assert r2.match_counts()["email"] == 0
