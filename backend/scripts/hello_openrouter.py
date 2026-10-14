"""Smoke test: one real, traced call to OpenRouter, recorded as a span in the dev database.

Run from backend/:  uv run python -m scripts.hello_openrouter
"""

import asyncio

from app.db import get_engine, make_sessionmaker
from app.llm import complete
from app.tracing import Tracer


async def main() -> None:
    engine = get_engine()
    tracer = Tracer(make_sessionmaker(engine))
    try:
        async with tracer.start_trace("smoke: hello openrouter") as trace_id:
            result = await complete(
                [
                    {
                        "role": "user",
                        "content": "In one sentence, what does a dog boarding facility do?",
                    }
                ],
                name="smoke.hello",
            )
    finally:
        await engine.dispose()

    print(f"model:   {result.model}")
    print(f"reply:   {result.text}")
    print(f"tokens:  {result.prompt_tokens} in / {result.completion_tokens} out")
    print(f"cost:    {result.cost_usd} USD (as reported by the provider)")
    print(f"trace:   {trace_id}")
    print(f"span:    {result.span_id}")


if __name__ == "__main__":
    asyncio.run(main())
