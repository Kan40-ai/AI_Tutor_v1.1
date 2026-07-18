import json

class StageZeroRouter:
    def __init__(self, llm_client):
        # Pass your existing Gemini Flash client in here
        self.llm = llm_client 

    def classify_intent(self, user_query: str) -> str:

        # ── Deterministic keyword pre-screen ──────────────────────────────
        # These patterns are unambiguous — no LLM call needed.
        # Prevents routing instability for high-frequency course admin queries.
        query_lower = user_query.lower()

        # Unambiguous YouTube signals — explicit video request words only
        YOUTUBE_KEYWORDS = ["youtube.com", "youtu.be", "youtube video", "find a video",
                            "search youtube", "video tutorial"]

        # Unambiguous course admin signals — specific enough to not false-positive
        NLP_ADMIN_KEYWORDS = ["professor of nlp", "nlp instructor", "nlp professor",
                            "nlp course email", "csce 5290", "nlp syllabus",
                            "nlp office hour", "nlp prerequisite", "nlp grading",
                            "week 1 nlp", "week 2 nlp"]

        ML_ADMIN_KEYWORDS  = ["csce 5200", "ml course instructor", "ml professor",
                            "machine learning course syllabus"]

        if any(kw in query_lower for kw in YOUTUBE_KEYWORDS):
            return "YOUTUBE_SEARCH"
        if any(kw in query_lower for kw in ML_ADMIN_KEYWORDS):
            return "COURSE_ML"
        if any(kw in query_lower for kw in NLP_ADMIN_KEYWORDS):
            return "COURSE_NLP"
        

        prompt = f"""
        You are a strict intent classifier for a University AI Tutor system.
        Classify the user query into EXACTLY ONE of these four categories.

        CATEGORY DEFINITIONS:

        COURSE_NLP: Choose this for ANY query about:
        - NLP technical concepts (text mining, linguistic models, tokenisation,
        n-grams, transformers, conversational AI, etc.)
        - Anything about the NLP course logistics: instructor name, professor name,
        email address, office hours, office location, syllabus, grading,
        prerequisites, weekly topics, course schedule, assignments.
        - If the query mentions "NLP course" or asks who teaches it, this is
        ALWAYS COURSE_NLP regardless of how the question is phrased.

        
        YOUTUBE_SEARCH: HIGHEST PRIORITY — choose this when the user explicitly
        asks for a video, uses the word "YouTube", or provides a YouTube link.

        GENERAL_ASSISTANCE: Choose this ONLY for queries completely unrelated to
        NLP or ML — greetings, Python debugging, personal advice, well-being, etc.
        Never choose this if the query mentions NLP or ML course details.

        DECISION RULE: When in doubt between COURSE_NLP and GENERAL_ASSISTANCE,
        always choose COURSE_NLP if the query mentions anything NLP course-related.

        ======================================================================
        CRITICAL ROUTING RULE: BASELINE OVER VIDEO
        ======================================================================
        When a user asks for a definition, a conceptual explanation (e.g., "How does X work?"), or a static diagram/visualization, you MUST categorize it into the relevant text domain ([COURSE_NLP], [COURSE_ML], or [GENERAL_ASSISTANCE]). 
        You are PROHIBITED from using [YOUTUBE_SEARCH] for conceptual or diagram requests unless the user explicitly uses video-specific keywords like "video", "watch", "YouTube", or "channel". Never assume a conceptual query requires a video.

        [YOUTUBE_SEARCH] -
        Primary Description:
        Triggered when the user requires visual, auditory, or step-by-step instructional media. This is the primary route for video-based learning, transcript-based summarization, and visual demonstrations.

        Classification Patterns:
        1.Direct Processing: Any message containing a youtube.com or youtu.be link where the user wants a summary, key takeaways, or specific questions answered about that video.
        2.Explicit Discovery: Queries containing action verbs like "find," "show," "search," "watch," or "tutorial" paired with a technical topic.
        3.Visual Learner Preference: When a user explicitly states they are a visual learner or find text-based explanations (RAG) difficult to follow.
        4.Demonstration Requests: "How-to" queries involving physical setups, software UI navigation, or complex mathematical visualizations that are better explained through motion.

        Edge Cases & Handling Instructions:
        1.The "Broken Link" Case: If the user provides a partial or malformed YouTube link, still route here. The pipeline will attempt to repair the link or extract the video ID.
        2.The "Vague Request" Case: If the user says "show me a video" without a topic, route here. The system will prompt the user for the subject.
        3.The "Text-Failure" Fallback: If a previous turn in the conversation shows the user is still confused after a text-based RAG answer, the model should proactively suggest this route.
        4.Short vs. Long: Distinguish between a "quick overview" (Search for < 5 mins) and a "deep dive" (Search for lectures/webinars).

        Analyze the underlying concept of the query, not just the exact words.
        You must respond ONLY with a valid JSON object containing the exact intent string. Do not include markdown formatting, code blocks, or conversational text.

        User Query: "{user_query}"

        Expected Output Format:
        {{"intent": "INTENT_NAME_HERE"}}
        """

        try:
            # Call Gemini Flash. 
            # Note: We enforce JSON output in the generation config.
            response = self.llm.generate_content(
                prompt, 
                generation_config={"response_mime_type": "application/json",
                                   "temperature": 0.0,       # deterministic classification — same input = same route every time
                                #    "max_output_tokens": 50,  # routing decision is tiny — cap tokens to reduce latency
                                    }
            )
            
            # Parse the JSON
            routing_data = json.loads(response.text)
            intent = routing_data.get("intent", "GENERAL_ASSISTANCE")
            
            # Failsafe: Ensure it only returns one of our 4 expected strings
            valid_intents = ["COURSE_NLP", "COURSE_ML", "YOUTUBE_SEARCH", "GENERAL_ASSISTANCE"]
            if intent not in valid_intents:
                return "GENERAL_ASSISTANCE"
                
            return intent
            
        # except Exception as e:
        #     print(f"⚠️ Router Error ({e}). Defaulting to GENERAL_ASSISTANCE.")
        #     return "GENERAL_ASSISTANCE"
        
        except Exception as e:
            print(f"⚠️ Router Error ({e}). Raw response: '{response.text if 'response' in dir() else 'NO RESPONSE'}'. Defaulting to GENERAL_ASSISTANCE.")
            return "GENERAL_ASSISTANCE"
        




        