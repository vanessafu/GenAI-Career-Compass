import logging
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from typing import TypeVar

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from backend.app.core.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE

logger = logging.getLogger("CareerCompass.Core.OpenAIClient")

T = TypeVar("T", bound=BaseModel)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Return the initialized client instance or raise if not yet initialized."""
    if _client is None:
        raise RuntimeError(
            "OpenAI client is not initialized. "
            "Ensure openai_client_lifespan is active."
        )
    return _client


@asynccontextmanager
async def openai_client_lifespan() -> AsyncGenerator[None, None]:
    """FastAPI lifespan context manager for the OpenAI client."""
    global _client
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

    _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    logger.info("OpenAI client initialized.")

    try:
        yield
    finally:
        if _client is not None:
            await _client.close()
            _client = None
            logger.info("OpenAI client closed.")


async def parse_structured(
    messages: Iterable[ChatCompletionMessageParam],
    response_format: type[T],
) -> T | None:
    """Call the LLM and parse the response into a Pydantic model."""
    response = await get_client().beta.chat.completions.parse(
        model=OPENAI_MODEL,
        messages=messages,
        response_format=response_format,
        temperature=OPENAI_TEMPERATURE,
    )

    message = response.choices[0].message
    if message.parsed is None:
        logger.warning(
            "Parsed message is None. Finish reason: %s, Refusal: %s",
            response.choices[0].finish_reason,
            message.refusal,
        )
    return message.parsed


async def complete(
    messages: Iterable[ChatCompletionMessageParam],
) -> str | None:
    """Call the LLM and return the response as a plain string."""
    response = await get_client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=OPENAI_TEMPERATURE,
    )
    return response.choices[0].message.content


async def embed(text: str, model: str) -> list[float]:
    """Embed a single text string and return the embedding vector."""
    response = await get_client().embeddings.create(model=model, input=[text])
    return response.data[0].embedding
