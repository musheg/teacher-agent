import pytest

from app.core.exceptions import AllFallbacksFailedError, UpstreamError
from app.core.resilience import call_with_retry, with_fallback


async def test_retry_succeeds_after_failure() -> None:
    attempts = {"n": 0}

    async def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise RuntimeError("flake")
        return "ok"

    result = await call_with_retry(flaky, upstream="test", timeout_s=5)
    assert result == "ok"
    assert attempts["n"] == 2


async def test_retry_exhausts_and_raises() -> None:
    async def always_fail() -> None:
        raise RuntimeError("nope")

    with pytest.raises(UpstreamError):
        await call_with_retry(always_fail, upstream="test_fail", timeout_s=5, max_attempts=2)


async def test_fallback_chain_first_success() -> None:
    async def call(entry: str) -> str:
        if entry == "primary":
            raise RuntimeError("down")
        return f"used:{entry}"

    out = await with_fallback(["primary", "secondary"], upstream="x", invoke=call)
    assert out == "used:secondary"


async def test_fallback_chain_all_fail() -> None:
    async def call(_entry: str) -> str:
        raise RuntimeError("kaboom")

    with pytest.raises(AllFallbacksFailedError):
        await with_fallback(["a", "b"], upstream="x", invoke=call)
