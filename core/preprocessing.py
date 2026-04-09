from __future__ import annotations

from dataclasses import dataclass
from typing import List, Iterable
import re
import os
from .documents import EduDocument

from google.cloud import vision
from google.cloud.vision_v1 import types
from google.oauth2 import service_account
import pymupdf as fitz


@dataclass
class ProsePreprocessConfig:
    """
    Configuration for OCR + prose text preprocessing.
    """
    # Phase 1 OCR Settings
    ocr_char_threshold: int = 100
    google_creds_path: str = "google_vision_key.json"

    # THE SWITCH:
    # Set to True to OCR every slide with an image (like slide containing Bag of Words image)
    # Set to False to ONLY OCR 'thin' slides (saves money)
    force_ocr_on_congested: bool = True

    join_hyphenated_words: bool = True
    collapse_multiple_spaces: bool = True
    normalize_bullets: bool = True
    strip_extra_newlines: bool = True

    # Header/footer removal
    remove_headers_and_footers: bool = True
    header_footer_patterns: Iterable[str] = (
        r"^\s*Page\s+\d+(\s+of\s+\d+)?\s*$",  # Page 3 / Page 3 of 20
        r"^\s*\d+\s*$",                       # bare page numbers
    )

    # Section title normalization
    normalize_section_titles: bool = True
    max_section_title_len: int = 120  # ignore very long lines
    # treat all-caps or numbered headings as section titles
    section_allcaps_min_len: int = 4




class OCREnricher:
    """
    Phase 1: Identifies 'thin' or 'congested' slides and 
    backfills them with Google Vision text.
    """
    def __init__(self, config: ProsePreprocessConfig):
        self.config = config
        # Initialize Google Vision Client here using your json key
        # 1. Verify the file exists to avoid a silent failure
        if not os.path.exists(self.config.google_creds_path):
            raise FileNotFoundError(f"Google credentials not found at: {self.config.google_creds_path}")

        # 2. Explicitly load the credentials
        credentials = service_account.Credentials.from_service_account_file(
            self.config.google_creds_path
        )
        
        # 3. Pass credentials directly to the client
        self.client = vision.ImageAnnotatorClient(credentials=credentials)
        
    # Funtion for OCR - Image text extraction
    def enrich_page(self, page_obj, base_text: str) -> str:
        
        # STEP 1: Signal A - The 'Thin Text' Check
        # If the PDF reader finds < 100 characters, it's likely a 'mostly-image' slide
        is_thin = len(base_text) < self.config.ocr_char_threshold
        
        # STEP 2: Signal B/C - The 'Visual Objects' Check
        # We check if the PDF internally lists any images or vector drawings
        has_images = len(page_obj.get_images()) > 0
        has_vectors = len(page_obj.get_drawings()) > 0
        has_visual_content = has_images or has_vectors
        
        # STEP 3: The Trigger Logic
        # If it's thin OR has visuals (congested), we run the OCR
        should_ocr = False

        if is_thin:
            # If text is thin, we only use OCR if there's actually a visual taking up space
            if has_visual_content:
                should_ocr = True
            # Result: Skip OCR for empty slides or simple title headers
        
        else:
            # Case: 'Congested Slides'
            # Even if text > threshold, we might still want OCR if visuals are present
            if has_visual_content and self.config.force_ocr_on_congested:
                should_ocr = True
        
        # Final Execution
        if should_ocr:
            ocr_text = self._get_text_from_vision(page_obj)
            return f"{base_text}\n\n[VISUAL_CONTEXT]: {ocr_text}"
        
        return base_text

    def _get_text_from_vision(self, page_obj) -> str:
        """
        Helper to send image data to Google and return the string.
        """
        # Logic to convert PDF page -> Image Bytes goes here
        # Then: response = self.client.document_text_detection(image=image)
        try:
            # 1. RENDER PAGE TO IMAGE
            pix = page_obj.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_bytes = pix.tobytes("png")
            
            # 2. PREPARE GOOGLE VISION OBJECT
            image = vision.Image(content=image_bytes)
            
            # 3. EXECUTE OCR API CALL
            response = self.client.document_text_detection(image=image)
            
            # 4. RETURN THE TEXT
            if response.full_text_annotation:
                return response.full_text_annotation.text
                
        except Exception as e:
            print(f"⚠️ OCR API Error: {e}")
            
        return ""


