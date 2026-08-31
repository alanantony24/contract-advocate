import io
import pdfplumber


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract raw text from PDF bytes using pdfplumber.

    Works for text-based PDFs (the common case for contracts). Scanned/image
    PDFs will return little or no text - that's a known limitation. Handling
    those would need OCR (e.g. AWS Textract), which is out of scope for the
    hackathon build unless there's spare time at the end.
    """
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_pdf_path(path: str) -> str:
    with open(path, "rb") as f:
        return extract_text_from_pdf_bytes(f.read())
