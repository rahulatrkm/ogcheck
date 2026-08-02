"""API keys for OGCheck Pro — issue, store (hashed), and verify.

A real, honest paid tier: a Pro customer gets an API key that lifts their rate
limit. Security-first, matching the rest of the enterprise:

* Keys look like ``ogc_live_<32 hex>`` — the plaintext is shown **once** at
  issuance and never stored.
* Only the **SHA-256 hash** of each key is persisted (JSON Lines keystore), so a
  leaked keystore can't be used to make requests.
* Verification hashes the presented key and looks it up; revoked keys fail.

Pure standard library, so it deploys free like the rest of OGCheck.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_PREFIX = "ogc_live_"
# Rate limits (requests/min): free vs. Pro.
FREE_RATE = 30
PRO_RATE = 600


def _keystore_path() -> Path:
    # Overridable for tests / deployment via OGCHECK_KEYSTORE.
    return Path(os.environ.get("OGCHECK_KEYSTORE", "data/api_keys.jsonl"))


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class KeyRecord:
    """The stored (non-secret) facts about an issued key."""

    key_hash: str
    email: str
    plan: str
    created_at: str
    revoked: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "key_hash": self.key_hash,
            "email": self.email,
            "plan": self.plan,
            "created_at": self.created_at,
            "revoked": self.revoked,
        }

    @classmethod
    def from_dict(cls, d: dict) -> KeyRecord:
        return cls(
            key_hash=str(d["key_hash"]),
            email=str(d.get("email", "")),
            plan=str(d.get("plan", "pro")),
            created_at=str(d.get("created_at", "")),
            revoked=bool(d.get("revoked", False)),
        )


def _load(path: Path | None = None) -> list[KeyRecord]:
    p = path or _keystore_path()
    if not p.exists():
        return []
    records: list[KeyRecord] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(KeyRecord.from_dict(json.loads(line)))
    return records


def _save_all(records: list[KeyRecord], path: Path | None = None) -> None:
    p = path or _keystore_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(r.to_dict()) for r in records)
    tmp = p.with_suffix(".jsonl.tmp")
    tmp.write_text(payload + ("\n" if payload else ""), encoding="utf-8")
    tmp.replace(p)


def issue_key(email: str, *, plan: str = "pro", path: Path | None = None) -> str:
    """Create a new key, store only its hash, and return the plaintext ONCE.

    The returned string is the only time the full key exists — the caller (the
    owner) must deliver it to the customer; it cannot be recovered later.
    """
    if not email.strip():
        raise ValueError("email is required to issue a key")
    key = _PREFIX + secrets.token_hex(16)
    record = KeyRecord(
        key_hash=_hash(key),
        email=email.strip().lower(),
        plan=plan,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    records = _load(path)
    records.append(record)
    _save_all(records, path)
    return key


def verify_key(key: str | None, *, path: Path | None = None) -> KeyRecord | None:
    """Return the (non-revoked) record for ``key``, or ``None`` if invalid."""
    if not key or not key.startswith(_PREFIX):
        return None
    target = _hash(key)
    for record in _load(path):
        if record.key_hash == target and not record.revoked:
            return record
    return None


def revoke_key_by_email(email: str, *, path: Path | None = None) -> int:
    """Revoke all keys for an email (e.g. refund/chargeback). Returns count."""
    email = email.strip().lower()
    records = _load(path)
    revoked = 0
    updated: list[KeyRecord] = []
    for r in records:
        if r.email == email and not r.revoked:
            updated.append(KeyRecord(r.key_hash, r.email, r.plan, r.created_at, revoked=True))
            revoked += 1
        else:
            updated.append(r)
    if revoked:
        _save_all(updated, path)
    return revoked


def list_keys(*, path: Path | None = None) -> list[KeyRecord]:
    """All key records (hashes only — never the plaintext keys)."""
    return _load(path)


def rate_for(record: KeyRecord | None) -> int:
    """The per-minute rate limit for a request with (or without) a valid key."""
    return PRO_RATE if record is not None else FREE_RATE


__all__ = [
    "FREE_RATE",
    "PRO_RATE",
    "KeyRecord",
    "issue_key",
    "list_keys",
    "rate_for",
    "revoke_key_by_email",
    "verify_key",
]
