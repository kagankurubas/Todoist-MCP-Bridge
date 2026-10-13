"""Tool description normalization, so every supported Python publishes the same descriptions."""

from typing import Optional


def clean_docstring(doc: Optional[str]) -> Optional[str]:
    """Returns doc exactly as the Python 3.13+ compiler stores a docstring.

    Port of CPython's _PyCompile_CleanDoc (Python/compile.c, 3.13): tabs are expanded,
    leading spaces are removed from the first line, and each later line loses up to the
    common indentation of the non-blank later lines. Only spaces count as indentation, and
    leading/trailing blank lines (so the trailing newline) are kept, which is where
    inspect.cleandoc differs. On 3.13+ __doc__ is already clean and this is the identity.
    """
    if doc is None:
        return None
    lines = doc.expandtabs().split("\n")
    first, rest = lines[0], lines[1:]
    indents = [_indent(line) for line in rest if line.strip(" ")]
    margin = min(indents, default=0)
    return "\n".join([first.lstrip(" ")] + [line[min(margin, _indent(line)):] for line in rest])


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))
