"""Extract raw text from uploaded documents (PDF or plain text)."""
import io

from pypdf import PdfReader


def extract_text_with_pages(filename: str, content: bytes) -> list[tuple[int | None, str]]:
    """Return a list of (page_number, text) tuples.

    For PDFs, page_number is 1-indexed. For plain text files, page_number is
    None and the whole file is returned as a single entry.
    """
    lower = filename.lower()

    if lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append((i, text))
        return pages

    if lower.endswith((".txt", ".md")):
        text = content.decode("utf-8", errors="ignore")
        return [(None, text)]

    raise ValueError(f"Unsupported file type for: {filename}")
