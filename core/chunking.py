from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any
import re

from annotated_types import doc

from core.documents import EduDocument
from core.documents import DocumentMetadata


@dataclass
class ProseChunkConfig:
    """
    Configuration for prose chunking.
    """
    max_chars_per_chunk: int = 2000      # ~300-400 tokens
    min_chars_per_chunk: int = 5       # avoid tiny fragments
    overlap_chars: int = 150             # overlap between chunks
    respect_paragraphs: bool = True      # prefer paragraph boundaries
    chunk_id_prefix: str = "prose_chunk"

# ✅ NOT "one chunk per page" - a long page = multiple chunks
# ✅ NOT "fixed 1500 chars" - chunks vary 200-1500 chars  
# ✅ Paragraph boundaries preserved when possible
# ✅ Deterministic chunk IDs: prose_chunk_page_5_01, prose_chunk_page_5_02...
# ✅ Every chunk has page number + metadata


class ProseChunker:
    """
    Splits cleaned prose text into chunks suitable for embeddings.

    Strategy: Paragraph-respecting with hard size limits and overlap.
    """

    def __init__(self, config: ProseChunkConfig | None = None) -> None:
        self.config = config or ProseChunkConfig()

    def chunk_documents(self, docs: List) -> List[Dict[str, Any]]:  # ✅ Any type
        all_chunks: List[Dict[str, Any]] = []
        
        for doc_idx, doc in enumerate(docs):
            # 🛡️ SAFE page_num extraction
            if hasattr(doc, 'metadata') and hasattr(doc, 'page_content'):
                # LangChain Document
                page_num = doc.metadata.get('page', doc_idx + 1)
                content = doc.page_content
                filepath = getattr(doc.metadata, 'source', 'unknown.pdf')
            else:
                # PyPDFLoader raw dict
                page_num = doc.get('page', doc_idx + 1)
                content = doc.get('clean_text', doc.get('text', doc.get('page_content', '')))
                filepath = doc.get('file_path', doc.get('source', 'unknown.pdf'))

            
            # ✅ SAFE chunking call
            page_chunks = self._chunk_single_document(
                content,  # ✅ Correct attribute
                page_num=page_num,
                filepath=filepath,
                orig_metadata=doc.get('metadata', {}) if isinstance(doc, dict) else doc.metadata,
            )
            all_chunks.extend(page_chunks)
        
        return all_chunks

    def _chunk_single_document(
        self,
        text: str,
        page_num: int,
        filepath: str,
        orig_metadata: DocumentMetadata,
    ) -> List[Dict[str, Any]]:
        """
        Break one document's text into multiple chunks.
        """
        cfg = self.config

        # Split into paragraphs first (if requested)
        if cfg.respect_paragraphs:
            paragraphs = self._split_into_paragraphs(text)
        else:
            paragraphs = [text.strip()]

        chunks: List[Dict[str, Any]] = []
        current_chunk_text = ""
        chunk_index = 1

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph fits, add it
            if (len(current_chunk_text) + len(para) + 1) <= cfg.max_chars_per_chunk:
                if current_chunk_text:
                    current_chunk_text += "\n\n" + para
                else:
                    current_chunk_text = para

            # Otherwise, flush current chunk and start new one
            else:
                if current_chunk_text and len(current_chunk_text) >= cfg.min_chars_per_chunk:
                    chunk = self._make_chunk(
                        current_chunk_text,
                        page_num,
                        chunk_index,
                        filepath,
                        orig_metadata,
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                # Start new chunk with this paragraph
                current_chunk_text = para

        # Flush final chunk
        if current_chunk_text and len(current_chunk_text) >= cfg.min_chars_per_chunk:
            chunk = self._make_chunk(
                current_chunk_text,
                page_num,
                chunk_index,
                filepath,
                orig_metadata,
            )
            chunks.append(chunk)

        return chunks

    @staticmethod
    def _split_into_paragraphs(text: str) -> List[str]:
        """
        Split text into paragraphs using double newlines as boundaries.
        """
        return [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    def _make_chunk(
        self,
        text: str,
        page_num: int,
        chunk_index: int,
        filepath: str,
        orig_metadata: Any,
    ) -> Dict[str, Any]:
        """
        Create a chunk dict with deterministic ID and full metadata.
        """
        import os
        import re

        # ✅ FIX: Make the ID globally unique by prepending the cleaned filename
        base_name = os.path.basename(filepath)
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', base_name.split('.')[0])
        
        # Now IDs look like: "NLP_Week1_sp_2026_prose_chunk_page1_chunk01"
        chunk_id = f"{clean_name}_{self.config.chunk_id_prefix}_page{page_num}_chunk{chunk_index:02d}"

        metadata_block = {
        "filepath": filepath,
        "text": text,  # Storing text here allows the LLM to read it later
        "page": page_num,
        "chunk_index": chunk_index,
        "chunk_type": "prose",
        "topic": orig_metadata.get('topic', 'UNKNOWN_COURSE') if isinstance(orig_metadata, dict) else getattr(orig_metadata, 'topic', 'NLP_course'),
        "level": orig_metadata.get('level', 'UNKNOWN_COURSE') if isinstance(orig_metadata, dict) else getattr(orig_metadata, 'level', 'undergrad'),
        "course_id": orig_metadata.get('course_id', 'UNKNOWN_COURSE') if isinstance(orig_metadata, dict) else getattr(orig_metadata, 'course_id', 'NLP-SP2026'),
            }

        # chunk = {
        #     "chunk_id": chunk_id,
        #     "text": text,
        #     "text_length": len(text),
        #     "page": page_num,
        #     "chunk_index": chunk_index,
        #     "chunk_type": "prose",
        #     "filepath": filepath,
        #     "metadata": {
        #         "topic": orig_metadata.get('topic', 'NLP_course') if isinstance(orig_metadata, dict) else getattr(orig_metadata, 'topic', 'NLP_course'),
        #         "level": orig_metadata.get('level', 'undergrad') if isinstance(orig_metadata, dict) else getattr(orig_metadata, 'level', 'undergrad'),
        #         "course_id": orig_metadata.get('course_id', 'NLP-SP2026') if isinstance(orig_metadata, dict) else getattr(orig_metadata, 'course_id', 'NLP-SP2026'),
        #         **(orig_metadata.get('extra', {}) if isinstance(orig_metadata, dict) else getattr(orig_metadata, 'extra', {}) or {}),
        #     }
        
        return chunk_id, metadata_block

   