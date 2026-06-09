from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone


def _seed_digest(seed: str, nbytes: int = 32) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[: nbytes * 2]


def make_cache_buster(*, fixed: bool = False, seed: str | None = None) -> str:
    """Build a structured metadata header that busts prefix cache when unique."""
    if fixed and seed is not None:
        digest = _seed_digest(seed)
        app_hash = _seed_digest(seed, nbytes=64)
        request_id = digest[:16]
        session = f"sess_{digest[16:28]}"
        revision = f"r-{int(digest[:8], 16) % 100000}"
        generated_at = "2026-01-01T00:00:00Z"
    else:
        app_hash = secrets.token_hex(64)
        request_id = secrets.token_hex(8)
        session = f"sess_{secrets.token_hex(6)}"
        revision = f"r-{secrets.randbelow(100000)}"
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return (
        "[Build Metadata]\n"
        f"app hash: {app_hash}\n"
        f"request id: {request_id}\n"
        f"session: {session}\n"
        f"generated at: {generated_at}\n"
        f"revision: {revision}\n"
        "---\n"
    )


def prepend_cache_buster(prompt: str, *, fixed: bool = False, seed: str | None = None) -> str:
    return make_cache_buster(fixed=fixed, seed=seed) + prompt
