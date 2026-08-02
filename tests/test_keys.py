"""Tests for the OGCheck API-key system — offline, temp keystore."""

from __future__ import annotations

from ogcheck.keys import (
    FREE_RATE,
    PRO_RATE,
    issue_key,
    list_keys,
    rate_for,
    revoke_key_by_email,
    verify_key,
)


def test_issue_returns_prefixed_key(tmp_path) -> None:
    p = tmp_path / "keys.jsonl"
    key = issue_key("a@example.com", path=p)
    assert key.startswith("ogc_live_")
    assert len(key) > 20


def test_plaintext_key_is_not_stored(tmp_path) -> None:
    p = tmp_path / "keys.jsonl"
    key = issue_key("a@example.com", path=p)
    raw = p.read_text()
    assert key not in raw  # only the hash is persisted
    assert "key_hash" in raw


def test_verify_valid_and_invalid(tmp_path) -> None:
    p = tmp_path / "keys.jsonl"
    key = issue_key("user@example.com", path=p)
    rec = verify_key(key, path=p)
    assert rec is not None
    assert rec.email == "user@example.com"
    assert rec.plan == "pro"
    assert verify_key("ogc_live_deadbeef", path=p) is None
    assert verify_key(None, path=p) is None
    assert verify_key("not-even-a-key", path=p) is None


def test_revoke_disables_key(tmp_path) -> None:
    p = tmp_path / "keys.jsonl"
    key = issue_key("gone@example.com", path=p)
    assert verify_key(key, path=p) is not None
    n = revoke_key_by_email("gone@example.com", path=p)
    assert n == 1
    assert verify_key(key, path=p) is None  # revoked keys fail


def test_rate_for_tiers() -> None:
    assert rate_for(None) == FREE_RATE
    # A record (any) yields the Pro rate.
    from ogcheck.keys import KeyRecord

    rec = KeyRecord("h", "e@x.com", "pro", "2026-01-01")
    assert rate_for(rec) == PRO_RATE
    assert PRO_RATE > FREE_RATE


def test_list_keys(tmp_path) -> None:
    p = tmp_path / "keys.jsonl"
    issue_key("one@example.com", path=p)
    issue_key("two@example.com", path=p)
    records = list_keys(path=p)
    assert len(records) == 2
    assert {r.email for r in records} == {"one@example.com", "two@example.com"}


def test_empty_email_rejected(tmp_path) -> None:
    import pytest

    with pytest.raises(ValueError):
        issue_key("  ", path=tmp_path / "k.jsonl")
