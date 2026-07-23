"""Recursive character-based text splitter.

Splits text on a hierarchy of separators (paragraphs -> lines -> sentences ->
words) recursively, trying the largest separator first and only falling back
to a smaller one when a piece is still too large. This keeps semantically
related text together more often than a naive fixed-width split.
"""

SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def _split_text(text: str, separators: list[str]) -> list[str]:
    if not separators:
        return [text]

    sep, *rest = separators
    if sep == "":
        return list(text)

    parts = text.split(sep)
    if len(parts) == 1:
        return _split_text(text, rest)

    # Re-attach separator (except for the last part) so we don't lose punctuation/whitespace.
    return [p + sep if i < len(parts) - 1 else p for i, p in enumerate(parts)]


def recursive_chunk_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[str]:
    """Split `text` into overlapping chunks of at most `chunk_size` characters."""
    if not text or not text.strip():
        return []

    pieces = _split_text(text, SEPARATORS)

    chunks: list[str] = []
    current = ""

    for piece in pieces:
        if len(current) + len(piece) <= chunk_size:
            current += piece
        else:
            if current.strip():
                chunks.append(current.strip())
            if len(piece) > chunk_size:
                # Piece itself too large (e.g. no separators found) - hard split.
                for i in range(0, len(piece), chunk_size - chunk_overlap):
                    sub = piece[i : i + chunk_size]
                    if sub.strip():
                        chunks.append(sub.strip())
                current = ""
            else:
                # Start new chunk, carrying overlap from the end of the previous chunk.
                overlap_text = current[-chunk_overlap:] if chunk_overlap else ""
                current = overlap_text + piece

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if c]
