"""PDF -> text."""
import io
import logging

from pypdf import PdfReader

from app.exceptions import ResumeProcessingError

logger = logging.getLogger(__name__)
MIN_TEXT_LENGTH = 30


def extract_text_from_pdf(data: bytes) -> str:
    if not data:
        raise ResumeProcessingError("The uploaded file is empty.")
    if not data.lstrip().startswith(b"%PDF"):
        raise ResumeProcessingError("The file is not a valid PDF.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ResumeProcessingError("The PDF is password-protected.")
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except ResumeProcessingError:
        raise
    except Exception as exc:
        logger.warning("PDF parse error: %s", exc)
        raise ResumeProcessingError("The PDF could not be read (it may be corrupted).") from exc
    if len(text.strip()) < MIN_TEXT_LENGTH:
        raise ResumeProcessingError(
            "No readable text found in the PDF. Scanned/image-only PDFs are not supported.")
    return text.strip()
