"""The Oncology Specialty Module. The registry loads `MODULE` by name; the Core never imports this package."""

from app.specialties.oncology.module import MODULE

__all__ = ["MODULE"]
