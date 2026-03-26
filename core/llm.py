from __future__ import annotations
import json
import os
import re
import time
from typing import Any

import anthropic

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set.")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def chat(
    system: str,
    user: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    retries: int = 3,
    temperature: float = 0.7,
) -> str:
    """Temel LLM çağrısı — ham metin döner."""
    client = get_client()
    for attempt in range(retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            wait = 2 ** attempt
            print(f"[llm] Rate limit — {wait}s bekleniyor...")
            time.sleep(wait)
        except anthropic.APIError as e:
            if attempt == retries - 1:
                raise
            print(f"[llm] API hatası ({e}), tekrar deneniyor...")
            time.sleep(1)
    raise RuntimeError("LLM çağrısı başarısız oldu.")


def chat_json(
    system: str,
    user: str,
    **kwargs: Any,
) -> Any:
    """JSON döndürmesi beklenen LLM çağrısı. Markdown fence'leri temizler."""
    raw = chat(system=system, user=user, **kwargs)
    # ```json ... ``` veya ``` ... ``` bloklarını temizle
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM geçerli JSON döndürmedi.\nHata: {e}\nCevap:\n{raw}") from e
