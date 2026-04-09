from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

@dataclass
class ProseEmbeddingConfig:
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"    # ✅ General academic/general purpose
    # Alternatives: "BAAI/bge-small-en-v1.5", "all-MiniLM-L6-v2", "sentence-transformers/all-mpnet-base-v2"
    batch_size: int = 32
    embedding_field: str = "vector"  # Standard name
    namespace: str = "prose"
    normalize_embeddings: bool = True  # For cosine similarity

class ProseEmbeddingCreator:
    def __init__(
        self,
        config: Optional[ProseEmbeddingConfig] = None,
        embed_fn: Optional[Callable[[List[str]], List[List[float]]]] = None,
    ):
        if embed_fn is None:
            raise ValueError("embed_fn must be provided - e.g., SentenceTransformer.encode")
        self.config = config or ProseEmbeddingConfig()
        self.embed_fn = embed_fn

        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    # Inside core/embeddings.py
    def build_embeddings(self, chunks: List[Any]) -> List[Dict[str, Any]]:
        payloads = []
        
        # Process in batches for efficiency
        batch_size = 32
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            
            # ✅ FIX: Handle both dicts and tuples
            batch_dicts = []
            for c in batch:
                if isinstance(c, tuple):
                    # If it's a tuple, we assume the structure is (id, text, metadata)
                    # or whatever _make_chunk returned. 
                    # Better yet, let's just force it to be a dict if possible.
                    chunk_id = c[0]
                    metadata_block = c[1]
                        
                    c = {
                            "chunk_id": chunk_id,
                            # ✅ Extract text from inside the metadata block
                            "text": metadata_block.get("text", ""),
                            # ✅ The whole block is the metadata
                            "metadata": metadata_block
                        }
                    # c = {
                    # "chunk_id": c[0],
                    # "text": c[1],
                    # "metadata": c[2] if len(c) > 2 else {}
                    #     }
                batch_dicts.append(c)

            # Now extract the text safely
            texts = [c.get("text", "") for c in batch_dicts]
            
            # Generate embeddings
            embeddings = self.model.encode(texts, normalize_embeddings=self.config.normalize_embeddings)
            
            for j, chunk in enumerate(batch_dicts):
                # Use 'chunk_id' from your updated _make_chunk
                cid = chunk.get("chunk_id")
                meta = self._build_metadata(chunk)

                payloads.append({
                    "id": cid,                             # Standard ID key
                    "chunk_id": cid,                       # Redundant but safe for your DB check
                    "values": embeddings[j].tolist(),      
                    
                    # ✅ TOP LEVEL KEYS (What VectorDB expects)
                    "filepath": meta.get("filepath"),
                    "text": texts[j],
                    
                    # ✅ METADATA BLOCK (What Pinecone stores)
                    "metadata": meta 
                })
                
                # payloads.append({
                #     "id": cid,
                #     "values": embeddings[j].tolist(),
                #     "metadata": {
                #         **chunk.get("metadata", {}),       # ✅ Include all original metadata
                #         "text": texts[j],                  # ✅ Store text INSIDE metadata for retrieval
                #         "filepath": chunk.get("metadata", {}).get("filepath", "unknown.pdf")
                #     }
                # })
                
        return payloads

    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """L2 normalize embedding vector for cosine similarity."""
        vec = np.array(vector)
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vector.tolist() if hasattr(vector, 'tolist') else list(vector)  # Return original (unnormalized)
        
        normalized_vec = (vec / norm).tolist()  # ✅ Normalize + convert to list!
        return normalized_vec


    # def _build_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
    #     """Build clean metadata for vector DB."""
    #     # meta = {
    #     #     "chunk_type": "prose",
    #     #     "namespace": self.config.namespace,
    #     #     "model_name": self.config.model_name,
    #     #     "page": chunk.get("page"),
    #     #     "chunk_index": chunk.get("chunk_index"),
    #     #     "filepath": chunk.get("filepath"),
    #     #     "text_length": len(chunk.get("text", "")),
    #     # }
    #     # # Copy document-level metadata
    #     # for key in ["topic", "level", "course_id"]:
    #     #     if key in chunk.get("metadata", {}):
    #     #         meta[key] = chunk["metadata"][key]
    #     # return meta
    

    #     inner_meta = chunk.get("metadata", {})
        
    #     meta = {
    #         "chunk_type": "prose",
    #         "namespace": self.config.namespace,
    #         "model_name": self.config.model_name,
            
    #         # Look in inner_meta first, then fallback to chunk top-level
    #         "page": inner_meta.get("page", chunk.get("page")),
    #         "chunk_index": inner_meta.get("chunk_index", chunk.get("chunk_index")),
            
    #         # ✅ Critical: Ensure filepath is captured
    #         "filepath": inner_meta.get("filepath") or chunk.get("filepath", "unknown.pdf"),
            
    #         # ✅ Critical: Store text inside metadata so Retrieval can display it
    #         "text": chunk.get("text", ""),
    #         "text_length": len(chunk.get("text", "")),
    #     }
        
    #     # Copy document-level tags (course_id, topic, etc.)
    #     for key in ["topic", "level", "course_id"]:
    #         if key in inner_meta:
    #             meta[key] = inner_meta[key]
                
    #     return meta

    def _build_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize metadata and add embedding-specific tags."""
        
        # 1. Start with EVERYTHING from upstream (preserves course_id, topic, etc.)
        # We look inside 'metadata' first (where your chunker put it)
        # If not there, we fallback to the chunk root (just in case)
        upstream_meta = chunk.get("metadata") or chunk
        
        # Create a clean copy so we don't mutate the original
        meta = upstream_meta.copy() 

        # 2. Add Embedding-Specific Context (Chunker doesn't know these)
        meta["model_name"] = self.config.model_name
        meta["namespace"] = self.config.namespace
        meta["chunk_type"] = "prose"

        # 3. SAFETY PATCH: Fix None values to prevent Pinecone 400 Errors
        # If 'page' is None, default to -1. If it's effectively 0, keep it.
        if meta.get("page") is None:
            meta["page"] = -1
        else:
            meta["page"] = int(meta["page"]) # Ensure it's an int, not string

        if meta.get("chunk_index") is None:
            meta["chunk_index"] = -1
        else:
            meta["chunk_index"] = int(meta["chunk_index"])

        # 4. Critical: Ensure Text and Filepath exist for Retrieval
        # (This acts as a failsafe if upstream forgot them)
        if "text" not in meta:
            meta["text"] = chunk.get("text", "")
            
        if "filepath" not in meta:
            meta["filepath"] = chunk.get("filepath", "unknown.pdf")
            
        meta["text_length"] = len(meta["text"])

        return meta


# class TableEmbeddingCreator:
#     """
#     Creates embedding payloads for table chunks.
#     """

#     def __init__(self, embed_fn: Callable[[List[str]], List[List[float]]],
#                  config: EmbeddingConfig) -> None:
#         self.embed_fn = embed_fn
#         self.config = config

#     def build_payloads(self, table_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#         """
#         Return a list of payload dicts ready for upsert into a vector DB:
#         {
#           'id': <chunk_id>,
#           'vector': [...],
#           'metadata': {...}
#         }
#         """
#         raise NotImplementedError



