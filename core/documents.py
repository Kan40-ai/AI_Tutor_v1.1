from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any, Iterable

from langchain_community.document_loaders import PyPDFLoader, TextLoader


@dataclass
class DocumentMetadata:
    """
    Metadata attached to each educational document.
    """
    source: str
    topic: Optional[str] = None       # e.g. "calculus"
    level: Optional[str] = None       # e.g. "grade_10", "undergrad"
    course_id: Optional[str] = None   # MOOC course identifier
    extra: Optional[Dict[str, Any]] = None


@dataclass
class EduDocument:
    """
    In-memory representation of a loaded document.
    """
    text: str
    metadata: DocumentMetadata


class EduDocumentLoader:
    """
    Simple, unified loader for multiple sources:

    - Local PDF files
    - Local text/markdown files
    - (Later) MOOC APIs like Coursera/Udemy

    The main method you will call is `load_many(...)`.
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        # If base_dir is set, all relative paths are resolved against it.
        self.base_dir = Path(base_dir).resolve() if base_dir else None

    # ---------- public API ----------

    def load_many(
        self,
        file_paths: Iterable[str],
        topic: Optional[str] = None,
        level: Optional[str] = None,
        course_id: Optional[str] = None,
    ) -> List[EduDocument]:
        """
        Load multiple local files (pdf/txt/md) in a single call.

        Example:
            loader = EduDocumentLoader(base_dir="assets")
            docs = loader.load_many(
                ["notes1.pdf", "notes2.txt"],
                topic="linear algebra",
                level="undergrad",
            )
        """
        docs: List[EduDocument] = []
        for p in file_paths:
            path = self._resolve(p)
            suffix = path.suffix.lower()

            if suffix == ".pdf":
                docs.extend(
                    self._load_pdf(
                        path,
                        topic=topic,
                        level=level,
                        course_id=course_id,
                    )
                )
            elif suffix in {".txt", ".md"}:
                docs.extend(
                    self._load_text(
                        path,
                        topic=topic,
                        level=level,
                        course_id=course_id,
                    )
                )
            else:
                # Unsupported type for now; you can log/print later if desired.
                continue
        
        print(f"📄 LOADER DEBUG: Loaded {len(docs)} docs from {len(file_paths)} files")
        if docs:
            print(f"   ✅ First doc: {docs[0].text[:100]}...")
            print(f"   ✅ Source: {docs[0].metadata.source}")
        else:
            print("   ❌ NO DOCS LOADED!")
        print("-" * 40)

        return docs

    def load_from_dir(
        self,
        dir_path: str,
        patterns: Iterable[str] = ("*.pdf", "*.txt", "*.md"),
        topic: Optional[str] = None,
        level: Optional[str] = None,
        course_id: Optional[str] = None,
    ) -> List[EduDocument]:
        """
        Convenience method to load many files from a directory in one go.

        It will apply all glob patterns in `patterns` (non-recursive).
        Use '**/*.pdf' etc. if you want recursion.
        """
        root = self._resolve(dir_path)
        all_paths: List[str] = []
        for pattern in patterns:
            all_paths.extend(str(p) for p in root.glob(pattern))

        return self.load_many(
            all_paths,
            topic=topic,
            level=level,
            course_id=course_id,
        )

    def load_from_mooc_api(
        self,
        provider: str,
        course_id: str,
        **kwargs: Any,
    ) -> List[EduDocument]:
        """
        Placeholder for MOOC API corpus upload.

        In Phase 2, this will:
        - Call the provider's API (Coursera, Udemy, etc.).
        - Pull lecture transcripts / notes.
        - Wrap them into EduDocument objects.

        For now, it is intentionally a stub.
        """
        raise NotImplementedError(
            f"MOOC API loading for provider '{provider}' is not implemented yet."
        )

    # ---------- internal helpers ----------

    def _resolve(self, path_str: str) -> Path:
        path = Path(path_str)
        if not path.is_absolute() and self.base_dir is not None:
            path = (self.base_dir / path).resolve()
        return path

    def _load_pdf(
        self,
        pdf_path: Path,
        topic: Optional[str],
        level: Optional[str],
        course_id: Optional[str],
    ) -> List[EduDocument]:
        """
        Load a PDF and return one EduDocument per page.
        """
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()

        file_name = pdf_path.name

        docs: List[EduDocument] = []
        for page in pages:
            md = page.metadata or {}
            page_num = md.get("page")

            meta = DocumentMetadata(
                source=file_name,
                topic=topic,
                level=level,
                course_id=course_id,
                extra={
                    "page": page_num,
                    **{k: v for k, v in md.items() if k not in {"source", "page"}},
                },
            )
            docs.append(EduDocument(text=page.page_content, metadata=meta))

        print(f"📄 PDF DEBUG: {pdf_path.name} → {len(docs)} pages")
        return docs

    def _load_text(
        self,
        txt_path: Path,
        topic: Optional[str],
        level: Optional[str],
        course_id: Optional[str],
    ) -> List[EduDocument]:
        """
        Load a text/markdown file as a single EduDocument.
        """
        loader = TextLoader(str(txt_path), encoding="utf-8")
        docs_raw = loader.load()  # usually one element

        docs: List[EduDocument] = []
        for d in docs_raw:
            md = d.metadata or {}
            meta = DocumentMetadata(
                source=str(txt_path),
                topic=topic,
                level=level,
                course_id=course_id,
                extra={k: v for k, v in md.items() if k != "source"},
            )
            docs.append(EduDocument(text=d.page_content, metadata=meta))

        return docs