class ProseTextPreprocessor:
    """
    Cleans prose-like text from educational documents while preserving meaning.

    Responsibilities:
    - Fix hyphenation / bad line breaks.
    - Clean whitespace and bullets.
    - Remove simple headers/footers (page numbers, boilerplate).
    - Normalize section titles (casing, numbering).
    """

    def __init__(self, config: ProsePreprocessConfig | None = None) -> None:
        self.config = config or ProsePreprocessConfig()
        self._header_footer_regexes = [
            re.compile(pat) for pat in self.config.header_footer_patterns
        ]


    def process_enriched_content(self, pdf_text: str, ocr_text: str = None) -> str:
        """
        Combines PDF text and OCR text in the correct sequence 
        before sending them to the core cleaning engine.
        """
        # Step 1: Sequence Assembly
        # We place the OCR text after the slide text to act as a 'Visual Description'
        if ocr_text:
            # The [EXTRACTED_FROM_IMAGE_OCR] tag is critical for LLM context
            combined_segment = f"{pdf_text}\n\n[EXTRACTED_FROM_IMAGE_OCR]\n{ocr_text}\n"
        else:
            combined_segment = pdf_text

        # Step 2: Core Cleaning
        # Now we run the combined text through the existing _clean_text logic
        # This ensures bullets and hyphens in the OCR are fixed too!
        return self._clean_text(combined_segment)


    # ---------- public API ----------
    def preprocess_documents(self, docs: List[EduDocument]) -> List[EduDocument]:
        """
        Apply cleaning to each document and return a new list of EduDocument
        with cleaned text (metadata is preserved).
        """
        cleaned_docs: List[EduDocument] = []
        for doc in docs:
            # Check if metadata contains OCR text from the Enricher
            ocr_content = doc.metadata.get("ocr_text", None)

            # Use the new helper to combine and clean in the right sequence
            clean_text = self.process_enriched_content(doc.text, ocr_content)
            
            cleaned_docs.append(
                EduDocument(
                    text=clean_text,
                    metadata=doc.metadata,
                )
            )
        return cleaned_docs

    # ---------- core cleaning ----------
    def _clean_text(self, text: str) -> str:
        cfg = self.config
        t = text

        # 1) Normalize line endings
        t = t.replace("\r\n", "\n").replace("\r", "\n")

        # 2) Fix hyphenation across line breaks: "back-\npropagation" -> "backpropagation"
        if cfg.join_hyphenated_words:
            t = re.sub(r"(\w+)-\n(\w+)", r"\1\2", t)

        # 3) Normalize bullets
        if cfg.normalize_bullets:
            t = re.sub(r"[•●▪]", "-", t)

        # 4) Handle newlines: keep paragraph breaks but avoid mid-sentence breaks
        if cfg.strip_extra_newlines:
            # Temporarily mark double-newlines (paragraph breaks)
            t = t.replace("\n\n", "<PARA_BREAK>")
            # Turn leftover single newlines into spaces
            t = t.replace("\n", " ")
            # Restore paragraph breaks
            t = t.replace("<PARA_BREAK>", "\n\n")

        # 5) Collapse runs of spaces/tabs into a single space
        if cfg.collapse_multiple_spaces:
            t = re.sub(r"[ \t]+", " ", t)

        # 6) Remove non-printable characters except newlines
        t = "".join(ch for ch in t if ch.isprintable() or ch in "\n")

        # 7) Split into lines for header/footer + section-title logic
        lines = t.split("\n")

        # 7a) Trim whitespace per line
        lines = [ln.strip() for ln in lines]

        # 7b) Remove simple headers/footers
        if cfg.remove_headers_and_footers:
            lines = [ln for ln in lines if not self._is_header_or_footer(ln)]

        # 7c) Normalize section titles
        if cfg.normalize_section_titles:
            lines = [self._normalize_section_title(ln) for ln in lines]

        # 8) Drop empty leading/trailing lines but keep internal blank lines
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()

        return "\n".join(lines)

    # ---------- helpers ----------

    def _is_header_or_footer(self, line: str) -> bool:
        """
        Simple heuristic to drop page numbers or trivial running headers/footers.
        """
        stripped = line.strip()
        if not stripped:
            return False

        for regex in self._header_footer_regexes:
            if regex.match(stripped):
                return True

        return False

    def _normalize_section_title(self, line: str) -> str:
        """
        Normalize section titles such as:
        - '1.2 BACKPROPAGATION' -> 'Backpropagation'
        - 'CHAPTER 3: DERIVATIVES' -> 'Chapter 3: Derivatives'

        The goal is to keep headings recognizable and consistent, not to remove them.
        """
        cfg = self.config
        stripped = line.strip()

        if not stripped or len(stripped) > cfg.max_section_title_len:
            return line

        # Detect numbered headings: "1.", "1.2.", "2.3.4", etc.
        numbered_heading = re.match(r"^(\d+(\.\d+)*)\s+(.+)$", stripped)
        text_part = stripped

        if numbered_heading:
            # Keep the numbering if you like, but normalize the text part
            numbering = numbered_heading.group(1)
            text_part = numbered_heading.group(3)
            normalized = f"{numbering} {self._nice_case(text_part)}"
            return normalized

        # Detect ALL CAPS headings of reasonable length
        if (
            len(stripped) >= cfg.section_allcaps_min_len
            and stripped.upper() == stripped
            and any(ch.isalpha() for ch in stripped)
        ):
            # Convert to title case
            return self._nice_case(stripped)

        return line

    @staticmethod
    def _nice_case(text: str) -> str:
        """
        Convert heading text to a nicer casing:
        - lower everything, then title-case, but preserve common small words.
        """
        small_words = {"and", "or", "of", "in", "on", "for", "to", "a", "an", "the"}
        # basic title-case
        words = text.lower().split()
        if not words:
            return text

        result_words: list[str] = []
        for i, w in enumerate(words):
            if i == 0 or w not in small_words:
                result_words.append(w.capitalize())
            else:
                result_words.append(w)
        return " ".join(result_words)
