from dataclasses import dataclass
from typing import Dict, Any, List, Optional

# from torch import norm
from core.chunking import ProseChunkConfig, ProseChunker
from core.documents import EduDocumentLoader
from core.preprocessing import ProseTextPreprocessor, ProsePreprocessConfig, OCREnricher
from core.preprocess_query import preprocess_query
from core.intent_router import StageZeroRouter
# import fitz  # PyMuPDF
import pymupdf as fitz
from sentence_transformers import CrossEncoder
from vertexai.generative_models import GenerativeModel

import numpy as np
#from core.documents import DocumentMetadata

# from core.search import EduSearchHelper, SearchConfig
# from core.rag import EduRAGTutor, EduRAGConfig, TutorMode
# from config import config as app_config  # your AppConfig from config.py
from core.vectordb import VectorDBConfig, EduVectorDB


from core.vectordb import EduVectorDB
from core.rag import EduRAGConfig

from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Callable    
from core.embeddings import ProseEmbeddingCreator, ProseEmbeddingConfig
from core.bm25_encoder import BM25Manager
import os

import vertexai
from vertexai.generative_models import GenerativeModel

from core.rag import EduRAGTutor
from fastmcp import Client
import regex as re

from core.governance import GovernanceLayer


@dataclass
class TutorResponse:
    answer: str
    context: list[Dict[str, Any]]


