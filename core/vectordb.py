"""
EduTutor Vector Database - Simple Pinecone wrapper for Professor demo.
Handles index creation, upload, search - all in one class.
"""

from typing import List, Dict, Any, Optional
import time
from dataclasses import dataclass
from pinecone import Pinecone, ServerlessSpec
import numpy as np

@dataclass
class VectorDBConfig:
    """Simple config for professor demo."""
    api_key: str
    index_name: str = "starter-index"
    dimension: int = 384  # all-mpnet-base-v2
    metric: str = "cosine"
    cloud: str = "aws"
    region: str = "us-east-1"

class EduVectorDB:
    def __init__(self, config: VectorDBConfig):
        """Initialize with Pinecone index (expects it to already exist)."""
        self.config = config
        self.index = self._create_or_get_index()
        print(f"✅ VectorDB ready: {self.config.index_name}")

    def _create_or_get_index(self) -> Pinecone.Index:
        pc = Pinecone(api_key=self.config.api_key)

        # List visible indexes for this API key
        indexes = pc.list_indexes().names()
        print(f"🔑 API KEY VISIBLE INDEXES: {indexes}")

        # 1) Check that desired index exists for this key
        if self.config.index_name not in indexes:
            raise Exception(
                f"CRITICAL: Index '{self.config.index_name}' not found for this API key. "
                f"Visible indexes: {indexes}"
            )

        # 2) Open exactly that index
        index = pc.Index(self.config.index_name)
        print(f"✅ Using Pinecone index: {self.config.index_name}")
        return index

    
    def upload(self, payloads: List[Dict[str, Any]], namespace: str = None):
        """Step 2: Upload embeddings (batched, sanitized)."""
        print(f"📤 Uploading {len(payloads)} vectors to namespace '{namespace}'")
        
        vectors = self._prepare_vectors(payloads)
        self._batch_upsert(vectors, namespace)
        print(f"✅ Uploaded {len(payloads)} vectors!")
    
    def _prepare_vectors(self, payloads: List[Dict[str, Any]]) -> List[tuple]:
        """
        Sanitize payloads for Pinecone.
        Ensures filepath and chunk_id are correctly moved into metadata.
        """
        vectors = []
        for payload in payloads:
            # 1. Use the globally unique chunk_id we created in chunking.py
            vec_id = payload.get("chunk_id", str(payload.get("id", f"vec_{hash(str(payload))}")))
            
            # 2. Get existing metadata or create new
            metadata = payload.get("metadata", {}).copy()
            metadata["filepath"] = payload.get("filepath")
            metadata["text"] = payload.get("text", "")
            
            # 3. CRITICAL: Explicitly move filepath and text into metadata
            # Pinecone needs these inside the metadata dict to return them in searches
            if "filepath" in payload:
                metadata["filepath"] = payload.get("filepath", "unknown.pdf")
            if "text" in payload:
                metadata["text"] = payload.get("text", "")
                
            # 4. Sanitize the updated metadata
            sanitized_metadata = self._sanitize_metadata(metadata)
            
            # 5. Extract vector values
            values = payload["values"]
        
            vectors.append((vec_id, values, sanitized_metadata))
            
        return vectors
    
    def _sanitize_metadata(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        """Clean metadata for Pinecone limits."""
        clean = {}
        for k, v in meta.items():
            # ✅ DEBUG: Print each metadata field type
            #print(f"    metadata['{k}'] type: {type(v)}")
            
            # ✅ FIX: Handle numpy types in metadata
            if isinstance(v, np.ndarray):
                print(f"      ⚠️ Converting numpy array to list")
                clean[k] = v.tolist()
            elif isinstance(v, (np.integer, np.floating)):
                print(f"      ⚠️ Converting numpy scalar to Python type")
                clean[k] = v.item()
            elif k == "bbox" and isinstance(v, (list, tuple)):
                clean[k] = ",".join(map(str, v))
            elif isinstance(v, (str, int, float, bool, type(None))):
                clean[k] = v
            elif isinstance(v, list):
                # ✅ Check if list contains numpy objects
                if any(isinstance(x, (np.ndarray, np.generic)) for x in v):
                    print(f"      ⚠️ List contains numpy objects")
                    clean[k] = [x.tolist() if hasattr(x, 'tolist') else x for x in v]
                elif len(v) < 10 and all(isinstance(x, str) for x in v):
                    clean[k] = v[:5]
                else:
                    clean[k] = [str(x) for x in v]  # Convert to strings if needed
            else:
                print(f"      ⚠️ Unknown type, converting to string")
                clean[k] = str(v)
        
        return clean
    
    def _batch_upsert(self, vectors: List[tuple], namespace: str = None):
        """Batch upsert with progress."""
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            if namespace:
                self.index.upsert(vectors=batch, namespace=namespace)
            else:
                self.index.upsert(vectors=batch)
            print(f"  📦 Upserted batch {i//batch_size + 1}/{(len(vectors)-1)//batch_size + 1}")
    
    def search(self, query_embedding: List[float], 
               namespace: str = None, 
               top_k: int = 5) -> List[Dict[str, Any]]:
        """Step 3: Semantic search (for RAG)."""
        # ✅ FIX: Convert numpy array to list
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()
        elif isinstance(query_embedding, np.ndarray):
            query_embedding = query_embedding.tolist()
        elif not isinstance(query_embedding, list):
            query_embedding = list(query_embedding)


        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            namespace=namespace
        )
        return [
            {
                "id": match["id"],
                "score": match["score"],
                "metadata": match["metadata"]
            }
            for match in results["matches"]
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Check how many vectors are stored."""
        stats = self.index.describe_index_stats()
        return {
            "total_vectors": stats.total_vector_count,
            "namespaces": stats.namespaces
        }

# Utility function for query embedding (Step 5)
def normalize_vector(vector: List[float]) -> List[float]:
    """L2 normalize for cosine similarity."""
    vec = np.array(vector)
    norm = np.linalg.norm(vec)
    return vector if norm == 0 else (vec / norm).tolist()
