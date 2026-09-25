"""Text field types shared by the API schemas."""

from typing import Annotated

from pydantic import StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
# Empty is allowed: in an edit it clears the address.
Email = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^([^@\s]+@[^@\s]+\.[^@\s]+)?$")]
