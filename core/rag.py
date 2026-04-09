from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple
import torch
from sentence_transformers import CrossEncoder
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import logging

from sentence_transformers import CrossEncoder
import torch

from core.search import EduSearchHelper, SearchTarget
from vertexai.generative_models import GenerativeModel

# TutorMode = Literal["rag", "rag_mcp"]
# logger = logging.getLogger(__name__)

@dataclass
class EduRAGConfig:
    """Consolidated configuration for the prototype pipeline."""
    use_reranker: bool = True
    reranker_model_name: str = "BAAI/bge-reranker-v2-m3"
    llm_model_name: str = "gemini-2.5-flash" 
    initial_top_k: int = 30  # Expanded search depth for the reranker
    final_top_k: int = 5     # Polished context for the LLM
    device: str = "cuda" if torch.cuda.is_available() else "cpu"

class EduRAGTutor:
    def __init__(self, config: EduRAGConfig):
        self.config = config
        
        # 1. SETUP RERANKER (The "Judge")
        self.reranker = CrossEncoder(
            config.reranker_model_name, 
            device=config.device
        )
        
        # 2. SETUP GENERATOR (The "Brain")
        # genai.configure(api_key=gemini_key)
        self.llm = GenerativeModel(config.llm_model_name)

    def _rerank(self, query: str, chunks: list):
        """Re-sorts retrieved chunks using deep semantic cross-attention."""
        if not chunks: return []
        
        pairs = [[query, chunk.get('text', '')] for chunk in chunks]
        scores = self.reranker.predict(pairs)
        
        for i, score in enumerate(scores):
            chunks[i]['rerank_score'] = float(score)

        sorted_chunks = sorted(chunks, key=lambda x: x['rerank_score'], reverse=True)

        # 🔍 DEBUG SECTION
        print(f"DEBUG: sorted_chunks type is {type(sorted_chunks)}")
                    
        # Return top K sorted by the new judge score
        return sorted_chunks[:self.config.final_top_k]

    def generate_answer(self, question: str) -> dict:
        """The full RAG cycle: Search -> Rerank -> Augment -> Generate."""
        
        # STAGE 1: Hybrid Retrieval (The Logic from your test_retrieval_rrf)
        # This replaces the simple search with your high-quality RRF search.
        print(f"🔍 Searching for: {question}...")
        raw_chunks = self.config.search_helper.search(
            query=question, 
            top_k=self.config.initial_top_k
        )
        
        # STAGE 2: Precision Reranking
        # Even if RRF put the instructor email at #15, the reranker will move it to #1.
        refined_chunks = self._rerank(question, raw_chunks)
        
        # STAGE 3: Context Augmentation (Preparation for LLM)
        context_blocks = []
        for i, c in enumerate(refined_chunks, 1):
            source = c['metadata'].get('source', 'Lecture Slide')
            page = c['metadata'].get('page', '?')
            # Identifying OCR text helps the LLM understand diagram data
            text = c.get('text', '')
            context_blocks.append(f"SOURCE {i} (File: {source}, Page: {page}):\n{text}")
        
        context_str = "\n\n---\n\n".join(context_blocks)

        # STAGE 4: Generation with Gemini
        system_prompt = (
            "You are a helpful NLP AI Tutor. Explain concepts clearly using the provided context. "
            "If the text contains [VISUAL_CONTEXT], it means the info was in a slide diagram. "
            "Always cite your sources by their number (e.g., [Source 1])."
        )
        
        full_prompt = f"{system_prompt}\n\nCOURSE CONTEXT:\n{context_str}\n\nSTUDENT QUESTION: {question}"
        
        response = self.llm.generate_content(full_prompt)
        
        return {
            "answer": response.text,
            "used_sources": [c['metadata'].get('source') for c in refined_chunks],
            "top_score": refined_chunks[0]['rerank_score'] if refined_chunks else 0
        }


# class EduRAGTutor:
#     """
#     Orchestrates the end-to-end flow for answering a student's query:

