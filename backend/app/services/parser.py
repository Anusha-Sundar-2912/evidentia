import re
from pathlib import Path

import pymupdf
from docx import Document as DocxDocument


def clean_text(
    text: str,
) -> str:
    """
    Normalize extracted document text while preserving
    meaningful paragraph boundaries.

    Handles common PDF extraction artifacts including
    line-break hyphenation and split-word hyphenation.
    """

    if not text:
        return ""

    # Remove null characters that can cause downstream
    # storage or processing issues.
    text = text.replace(
        "\x00",
        "",
    )

    # Normalize non-breaking spaces.
    text = text.replace(
        "\u00a0",
        " ",
    )

    # -----------------------------------------------------
    # Repair words split across PDF line breaks.
    #
    # Example:
    # "methodolo-\n gies" -> "methodologies"
    # -----------------------------------------------------

    text = re.sub(
        r"(?<=[A-Za-z])-\s*\n\s*(?=[a-z])",
        "",
        text,
    )

    # -----------------------------------------------------
    # Some PDF extraction pipelines flatten the newline
    # but leave the hyphen and whitespace.
    #
    # Example:
    # "methodolo- gies" -> "methodologies"
    # "deploy- ment"    -> "deployment"
    #
    # Require lowercase fragments on both sides so
    # constructs such as "AI - based" are not joined.
    # -----------------------------------------------------

    text = re.sub(
        r"(?<=[a-z]{2})-\s+(?=[a-z]{2})",
        "",
        text,
    )

    # Normalize horizontal whitespace while retaining
    # newline boundaries.
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    # Remove whitespace immediately before punctuation.
    text = re.sub(
        r"\s+([,.;:!?])",
        r"\1",
        text,
    )

    # Remove spaces directly after a newline.
    text = re.sub(
        r"\n[ \t]+",
        "\n",
        text,
    )

    # Remove spaces directly before a newline.
    text = re.sub(
        r"[ \t]+\n",
        "\n",
        text,
    )

    # Preserve paragraph structure while preventing
    # excessive blank lines.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def parse_pdf(
    file_path: str,
) -> list[dict]:
    """
    Extract normalized text from a PDF while preserving
    page numbers for Evidentia's citation system.
    """

    pages = []

    with pymupdf.open(
        file_path
    ) as pdf:
        for page_number, page in enumerate(
            pdf,
            start=1,
        ):
            text = page.get_text(
                "text"
            )

            text = clean_text(
                text
            )

            if not text:
                continue

            pages.append(
                {
                    "page_number": page_number,
                    "text": text,
                }
            )

    return pages


def parse_docx(
    file_path: str,
) -> list[dict]:
    """
    Extract and normalize paragraph text from a DOCX.

    DOCX does not provide reliable page boundaries at
    this level, so page_number remains None.
    """

    doc = DocxDocument(
        file_path
    )

    paragraphs = []

    for paragraph in doc.paragraphs:
        cleaned = clean_text(
            paragraph.text
        )

        if cleaned:
            paragraphs.append(
                cleaned
            )

    text = "\n".join(
        paragraphs
    )

    if not text:
        return []

    return [
        {
            "page_number": None,
            "text": text,
        }
    ]


def parse_document(
    file_path: str,
) -> list[dict]:
    """
    Dispatch document parsing based on file extension.
    """

    extension = (
        Path(file_path)
        .suffix
        .lower()
    )

    if extension == ".pdf":
        return parse_pdf(
            file_path
        )

    if extension == ".docx":
        return parse_docx(
            file_path
        )

    raise ValueError(
        f"Unsupported file type: {extension}"
    )