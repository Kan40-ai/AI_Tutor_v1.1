import os
from typing import List, Dict, Any
from pinecone_text.sparse import BM25Encoder


class BM25Manager:
    def __init__(self, config=None):
        """
        Initializes the BM25 Manager.
        Accepts a config object to maintain consistency with the rest of the pipeline.
        """
        # Fallback to a default string if no config is passed, but prioritize config
        self.filepath = config.BM25_WEIGHTS_PATH if config else "bm25_weights.json"
        self.encoder = BM25Encoder()

    def fit_and_save(self, slide_texts: List[str]) -> None:
        """
        Fits the BM25 model on the corpus and saves the weights (as json to filepath)
        
        Args:
            slide_texts (List[str]): A simple list of strings containing the 
                                     extracted OCR text from your lecture slides.
        """
        print(f"Fitting BM25 on {len(slide_texts)} chunks...")
        self.encoder.fit(slide_texts)
        self.encoder.dump(self.filepath)
        print(f"BM25 weights successfully saved to {self.filepath}")

    def load_model(self) -> None:
        """Loads the pre-calculated weights for fast querying during inference."""
        if os.path.exists(self.filepath):
            self.encoder = BM25Encoder().load(self.filepath)
            print("BM25 weights loaded successfully.")
        else:
            raise FileNotFoundError(
                f"BM25 weights not found at {self.filepath}. "
                "Run fit_and_save() during your database initialization phase."
            )

    def encode_corpus_chunk(self, chunk_text: str) -> Dict[str, Any]:
        """
        Use this ONLY when upserting your slide chunks into Pinecone.
        Returns: {'indices': [...], 'values': [...]}
        """
        return self.encoder.encode_documents(chunk_text)

    def encode_student_query(self, query_text: str) -> Dict[str, Any]:
        """
        Use this ONLY when a student asks a question to the AI Tutor.
        Applies a different mathematical scaling optimized for short search queries.
        Returns: {'indices': [...], 'values': [...]}
        """
        return self.encoder.encode_queries(query_text)