#     1) Retrieve relevant chunks from vector DB(s) via EduSearchHelper.
#     2) Optionally rerank candidates.
#     3) Build a tutor-style prompt with context.
#     4) Call the underlying LLM (and, later, MCP tools when mode='rag_mcp').
#     """

#     def __init__(self, config: EduRAGConfig) -> None:
#         self.config = config
#         self.search_helper = config.search_helper
        
#         # Initialize reranker
#         if config.use_reranker:
#             try:
#                 self._reranker = CrossEncoder(
#                     config.reranker_model_name, 
#                     device=config.device,
#                     torch_dtype=torch.float16 if config.device == "cuda" else torch.float32
#                 )
#                 logger.info(f"Loaded reranker: {config.reranker_model_name}")
#             except Exception as e:
#                 logger.warning(f"Reranker load failed: {e}. Using score-based ranking.")
#                 self._reranker = None
#         else:
#             self._reranker = None

#         # Initialize LLM
#         try:
#             tokenizer = AutoTokenizer.from_pretrained(config.llm_model_name, trust_remote_code=True)
#             if tokenizer.pad_token is None:
#                 tokenizer.pad_token = tokenizer.eos_token
            
#             # For Phi-3-mini, we can load the model with 16-bit precision for efficiency
#             model = AutoModelForCausalLM.from_pretrained(
#                 config.llm_model_name, 
#                 torch_dtype=torch.float16 if config.device == "cuda" else torch.float32,
#                 device_map="auto" if config.device == "cuda" else None,
#                 trust_remote_code=True
#             )
            
#             # Initializing the text-generation pipeline with the loaded model and tokenizer
#             self._llm = pipeline(
#                 "text-generation",
#                 model=model,
#                 tokenizer=tokenizer,
#                 device_map="auto" if config.device == "cuda" else None,
#                 max_new_tokens=512,
#                 temperature=0.1,
#                 do_sample=True,
#                 pad_token_id=tokenizer.eos_token_id
#             )
#             logger.info(f"Loaded LLM: {config.llm_model_name} on {config.device}")
#         except Exception as e:
#             logger.error(f"LLM load failed: {e}")
#             raise

#     # ---------- public API ----------

#     def answer(
#         self,
#         query: str,
#         mode: TutorMode = "rag",
#         target: SearchTarget = "both",
#         table_filter: Optional[Dict[str, Any]] = None,
#         prose_filter: Optional[Dict[str, Any]] = None,
#         user_profile: Optional[Dict[str, Any]] = None,
#     ) -> Dict[str, Any]:
#         """
#         Main entrypoint used by TutorService.

#         Returns a dict like:
#         {
#             "answer": "...",
#             "context": [...],    # list of chunks used
#             "mode": "rag" | "rag_mcp",
#             "tool_calls": [...]  # later, for MCP
#         }
#         """
#         try:
#             # 1. Retrieve candidates
#             raw_results = self.search_helper.search(
#                 query=query,
#                 target=target,
#                 top_k=self.config.initial_top_k,
#                 table_filter=table_filter,
#                 prose_filter=prose_filter,
#             )

#             candidates = self._flatten_results(raw_results)
#             if not candidates:
#                 return {
#                     "answer": "I could not find any relevant material in the knowledge base.",
#                     "context": [],
#                     "mode": mode,
#                     "tool_calls": [],
#                 }

#             # 2. Optional rerank
#             if self.config.use_reranker and self._reranker is not None:
#                 candidates = self._rerank(query, candidates, top_k=self.config.final_top_k)
#             else:
#                 candidates = candidates[: self.config.final_top_k]

#             # 3. Build prompt
#             prompt = self._build_prompt(
#                 query=query,
#                 chunks=candidates,
#                 user_profile=user_profile,
#                 mode=mode,
#             )

#             # 4. Call LLM (and, later, MCP)
#             answer_text, tool_calls = self._call_llm(prompt=prompt, mode=mode)

#             return {
#                 "answer": answer_text,
#                 "context": candidates,
#                 "mode": mode,
#                 "tool_calls": tool_calls,
#             }
#         except Exception as e:
#             logger.error(f"Error in answer(): {e}")
#             return {
#                 "answer": f"Sorry, I encountered an error: {str(e)}",
#                 "context": [],
#                 "mode": mode,
#                 "tool_calls": [],
#             }

