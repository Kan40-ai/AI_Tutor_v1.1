import json

class StageZeroRouter:
    def __init__(self, llm_client):
        # Pass your existing Gemini Flash client in here
        self.llm = llm_client 

    def classify_intent(self, user_query: str) -> str:
        prompt = f"""
        You are an intelligent Intent Classification Agent for a University AI Tutor.
        Your job is to analyze the user's query and categorize it into the correct domain.

        [COURSE_NLP] - Queries involving NLP technical concepts (text mining, linguistic models, conversational AI) AND all specific NLP course logistics (e.g., questions about the NLP syllabus, instructor details, grading, emails, or schedule).
        [COURSE_ML] - Queries involving core machine learning concepts, statistical modeling, neural networks, computer vision AND all specific ML course logistics (e.g., questions about the ML syllabus, instructor details, grading, emails, or schedule).
        [YOUTUBE_SEARCH] - HIGHEST PRIORITY: ANY explicit command to search for a "video", "YouTube", "watch", or visual media. You MUST choose this route if the user asks for a video, EVEN IF the query mentions NLP or Machine Learning topics.
        [GENERAL_ASSISTANCE] - System troubleshooting, coding debugging (like Python/Flask errors), greetings, well-being, or off-topic queries. Do NOT use this for questions about course instructors, syllabus, or class schedules.

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
        {{
            "intent": "INTENT_NAME_HERE"
        }}
        """

        try:
            # Call Gemini Flash. 
            # Note: We enforce JSON output in the generation config.
            response = self.llm.generate_content(
                prompt, 
                generation_config={"response_mime_type": "application/json"}
            )
            
            # Parse the JSON
            routing_data = json.loads(response.text)
            intent = routing_data.get("intent", "GENERAL_ASSISTANCE")
            
            # Failsafe: Ensure it only returns one of our 4 expected strings
            valid_intents = ["COURSE_NLP", "COURSE_ML", "YOUTUBE_SEARCH", "GENERAL_ASSISTANCE"]
            if intent not in valid_intents:
                return "GENERAL_ASSISTANCE"
                
            return intent
            
        except Exception as e:
            print(f"⚠️ Router Error ({e}). Defaulting to GENERAL_ASSISTANCE.")
            return "GENERAL_ASSISTANCE"