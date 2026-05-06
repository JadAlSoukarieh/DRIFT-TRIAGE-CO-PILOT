"""Small optional LLM smoke test.

Run with:
python -m agent.app.llm.smoke_test
"""

from __future__ import annotations

import sys

from agent.app.config.settings import get_settings
from agent.app.llm.client import complete_json


def main() -> int:
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower().strip()
    fallback = {"ok": True, "mode": provider, "content": "smoke fallback"}
    try:
        result = complete_json(
            system_prompt="You are a smoke test assistant.",
            user_payload={"task": "return a tiny success object"},
            fallback=fallback,
        )
    except RuntimeError as exc:
        if provider == "azure":
            print(f"Azure LLM smoke failed safely: {exc}")
            return 1
        raise
    except Exception as exc:
        if provider == "azure":
            print(f"Azure LLM smoke failed safely: {exc.__class__.__name__}")
            return 1
        raise

    if provider == "mock":
        print("Mock LLM smoke passed.")
        return 0

    print("Azure LLM smoke passed.")
    print(f"Returned keys: {sorted(result.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
