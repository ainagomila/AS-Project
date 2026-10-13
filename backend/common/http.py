"""Small helpers shared by the views."""

from .validators import as_text


def text(request, field):
    """A String field of the JSON body, coerced the way Jackson does."""
    return as_text(request.data.get(field))
