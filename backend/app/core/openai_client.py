import logging
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from typing import TypeVar

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from backend.app.core.config import (
    OPENAI_API_KEY,
    OPENAI_CAREER_PATH_MODEL,
    OPENAI_CV_PARSING_MODEL,
    OPENAI_IDENTITY_MODEL,
    OPENAI_MODEL,
    OPENAI_ROLE_DESCRIPTION_MODEL,
    OPENAI_TEMPERATURE,
)

logger = logging.getLogger("CareerCompass.Core.OpenAIClient")

T = TypeVar("T", bound=BaseModel)

_client: AsyncOpenAI | None = None


def select_model(model_purpose: str | None = None) -> str:
    return {
        "cv_parsing": OPENAI_CV_PARSING_MODEL,
        "identity": OPENAI_IDENTITY_MODEL,
        "role_description": OPENAI_ROLE_DESCRIPTION_MODEL,
        "career_path": OPENAI_CAREER_PATH_MODEL,
    }.get(model_purpose, OPENAI_MODEL)


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

    _client = AsyncOpenAI(api_key=OPENAI_API_KEY, timeout=180.0, max_retries=0)
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
    *,
    model_purpose: str | None = None,
    model: str | None = None,
) -> T | None:
    """Call the LLM and parse the response into a Pydantic model."""
    response = await get_client().beta.chat.completions.parse(
        model=model or select_model(model_purpose),
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
