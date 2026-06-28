"""Resume context provider.

The resume is tiny (~2.4K tokens), so we skip vector retrieval entirely and feed
the whole document to the model — eliminating retrieval misses. Text is loaded
once and cached.

In production the resume comes from R2. For local dev / evals, if R2 isn't
configured we fall back to a local PDF (LOCAL_RESUME_PDF, or a resume PDF next to
this file).
"""
import os
import glob
import logging

from dotenv import load_dotenv

from load_resume import get_resume_from_r2, extract_text_from_pdf

load_dotenv()

logger = logging.getLogger(__name__)

_resume_text = None


def _local_pdf() -> str | None:
    explicit = os.getenv("LOCAL_RESUME_PDF")
    if explicit and os.path.exists(explicit):
        return explicit
    here = os.path.dirname(os.path.abspath(__file__))
    matches = glob.glob(os.path.join(here, "*resume*.pdf"))
    return matches[0] if matches else None


def get_resume_text() -> str:
    """Return the full resume text, cached after first load."""
    global _resume_text
    if _resume_text is not None:
        return _resume_text

    # Prefer R2 when configured; otherwise use a local PDF (dev/evals).
    if os.getenv("R2_BUCKET_NAME"):
        _resume_text = get_resume_from_r2()
    else:
        pdf = _local_pdf()
        if not pdf:
            raise RuntimeError(
                "No resume source: set R2_BUCKET_NAME (prod) or LOCAL_RESUME_PDF / "
                "place a *resume*.pdf next to rag_engine.py (dev)."
            )
        logger.info(f"Loading resume from local PDF: {pdf}")
        _resume_text = extract_text_from_pdf(pdf)

    return _resume_text
