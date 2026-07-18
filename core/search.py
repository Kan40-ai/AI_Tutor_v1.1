from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional
import logging
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

SearchTarget = Literal["tables", "prose", "both"]
logger = logging.getLogger(__name__)

@dataclass
class SearchConfig:
    table_index_name: str = "edu-tables"
    prose_index_name: str = "edu-prose" 
    table_namespace: str = "tables"
    prose_namespace: str = "prose"
    table_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    prose_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    default_top_k: int = 10
    default_score_threshold: Optional[float] = None

class EduSearchHelper:
    """
    Encapsulates query embedding + vector search across table and prose indices.
    Fully implemented for your single prose index setup.
    """
    
    def __init__(self, config: SearchConfig, api_key: Optional[str] = None) -> None:
        self.config = config
        self.api_key = api_key
        self._pc_client = None
        self._table_index = None
        self._prose_index = None
        self._table_model = None
        self._prose_model = None

    def init_clients_and_models(self) -> None:
        """Initialize Pinecone client, indices, and embedding models."""
        if self._pc_client is None:
            self._pc_client = Pinecone(api_key=self.api_key)
            logger.info("✅ Connected to Pinecone")
        
        # Load YOUR prose index (ai-tutor)
        self._prose_index = self._pc_client.Index("ai-tutor")
        logger.info("✅ Loaded prose index: ai-tutor")
        
        # Load embedding model (SAME as your corpus)
        self._prose_model = SentenceTransformer(self.config.prose_model_name)
        logger.info(f"✅ Loaded embedding model: {self.config.prose_model_name}")
        
        # Tables not used (your setup), but stubbed for future
        self._table_model = None
        self._table_index = None

    def search(
        self,
        query: str,
        target: SearchTarget = "prose",
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        table_filter: Optional[Dict[str, Any]] = None,
        prose_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        High-level search API. Returns dict with 'tables' and 'prose' hits.
        Compatible with RAG.py expectations.
        """
        top_k = top_k or self.config.default_top_k
        
        # Search prose (YOUR data)
        prose_results = []
        if target in ["prose", "both"]:
            prose_results = self._search_single_index(
                query=query,
                index=self._prose_index,
                model=self._prose_model,
                namespace=self.config.prose_namespace,
                top_k=top_k,
                score_threshold=score_threshold,
                metadata_filter=prose_filter,
                chunk_type="prose"
            )
        
        # Tables stubbed (no table data in your setup)
        table_results = []
        if target in ["tables", "both"] and self._table_index:
            table_results = self._search_single_index(
                query=query,
                index=self._table_index,
                model=self._table_model,
                namespace=self.config.table_namespace,
                top_k=top_k,
                score_threshold=score_threshold,
                metadata_filter=table_filter,
                chunk_type="tables"
            )
        
        return {
            "prose": prose_results,
            "tables": table_results
        }

    def _search_single_index(
        self,
        query: str,
        index: Any,
        model: Any,
        namespace: str,
        top_k: int,
        score_threshold: Optional[float],
        metadata_filter: Optional[Dict[str, Any]],
        chunk_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Query one index and normalize matches into RAG.py format.
        """
        # Embed query using SAME model as corpus
        query_emb = model.encode([query], normalize_embeddings=True)[0].tolist()
        
        # Pinecone query (YOUR exact setup)
        results = index.query(
            vector=query_emb,
            top_k=top_k,
            namespace=namespace,  # "prose"
            include_metadata=True,
            filter=metadata_filter
        )
        
        # Format matches for RAG.py
        matches = []
        for match in results.get('matches', []):
            if score_threshold and match['score'] < score_threshold:
                continue
                
            matches.append({
                'id': match['id'],
                'score': match['score'],
                'text': match['metadata'].get('text', match['metadata'].get('clean_text', '')),
                'metadata': {
                    'chunk_type': chunk_type,
                    **match.get('metadata', {})
                }
            })
        
        logger.debug(f"Found {len(matches)} {chunk_type} matches")
        return matches
