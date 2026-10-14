"""Phase 0 smoke test: one real call to OpenRouter, printing the reply, tokens, and cost.

Run from backend/:  uv run python -m scripts.hello_openrouter
"""

import time

from openai import OpenAI

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    client = OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key.get_secret_value(),
        timeout=30,
    )

    started = time.perf_counter()
    response = client.chat.completions.create(
        model=settings.openrouter_model,
        messages=[
            {"role": "user", "content": "In one sentence, what does a dog boarding facility do?"}
        ],
    )
    latency_ms = (time.perf_counter() - started) * 1000

    usage = response.usage
    # `cost` is an OpenRouter extension to the OpenAI usage object, so the SDK has no typed
    # field for it; it's kept as an extra attribute.
    cost = getattr(usage, "cost", None)

    print(f"model:    {response.model}")
    print(f"reply:    {response.choices[0].message.content}")
    print(f"tokens:   {usage.prompt_tokens} in / {usage.completion_tokens} out")
    print(f"cost:     ${cost} (USD)")
    print(f"latency:  {latency_ms:.0f} ms")


if __name__ == "__main__":
    main()