#     # ---------- internal helpers ----------

#     def _flatten_results(self, res: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
#         """
#         Flatten { 'tables': [...], 'prose': [...] } into a single scored list.
#         """
#         combined: List[Dict[str, Any]] = []

#         for kind in ("tables", "prose"):
#             for item in res.get(kind, []):
#                 combined.append(
#                     {
#                         "id": item.get("id"),
#                         "score": item.get("score", 0.0),
#                         "text": item.get("text", ""),
#                         "metadata": {
#                             "chunk_type": kind,
#                             **item.get("metadata", {}),
#                         },
#                     }
#                 )

#         combined.sort(key=lambda x: x["score"], reverse=True)
#         return combined

#     def _rerank(
#         self,
#         query: str,
#         candidates: List[Dict[str, Any]],
#         top_k: int,
#     ) -> List[Dict[str, Any]]:
#         """
#         CrossEncoder-based reranking using bge-reranker.
#         """
#         pairs = [[query, c["text"]] for c in candidates]
#         scores = self._reranker.predict(pairs)
        
#         for i, score in enumerate(scores):
#             candidates[i]["rerank_score"] = float(score)
        
#         return sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)[:top_k]

#     def _build_prompt(
#         self,
#         query: str,
#         chunks: List[Dict[str, Any]],
#         user_profile: Optional[Dict[str, Any]],
#         mode: TutorMode,
#     ) -> str:
#         """
#         Build a system+user style prompt tailored to an educational tutor.
#         """
#         # Enhanced system instruction
#         system_msg = (
#             "You are an expert AI tutor. "
#             "Use ONLY the provided course materials to explain concepts clearly, "
#             "step by step, at the student's level. "
#             "Always cite sources by their numbers. "
#             "If information is missing or unclear, say so instead of guessing. "
#             "Structure answers with clear steps and examples when helpful."
#         )

#         if user_profile:
#             level = user_profile.get("level", "general")
#             system_msg += f" The student is at {level} level."

#         # Attach context with source citations
#         context_blocks: List[str] = []
#         for i, c in enumerate(chunks, start=1):
#             meta = c.get("metadata", {})
#             location = ""
#             if "page" in meta:
#                 location = f" (Page: {meta['page']})"
#             elif "section" in meta:
#                 location = f" (Section: {meta['section']})"
            
#             # Truncate long chunks for prompt
#             text = c.get("text", "")[:1000] + "..." if len(c.get("text", "")) > 1000 else c.get("text", "")
#             context_blocks.append(
#                 f"[Source {i}]{location}:\n{text}"
#             )

#         context_str = "\n\n".join(context_blocks)

#         prompt = (
#             f"<|system|>\n{system_msg}\n<|end|>\n\n"
#             f"<|user|>\nContext (course materials):\n{context_str}\n\n"
#             f"Student question: {query}\n<|end|>\n\n"
#             f"<|assistant|>\n"
#         )

#         return prompt

#     def _call_llm(
#         self,
#         prompt: str,
#         mode: TutorMode,
#     ) -> Tuple[str, List[Dict[str, Any]]]:
#         """
#         Generate response using Phi-3-mini. Returns (answer_text, tool_calls).
#         """
#         if mode == "rag_mcp":
#             # Future: parse tool_calls from response
#             pass
        
#         try:
#             response = self._llm(prompt, return_full_text=False)[0]
#             generated_text = response['generated_text'].strip()
            
#             # Extract just the assistant response
#             if "<|assistant|>" in generated_text:
#                 answer = generated_text.split("<|assistant|>")[-1].strip()
#             else:
#                 answer = generated_text
            
#             # Clean up any artifacts
#             answer = answer.replace("<|end|>", "").replace("<|im_end|>", "").strip()
            
#             return answer, []
#         except Exception as e:
#             logger.error(f"LLM generation failed: {e}")
#             return "Sorry, I had trouble generating a response.", []