class TutorService:
    """
    High-level service used by Flask routes.
    It delegates to EduRAGTutor for retrieval + generation.
    """
    def __init__(self, config: EduRAGConfig, pinecone_api_key: str, google_creds_path: str = "google_vision_key.json") -> None:
        self.pinecone_api_key = pinecone_api_key
        self.config = config

        # 🔑 Link the JSON key to your session
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
        
        # 🧠 Initialize the Brain using your Project ID
        vertexai.init(project="ornate-fragment-477923-t2", location="global")
        self.llm = GenerativeModel("gemini-2.5-flash")

        
        self.tutor_engine = EduRAGTutor(config=config)

        # Provision the Reranker (Local)
        self.reranker = CrossEncoder(
            config.reranker_model_name, 
            device=config.device
        )
        
        # Provision the LLM (Cloud)
        # genai.configure(api_key=gemini_key)
        # self.llm = genai.GenerativeModel(config.llm_model_name)

        self.database_dir = r"C:\Users\ks1679\Desktop\Research - Pain Points (Edu Domain)\AI Tutor Prototype\Database"
        # 2. Add this for your Project Root (Where app.py and the weights are)
        self.root_dir = r"C:\Users\ks1679\Desktop\AI Tutor - v1.1"

        # 1. Initialize Global Configurations and Classes
        config = ProsePreprocessConfig(
            ocr_char_threshold=100, 
            force_ocr_on_congested=True,
            google_creds_path=google_creds_path
        )

        # 2.1. Load educational documents (local PDFs/TXTs) once at startup
        # loader = EduDocumentLoader(base_dir=r"C:\\Users\\ks1679\\Desktop\\Research - Pain Points (Edu Domain)\\AI Tutor Prototype\\Database")
        # self.raw_docs = loader.load_many(
        #     [
        #         "NLP-Week1-sp-2026.pdf",
        #         "NLP-Week2-sp-2026.pdf",
        #     ],
        #     topic="Natural Language Processing",         # example tag
        #     level="Masters",                             # example level
        #     course_id="CSCE_5290_NLP" 
        # )

        # 2.2. Update metadata for each document (Page)
        # Since load_many returns a list of EduDocument objects, we loop through them:
        # for doc in self.raw_docs:
        #     # Ensure the metadata object exists and update its fields
        #     doc.metadata.topic = "Natural Language Processing"
        #     doc.metadata.level = "Masters"
        #     doc.metadata.course_id = "CSCE_5290_NLP"

        
        # 3. Initialize Enrichment and Cleaning Engines
        # pre_cfg = ProsePreprocessConfig()
        # enricher = OCREnricher(config)
        # preprocessor = ProseTextPreprocessor(config)

        # 4. Orchestration Loop: Enrich and Clean page-by-page
        # self.clean_docs = []

        # Mapping for fitz to access the physical PDF for OCR signals - A,B and C
        # current_fitz_doc = None
        # current_source = ""

        # for doc in self.raw_docs:
        #     # --- Move the path calculation ---
        #     filename = doc.metadata.source
        #     full_pdf_path = os.path.join(self.database_dir, filename)

        #     # Open/Re-open the PDF handle only when the source file changes
        #     if full_pdf_path != current_source:
        #         if current_fitz_doc: current_fitz_doc.close()
        #         current_fitz_doc = fitz.open(full_pdf_path)
        #         current_source = doc.metadata.source
            
            # Access the specific page in the PDF to check for images/vectors
            # page_idx = doc.metadata.extra.get("page", 1) - 1
            # page_obj = current_fitz_doc[page_idx]

            # # --- STEP A: OCR Enrichment (Phase 1 Logic) ---
            # # Checks if page is 'thin' or 'congested' and calls Google Vision if needed
            # enriched_text = enricher.enrich_page(page_obj, doc.text)
            
            # # --- STEP B: Prose Cleaning ---
            # # Merges PDF/OCR sequence and fixes hyphens/bullets/casing
            # # We treat the enriched_text as the primary input for the cleaner
            # cleaned_text = preprocessor._clean_text(enriched_text)
            
            # # --- STEP C: Reconstruct the EduDocument ---
            # doc.text = cleaned_text

            # 2. Update the metadata flag BEFORE appending
            # This ensures we know if THIS specific page used the Vision API
        #     doc.metadata.extra["has_ocr"] = "[EXTRACTED_FROM_IMAGE_OCR]" in enriched_text
            
        #     # 3. Add the finished document to your cleaned collection
        #     self.clean_docs.append(doc)

        # if current_fitz_doc: current_fitz_doc.close()
        # print(f"✅ Preprocessed {len(self.clean_docs)} documents with OCR enrichment")


        # 5. Chunk cleaned documents into prose chunks (with metadata)
        # Convert EduDocument → page dicts (simple transform)
        # clean_prose_pages = [{"page": d.metadata.extra.get("page", i+1), 
        #                     "clean_text": d.text, 
        #                     "file_path": d.metadata.source,
        #                     "metadata": {
        #                                 "course_id": d.metadata.course_id,
        #                                 "topic": getattr(d.metadata, 'topic', 'Unknown'), 
        #                                 "level": getattr(d.metadata, 'level', 'Unknown')  # 
        #                             }
        #                         }
        #                     # "course_id": d.metadata.course_id}
        #                     for i, d in enumerate(self.clean_docs)]
        
        # # print(f"Course ID for first page:  {clean_prose_pages[0].course_id}")
        # print(f"🔍 DEBUG: Created {len(clean_prose_pages)} prose pages")

        # chunk_cfg = ProseChunkConfig()
        # chunker = ProseChunker(config=chunk_cfg)
        # self.prose_chunks = chunker.chunk_documents(clean_prose_pages)
        # print(self.prose_chunks[0])
        # print(type(self.prose_chunks))

        # 6. Sparse vectors through BM25 encodings
        # raw_slide_texts = [chunk[1]["text"] for chunk in self.prose_chunks]
        self.bm25 = BM25Manager()
        self.bm25.filepath = os.path.join(self.root_dir, "bm25_weights.json")
        self.bm25.load_model()
        # self.bm25.fit_and_save(raw_slide_texts)

        # Then loop through your chunks to upsert them
        # for chunk in raw_slide_texts:
        #     sparse_vec = bm25.encode_corpus_chunk(chunk["text"])


        # embed_model.load()  # Load the model once at startup
        # 7. EMBEDDINGS CREATION =====
        # 7a. Load SentenceTransformer directly (NO wrapper needed)
        # print("🤖 Loading Sentence Transformers embeddings...") 
        # embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        

        # 7b. Define embed_fn for ProseEmbeddingCreator
        # def prose_embed_fn(texts: List[str]) -> List[List[float]]:
        #     """Encode texts → normalized embeddings."""
        #     embeddings = embed_model.encode(texts, normalize_embeddings=True)
        #     return embeddings.tolist()

        # 7c. Create embedding creator and generate payloads
        # embed_cfg = ProseEmbeddingConfig()
        # embedding_creator = ProseEmbeddingCreator(
        #     config=embed_cfg,
        #     embed_fn=prose_embed_fn
        # )

        # self.embedding_payloads = embedding_creator.build_embeddings(self.prose_chunks)
        # print(f"EMBEDDING DIMENSION: {len(self.embedding_payloads[0]['values'])}") 
        # print(f"✅ Embeddings type: {type(self.embedding_payloads[0]['values'])}")

        # 8. Inject the sparse vectors into each existing payload dictionary
        # for chunk, payload in zip(self.prose_chunks, self.embedding_payloads):
        #     chunk_text = chunk[1]["text"]
            
        #     # Generate the BM25 dictionary and add it to the payload
        #     sparse_vec = self.bm25.encode_corpus_chunk(chunk_text)
        #     payload["sparse_values"] = sparse_vec
    

        # 9. Initialize vector database and upload embeddings
        self.vectordb = EduVectorDB(
            VectorDBConfig(api_key=self.pinecone_api_key,
                           index_name="ai-tutor", dimension=384)
        )
        # self.vectordb.upload(self.embedding_payloads, namespace="prose")    

        # 6. 🔥 RAG SETUP (ONCE at startup)
        # search_config = SearchConfig(
        #             prose_index_name="ai-tutor",  # YOUR index
        #             prose_namespace="prose",             # YOUR namespace  
        #             prose_model_name="sentence-transformers/all-MiniLM-L6-v2"
        #         )

        # self.search_helper = EduSearchHelper(search_config, self.pinecone_api_key)
        # self.search_helper.init_clients_and_models()  # 🔥 Connects to YOUR vectordb

        # rag_config = EduRAGConfig(search_helper=self.search_helper)
        # self.rag_tutor = EduRAGTutor(rag_config)      

        # 7. 🆕 SAME MODEL for RETRIEVAL as CORPUS!
        # self.embedding_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        self.embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        # 🟢 Initialize Governance Layer 
        self.governance = GovernanceLayer(self.tutor_engine.llm)

        # 🟢 Initialize the intent router
        self.router = StageZeroRouter(self.tutor_engine.llm)

        self.youtube_mcp_path = r"C:\Users\ks1679\Desktop\AI Tutor - v1.1\core\youtube_MCP.py"

    # ASYNC method for the youtube MCP initialization
    async def get_video_info(self, url):
        """Helper to fetch transcript from the MCP server."""
         # 1. Connect to your local MCP server
        client = Client(self.youtube_mcp_path)
        async with client:
            transcript = await client.call_tool("get_youtube_transcript", {"video_url": url})
            return transcript

    async def search_youtube(self, topic):
        """Helper to search and summarize via MCP server."""
        client = Client(self.youtube_mcp_path)
        async with client:
            result = await client.call_tool("search_and_summarize_youtube", {"topic": topic})
            return result
        

        # # 8. Same pipeline for query
        # self.preprocessor = preprocessor()

        # def preprocess_query(self, raw_query: str) -> str:
        #     """Apply SAME preprocessing to query as used for corpus"""
        #     # Create a temporary "document" structure for the preprocessor
        #     temp_doc = {
        #         "text": raw_query,
        #         "metadata": {}
        #     }
            
        #     # Use the SAME preprocessor
        #     processed = self.preprocessor.preprocess_text(temp_doc["text"])
            
        #     return processed
    
    # 8. Test RAG retrieval separately (without LLM) to debug vector search
    def test_retrieval_rrf(self, question: str, top_k: int = 5) -> list:
        print(f"\n🔍 Testing RRF Hybrid Retrieval: '{question}'")
        
        preprocessed_query = preprocess_query(question)
        
        # 1. Generate both vectors
        q_emb = self.embedding_model.encode([preprocessed_query], normalize_embeddings=True)[0]
        dense_vec = [float(x) for x in q_emb]
        sparse_vec = self.bm25.encode_student_query(preprocessed_query)
        
        # 2. Execute Pure Dense Search (Semantic)
        dense_response = self.vectordb.index.query(
            vector=dense_vec,
            namespace="prose",
            top_k=10, # Fetch a bit more than top_k for better fusion overlap
            include_metadata=True
        )
        
        # 3. Execute Pure Sparse Search (BM25)
        # Pinecone requires a dense vector, so we send an array of zeros
        dummy_dense = [0.0] * len(dense_vec) 
        sparse_response = self.vectordb.index.query(
            vector=dummy_dense,
            sparse_vector=sparse_vec,
            namespace="prose",
            top_k=10,
            include_metadata=True
        )
        
        # 4. Perform Reciprocal Rank Fusion (RRF)
        rrf_scores = {}
        fused_results = {}
        k_constant = 60 # Standard RRF smoothing constant
        
        # Process Dense Ranks
        for rank, match in enumerate(dense_response['matches'], start=1):
            chunk_id = match['id']
            rrf_scores[chunk_id] = 1.0 / (k_constant + rank)
            fused_results[chunk_id] = match # Store the metadata payload
            
        # Process Sparse Ranks
        for rank, match in enumerate(sparse_response['matches'], start=1):
            chunk_id = match['id']
            if chunk_id in rrf_scores:
                rrf_scores[chunk_id] += 1.0 / (k_constant + rank)
            else:
                rrf_scores[chunk_id] = 1.0 / (k_constant + rank)
                fused_results[chunk_id] = match
                
        # 5. Sort by highest RRF score and slice the Top 5
        sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        # 6. Extract and return the final chunks
        final_matches = []
        print("\n✅ Found relevant chunks (RRF Sorted):")
        for i, (chunk_id, score) in enumerate(sorted_chunks, 1):
            match_data = fused_results[chunk_id]
            chunk_text = match_data['metadata'].get('text', '')[:150].replace('\n', ' ')
            
            # Extract the page number (default to 'N/A' if it's missing)
            page_num = match_data['metadata'].get('page', 'N/A')
            course_id = match_data['metadata'].get('course_id', 'Unknown Course')

            print(f"   {i}. RRF Score: {score:.4f} | Course: [{course_id}] | File: {match_data['metadata'].get('filepath', 'Unknown')} | Page: {page_num}")
            print(f"      {chunk_text}...\n")
            final_matches.append({
                'text': match_data['metadata'].get('text', ''),
                'metadata': match_data['metadata'],
                'rrf_score': score
            })
           

        # sample = final_matches[0]
        # print(f"Chunk 0 Type: {type(sample)}")
        # print(f"Chunk 0 Content: {str(sample)[:200]}...")

        return final_matches

    
    async def generate_answer(self, question: str) -> dict:
        """
        Pure Agentic RAG execution with Stage 0 Multi-Agent Routing: 
        Uses an Intent Router (Switchboard) to determine the path before retrieval, 
        then uses the Escape Hatch and NLI Judge for grounded verification.
        """
        try:
            # ==========================================
            # PROMPT GENERATION & FALLBACK HELPERS
            # ==========================================
            
            def build_governed_prompt(intent_specific_prompt: str, active_policies: list, detected_level: str) -> str:
                """
                Acts as a middleware wrapper. Injects dynamic governance policies 
                and strictly enforces them against LLM pre-training bias
                """
                if not active_policies:
                    policy_string = "- Standard academic rigor and neutral tone."
                else:
                    policy_string = "\n".join([f"- {policy}" for policy in active_policies])
                
                governed_prompt = f"""
                SYSTEM IDENTITY: You are a specialized, Culturally Responsive AI Tutor. You are currently teaching a {detected_level}. 
                You MUST adopt the cultural context and pedagogical style dictated by the policies below. You are NOT a generic AI. 
                
                CRITICAL GOVERNANCE POLICIES FOR THIS USER ({detected_level}):
                {policy_string}
                
                MANDATORY INSTRUCTIONS (FAILURE TO FOLLOW = SYSTEM VIOLATION):
                1. NO GENERIC OR FICTIONAL ANALOGIES: You are explicitly FORBIDDEN from using Western textbook examples (apples, widgets, lemonade stands) OR inventing generic student scenarios (like "school canteens").
                2. NO GLOBALIZED CONSUMERISM: Do NOT bypass cultural rules by using generic global youth tropes (e.g., video game shortages, sneakers, smartphones, or generic mall stores).
                3. FORCED MULTI-DIMENSIONAL COMPLIANCE: You MUST invent an analogy that simultaneously satisfies the geographic Cultural policy, the Infrastructure Mandate, AND any Seasonal/Temporal rules provided above. 
                   - Example: If Culture is "Sub-Saharan Africa" and Infrastructure is "LOW", use mobile-money (M-Pesa) or off-grid solar, not fiber-optic cables.
                   - Example: If the user is in the Southern Hemisphere, remember December is Summer.
                4. LINGUISTIC MIRRORING & CONFLICT RESOLUTION: If the student uses specific regional slang (e.g., "have a doubt", "prepone"), naturally adopt it to build rapport. If their slang conflicts with their target curriculum (e.g., South Asian slang but asking about US History), speak in their dialect but teach using the strict academic analogies required by the curriculum.
                5. NEUTRALITY & SOURCE: Provide a balanced view and explicitly state if data is general knowledge.
                6. NO HALLUCINATION: If a piece of specific data (like a date or name) is not in the context, admit it. Do not invent facts to force an analogy.
                

                =========================================
                TASK-SPECIFIC INSTRUCTIONS & CONTEXT:
                =========================================
                {intent_specific_prompt}
                """
                return governed_prompt


            # ---------------------------------------------------------
            # HELPER: THE AGENTIC FALLBACK (Now Policy-Enforced!)
            # ---------------------------------------------------------
            def trigger_fallback(reason: str):
                print(f"⚠️ Triggering Agentic Fallback. Reason: {reason}")
                
                # 1. Define ONLY the task-specific instructions (Governance handles the persona/tone)
                task_specific_prompt = f"""
                The student has asked a question that falls outside the specific academic syllabus, 
                or the available course materials do not contain the answer.
                
                TASK:
                1. Explain the concept using your internal knowledge base.
                2. Explicitly state at the very beginning that your advice is not drawn from specific course materials.
                3. DO NOT give a "general" or generic answer. You MUST aggressively tailor the examples, analogies, and tone to match the CRITICAL GOVERNANCE POLICIES provided above.
                4. Focus on teaching the underlying concept effectively while mirroring the user's conversational dialect.
                5. Because this is general knowledge, you MUST provide 2-3 real URLs to authoritative websites (like Wikipedia, Python Docs, Khan Academy) at the very bottom of your response under the heading "Suggested Links:".
                6. [VISUAL & DIAGRAM MANDATE]: If the user explicitly asks for a "diagram," "flowchart," or visual representation (e.g., "A -> B"), you MUST NOT use standard paragraphs. You must generate the response using strict ASCII art arrows (->, =>, |) or structured Markdown code blocks to visually map the relationship between components.
                STUDENT QUESTION: {question}
                """
                
                # 2. 🟢 INJECT GOVERNANCE! 
                # (This uses the variables generated in STAGE 0 of your main loop)
                final_governed_prompt = build_governed_prompt(
                    intent_specific_prompt=task_specific_prompt, 
                    active_policies=active_policies, 
                    detected_level=detected_level
                )
                
                # 3. Generate the response using the strict, governed prompt
                response = self.tutor_engine.llm.generate_content(final_governed_prompt)
                answer_text = response.text if response else "Error generating fallback response."
            
                print("\n" + "="*60)
                print(f"🧠 AGENTIC FALLBACK RESPONSE (Persona: {detected_level}):")
                print("="*60)
                print(answer_text)
                print("="*60 + "\n")
                
                return {
                    "answer": answer_text,
                    "sources": [f"🧠 Agentic Router (Base LLM) - Trigger: {reason}"],
                    "confidence_score": "N/A (Agentic Pivot)"
                }


            
            # ==========================================
            # STAGE 0: GOVERNANCE LAYER INVOKE
            # ==========================================

            # HIGH-LEVEL FLOW:
            # [User Query] 
            #   ➔ 1. detect_implicit_persona()   | Calculates Confidence & Dimensions (1-10)
            #   ➔ 2. handle_exceptions()         | Solves Trust Paradox (Default-to-High OR User Override)
            #   ➔ 3. generate_final_policy()     | Translates numbers into strict Prompt Text
            #   ➔ [Outputs: detected_level, active_policies] -> Sent to Prompt Builder later
            # ==========================================

            print("\n" + "="*60)
            print(f"🧠 STAGE 0: Routing to Governance Layer...")

            # 1. Detect
            raw_profile = self.governance.detect_implicit_persona(question)
            
            # 2. Handle Exceptions
            exception_check = self.governance.handle_exceptions(raw_profile)
            
            if exception_check["status"] == "ASK_USER":
                # PAUSE THE SYSTEM! Return the override question directly to the UI/Terminal.
                return exception_check["override_message"] 
                
            # 3. Finalize Policies
            resolved_profile = exception_check["resolved_profile"]
            policy_list = self.governance.generate_final_policy(resolved_profile)
            
            # Ready for STAGE 2 / STAGE 3
            detected_level = resolved_profile.get("persona_level", "Student")
            active_policies = "\n".join([f"- {p}" for p in policy_list])
            
            print(f"✅ Persona Detected: {detected_level}")
            print(f"✅ Active Policies loaded for generation.")



            # ==========================================
            # STAGE 1: THE INTENT ROUTER (The Switchboard)
            # ==========================================
            print("\n" + "="*60)
            print(f"🚦 STAGE 1: Routing Query...")
            
            # 1. Classify the intent
            intent = self.router.classify_intent(question)
            print(f"🎯 Decision: Route to [{intent}]")
            print("="*60)

            # 2. Immediate Bypass Logic
            if intent == "GENERAL_ASSISTANCE":
                print("\n🧠 Bypassing RAG. Routing directly to Base LLM...")
                return trigger_fallback("Stage 0 Router identified general assistance query.")
                
            elif intent == "YOUTUBE_SEARCH":
                print("\n📺 Routing to YouTube MCP Server...")
                # 1. Check if the user already provided a URL
                # Simple regex to find any youtube.com or youtu.be link
                url_match = re.search(r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be)\/\S+)', question)
                transcript = ""
                context_prefix = "" 
                video_url = ""

                # Use the path stored in __init__ for consistency
                async with Client(self.youtube_mcp_path) as mcp:
                    if url_match:  # SCENARIO A: Summarize the video for youtube link provided by user
                        video_url = url_match.group(0)
                        print(f"🔗 URL Found: {video_url}. Extracting transcript...")
                        
                        # Call tool
                        result = await mcp.call_tool("get_youtube_transcript", {"video_url": video_url})
                        transcript = result.content[0].text if hasattr(result, 'content') else str(result)
                        context_prefix = f"The student provided this video: {video_url}."
                    
                    else:
                        # SCENARIO B: Search YouTube for a topic
                        # We use the whole question as the 'topic'
                        print(f"Searching YouTube for: '{question}'")

                        # 1. Invoke the search tool       
                        result = await mcp.call_tool("search_and_summarize_youtube", {"topic": question})
                        # Result includes title, URL, and transcript

                        # 2. Extract the content safely from the MCP response
                        if hasattr(result, 'content') and result.content:
                            transcript = result.content[0].text
                        else:
                            transcript = str(result)
                        
                        context_prefix = "I searched YouTube to find a relevant video for you."


                # 🟡 UNIFIED LLM BLOCK (Moved one level left to handle BOTH Scenarios)      
                if transcript:
                    # 🟢 EXTRA FIX: If video_url is empty (Search Scenario), pluck it from the transcript
                    if not video_url and "VIDEO_URL: " in transcript:
                        url_search = re.search(r'VIDEO_URL: (https?://\S+)', transcript)
                        if url_search:
                            video_url = url_search.group(1)


                    # 🟢 ADD THIS: Simple error handling
                    if transcript.startswith("Error"):
                        print(f"❌ MCP Tool Error: {transcript}")
                        return f"I encountered an issue with that video: {transcript}"
  
                        
                    # 🟢 ADD THIS: Final LLM Prompting logic 
                    # (Don't forget to actually call the LLM with the context!)
                    print(f"✅ Context ready. Sending to Gemini...")
                    
                    full_prompt = f"""
                    SYSTEM: You are a specialized AI Tutor. You MUST use the provided transcript to answer.
                    USER CONTEXT: {context_prefix}
                    USER QUESTION: {question}

                    TRANSCRIPT DATA (USE THIS):
                    {transcript[:12000]}

                    INSTRUCTIONS:
                    1. Do NOT act like a general AI. Act as if you have just watched the video provided in the transcript.
                    2. Provide a detailed summary based ONLY on the transcript above.
                    3. Mention the video title in your first sentence.
                    4. YOU MUST explicitly provide the video URL ({video_url}) on its own line at the very beginning of your response so the student can click it.
                    """
                  
                    response = self.llm.generate_content(full_prompt)

                    print("\n--- 🤖 Gemini Summary Output ---")
                    print(response.text)

                    # 🟢 Explicitly print the source link
                    if video_url:
                        print(f"\n🔗 Source Link: {video_url}")
                    print("-------------------------------\n")

                    return {
                            "answer": response.text,
                            "sources": [video_url] if video_url else ["YouTube Search Result"]
                        }
                
    

                # return {"answer": "I'll help you search for a video on that. (MCP Integration Pending)", "sources": []}

            # 3. Determine the Metadata Filter for Course Queries
            if intent == "COURSE_ML":
                course_filter = {"course_id": "CSCE_5200_ML"}
            else: 
                # Default to NLP for COURSE_NLP or unidentified academic queries
                course_filter = {"course_id": "CSCE_5290_NLP"}

            # ==========================================
            # STAGE 2 & 3: RETRIEVAL & RERANKING
            # ==========================================
            print(f"\n📡 Step 1: Retrieving candidates from Pinecone...")
            
            # 🟢 UPDATED: Passing the metadata_filter into your RRF retrieval
            raw_chunks = self.test_retrieval_rrf(
                question, 
                top_k=self.config.initial_top_k, 
                # metadata_filter=course_filter
            )
            
            refined_chunks = []
            if raw_chunks:
                print(f"⚖️  Step 2: Reranking top {len(raw_chunks)} chunks locally...")
                refined_chunks = self.tutor_engine._rerank(question, raw_chunks)

            # Safety check if Pinecone returned nothing even with the filter
            if not refined_chunks:
                return trigger_fallback(f"Zero documents retrieved from {intent} database.")

            # ==========================================
            # STAGE 3: STRICT DRAFT GENERATION (With Escape Hatch)
            # ==========================================
            print(f"📝 Step 3: Drafting strict RAG response (checking context sufficiency)...")
            context_blocks = []
            for i, chunk in enumerate(refined_chunks, 1):
                course_id = chunk['metadata'].get('course_id', 'Unknown Course')
                source = chunk['metadata'].get('filepath', 'Unknown File')
                page = chunk['metadata'].get('page', 'N/A')
                text = chunk['metadata'].get('text', '')
                context_blocks.append(f"SOURCE {i} [Course: {course_id}, File: {source}, Page: {page}]:\n{text}")
                # context_blocks.append(f"SOURCE {i} [File: {source}, Page: {page}]:\n{text}")

            context_str = "\n\n---\n\n".join(context_blocks)
            
            draft_prompt = f"""
            You are a professional AI Tutor. Answer the student's question based STRICTLY on the provided course context.
            
            GUIDELINES:
            1. INLINE CITATIONS: When stating a fact, you MUST cite it using the exact file and page number provided in the context header. Use this exact format template: [File: <insert_exact_filename>, Page: <insert_exact_page>]. Do NOT just write [Source 1].
            2. THE ESCAPE HATCH: If the context does NOT contain the exact answer, you MUST output ONLY this exact string: INSUFFICIENT_CONTEXT
            3. PARTIAL MATCHES: If the context mentions the topic, but is missing the SPECIFIC detail asked, DO NOT explain what is missing. You MUST output ONLY: INSUFFICIENT_CONTEXT
            4. TOPIC MISMATCH: If the student asks about a specific person/concept (e.g., Shannon), and the context is about someone else (e.g., Markov), DO NOT summarize the context. You MUST output ONLY: INSUFFICIENT_CONTEXT
                        
            COURSE CONTEXT:
            {context_str}
            
            STUDENT QUESTION: {question}
            """
            
            draft_response = self.tutor_engine.llm.generate_content(draft_prompt)
            draft_answer = draft_response.text.strip() if draft_response else ""

            # Check if the LLM pulled the Escape Hatch during generation
            if "INSUFFICIENT_CONTEXT" in draft_answer:
                print("\n" + "="*60)
                print("🛡️ [STEP 3 ROUTING] ESCAPE HATCH PULLED")
                print("Diagnosis: Safe Refusal. The context lacked specific details.")
                print("Action: Bypassing the NLI Judge to save latency. Routing to General Fallback...")
                print("="*60 + "\n")
                return trigger_fallback("LLM determined context was insufficient (Escape Hatch pulled)")

            # ==========================================
            # STAGE 4: THE VERIFICATION AGENT (Post-Generation NLI)
            # ==========================================
            print(f"🕵️ Step 4: Verification Agent (LLM-Judge) validating evidence-claim entailment...")
            judge_prompt = f"""
            You are a strict NLI (Natural Language Inference) Entailment Judge.
            Read the CONTEXT, then evaluate the DRAFT ANSWER.
            
            Your ONLY job is to determine if the DRAFT ANSWER is 100% mathematically and factually entailed by the CONTEXT.
            If the DRAFT ANSWER hallucinates details, uses outside knowledge, or makes claims not explicitly found in the CONTEXT, you must reject it.
            
            CONTEXT:
            {context_str}
            
            DRAFT ANSWER:
            {draft_answer}
            
            If fully entailed by the context, output exactly: PASS
            If it contains hallucinations or ungrounded claims, output exactly: FAIL
            """
            
            judge_verdict = self.tutor_engine.llm.generate_content(judge_prompt).text.strip()

            # Catch overconfident LLM hallucinations post-generation
            if "FAIL" in judge_verdict:
                print("\n" + "="*60)
                print("🛑 [STEP 4 ROUTING] NLI JUDGE VETO")
                print("Diagnosis: Hallucination Detected! The draft contained ungrounded facts.")
                print("Action: Blocking false citation. Routing to General Fallback...")
                print("="*60 + "\n")
                return trigger_fallback("Verification Agent Detected Hallucination/Entailment Failure")


            # ==========================================
            # STAGE 5: SUCCESSFUL GROUNDED OUTPUT
            # ==========================================
            print(f"✅ Step 5: Verification Passed. Returning strictly grounded answer.")
            print("\n============================================================")
            print("📚 VERIFIED RAG RESPONSE (Grounded Course Context):")
            print("============================================================")
            print(draft_answer)
            print("\n")

            return {
                "answer": draft_answer,
                "sources": [c['metadata'].get('source') for c in refined_chunks],
                "confidence_score": "High (Verified by Agent)"
            }
          
            
        except Exception as e:
            print(f"❌ Generation Error: {e}")
            return {"answer": f"Error: {str(e)}", "sources": [], "confidence_score": "Error"}




    # 9. Main method to ask the tutor a question (RAG end-to-end)
    # async def ask_tutor(self, question: str):       
    #     return self.rag_tutor.answer(question)

            
    