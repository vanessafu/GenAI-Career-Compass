from typing import Annotated

from pydantic import StringConstraints

MAX_ITEMS = 50
ShortText = Annotated[str, StringConstraints(max_length=200)]
LongText = Annotated[str, StringConstraints(max_length=5_000)]