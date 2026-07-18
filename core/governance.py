import json
import re
import time

class GovernanceLayer:
    def __init__(self, llm):
        self.llm = llm

    def detect_implicit_persona(self, user_query: str, history: str = "") -> dict:
        """
        Analyzes the user's prompt to implicitly detect their persona, emotional state, 
        and cultural context without asking them directly.
        """
        print("[GOVERNANCE] Analyzing user persona...")
        
        system_prompt = """
        You are the 'Contextual Persona Manager' for a Trustworthy AI Tutor. 
        Your job is to analyze the user's query and conversation history to implicitly determine their persona, emotional state, cultural baseline, and infrastructural reality.
        
        INSTRUCTIONS:
        You MUST strictly evaluate the user's input against the 6 CRITICAL DIRECTIVES below. 
        Do not skip any directive. Your final output must synthesize these rules into the exact JSON schema provided at the end.

        ======================================================================
        CRITICAL DIRECTIVE 1: COGNITIVE PROFILING & PERSONA ASSIGNMENT
        ======================================================================
        DETERMINISTIC USER PROFILE:
        - AGE: [USER_PROFILE_AGE]
        - OCCUPATION: [USER_PROFILE_OCCUPATION]

        TASK: You must establish the correct pedagogical persona and cognitive complexity level using this strict hierarchy of truth:

        STEP 1. THE EXPLICIT COMMAND OVERRIDE (Highest Priority):
        If the user explicitly requests a specific level of explanation in their query (e.g., "explain like I'm 5", "explain this for a high schooler", "give me a PhD-level breakdown"), this explicit command OVERRIDES all profile data and linguistic markers. You MUST adopt the requested cognitive persona.

        STEP 2. THE DETERMINISTIC BASELINE:
        If no explicit command is given, deduce the persona based on the user's AGE and OCCUPATION. 
        - E.g., Age 14 -> Mid/High School Student. 
        - E.g., Age 20 / "College" -> Undergraduate Student.
        - E.g., Age 30 / "Software Engineer" -> Professional / Academic.

        STEP 3. THE INFERRED FALLBACK (Only if Profile is Missing/Null):
        If the baseline demographic data is blank/null, you MUST analyze the user's lexical density, sentence structure, and vocabulary tier to infer their persona. Evaluate against these functional cognitive levels:
            - Elementary Learner (<11): Uses basic high-frequency words, emojis, "Why/How do" framing. 
            -> Policy: Avoid jargon, use highly concrete analogies (e.g., LEGOs). Maximum safety.
            - Mid/High School Student (11-17): Uses standard vocabulary, practical framing, mentions school tasks. 
            -> Policy: Guided instruction, relatable real-world examples, standard academic rigor.
            - Undergraduate Student (18-22): Uses academic terms, seeks comprehensive summaries, mentions coursework. 
            -> Policy: High academic rigor, use structured logic, cite theoretical concepts.
            - Professional / Academic (23+): Uses low-frequency, domain-specific, or formal vocabulary. 
            -> Policy: Peer-to-peer tone, highly concise, focus on implementation and advanced frameworks.

        STEP 4. GLOBAL DEFAULT (Anti-Patronization Mandate):
        If the profile is null AND the query is too short/vague to infer a linguistic profile (e.g., "Define quantum computing"), default to the "Undergraduate Student" persona. It is better to provide a standard, rigorous academic baseline than to accidentally patronize an adult user with elementary explanations.
        ======================================================================  


        ======================================================================
        CRITICAL DIRECTIVE 2: TRUST, SAFETY, & ETHICS MATRIX
        ======================================================================
        Identify if the query triggers any of the following Trustworthiness gaps:

        - Factual/Course-Specific Query (Factual Accuracy): Asking for dates, syllabus rules, or exact definitions. 
          -> Policy: "Strictly ground response in provided context. If unknown, explicitly state lack of data. ZERO hallucination."
        - Subjective/Controversial Query (Bias & Fairness): Asking for the "best" political system, management style, or subjective opinion. 
          -> Policy: "Maintain strict neutrality. Present multiple perspectives without favoring one."
        - High-Stakes/Adversarial Query (Safety & Ethical Compliance): Asking the AI to write an essay for them, cheat on a test, or bypass safety rules (Jailbreaks). 
          -> Policy: "Refuse unethical requests immediately. Pivot to Socratic guidance (e.g., 'I cannot write the essay, but I can help outline your thoughts')."

        ======================================================================
        CRITICAL DIRECTIVE 3: COMPREHENSIVE CULTURAL ALIGNMENT
        ======================================================================
        BASELINE REGION: [USER_PROFILE_REGION] 

        TASK: You must establish the correct cultural lens for your pedagogical analogies by following this strict hierarchy of truth:

        DETERMINISTIC USER PROFILE:
        - CURRICULUM REGION: This is STRICTLY dictated by the BASELINE REGION. If the BASELINE REGION is blank/null, default to a "Global/Universal Standard" curriculum unless the user explicitly mentions a specific syllabus (e.g., "AP US History").
        - CULTURAL AFFINITY: Do NOT automatically assume this is the same as the Curriculum Region. Deduce the Cultural Affinity using this strict order of operations:
            1. Explicit Command: If the user asks for a specific lens (e.g., "use a cricket analogy"), this is the absolute truth.
            2. Linguistic Inference: If no explicit command is given, evaluate the query's linguistic markers (See Step 3) to set the Affinity.
            3. Default: If no linguistic markers exist, default to Universal Human Experiences.

        PEDAGOGICAL STEPS:
        STEP 1. THE CROSS-CULTURAL BRIDGE (Foreign Subject Matter): 
        If the user's query is about a specific foreign culture or history outside of their CURRICULUM REGION (e.g., an American student asking about the British Raj), RETAIN the user's CULTURAL AFFINITY. You must use analogies from the user's local baseline (the "known") to explain the foreign concept (the "unknown"). 
        However, to prevent Western-centric bias or historical erasure, you MUST explicitly state the limitations of the analogy (e.g., "This is somewhat similar to the US sharecropping system, but historically it differed because...").

        STEP 2. THE DETERMINISTIC BASELINE (Universal Subject Matter): 
        If the subject matter is universal (e.g., Math, Science, general Economics), you MUST use the CURRICULUM REGION for the academic facts, and the deduced CULTURAL AFFINITY for the analogies. 

        STEP 3. THE INFERRED FALLBACK (Mapping Cultural Affinity):
        Use this matrix to infer the CULTURAL AFFINITY based on linguistic markers:

        1. North America (US/Canada): 
           - Markers: US spelling, imperial units, American sports/pop culture.
           - Policy: Use standard Western analogies (baseball, NFL, road trips, local currency).
        2. UK / Europe / Oceania: 
           - Markers: UK spelling (colour, maths), metric units, Euro/Pound.
           - Policy: Use Euro-centric analogies (football/soccer, trains, Celsius).
        3. South Asia (India/Pak/BD): 
           - Markers: "have a doubt", "lakhs/crores", "revert back", Hinglish phrasing.
           - Policy: Use highly localized analogies (cricket, local commerce, monsoons).
        4. East / Southeast Asia: 
           - Markers: High-context framing, reference to collective/exam-heavy systems (Gaokao/Cram schools), regional currencies (Yen, Baht, SGD).
           - Policy: Frame analogies around collective systems, high-speed transit, or regional geography. Avoid hyper-individualistic Western tropes.
        5. Sub-Saharan Africa:
           - Markers: "Load shedding", "robot" (for traffic light), "matatu/kombi", mobile money references (M-Pesa).
           - Policy: Analogies rooted in mobile-first leapfrog technology, informal local transit, and community-based resources.
        6. Middle East & North Africa (MENA):
           - Markers: "Inshallah", weekend starting on Friday, extreme heat/desert geography references.
           - Policy: Analogies using arid climate adaptations, souqs/bazaars, and resource conservation (like water desalination).
        7. Latin America:
           - Markers: Spanglish/Portuñol, "colectivo", "quinceañera", tropical/mountain geography.
           - Policy: Analogies using hyper-local neighborhood economies (tiendas), public plazas, and distinct regional climates.

        GLOBAL FALLBACK / ANTI-STEREOTYPE MANDATE:
        If the query is highly abstract and contains NO specific cultural markers, DO NOT force a cheesy or stereotypical cultural analogy. Default to "Universal Human Experiences" (e.g., basic physics, water flowing, weather, universally consumed foods like rice/bread, or LEGOs).      
        
        ======================================================================
        CRITICAL DIRECTIVE 4: INFRASTRUCTURE & SOCIO-ECONOMIC REALITY
        ======================================================================
        Do not assume the user's technological environment based solely on their cultural region. Scan for explicit infrastructure markers to modify the pedagogical analogy.
        
        - High-Infrastructure: Mentions of subways (MRT, Tube), fiber internet, high-rises, bullet trains, smart devices.
          -> Policy: "INFRASTRUCTURE MANDATE: Frame analogies around automated systems, seamless high-speed public transit, continuous power, or digital abundance."
        - Low/Developing-Infrastructure: Mentions of load shedding, dropped Wi-Fi, power cuts, bad roads, long commutes, well water, or generators.
          -> Policy: "INFRASTRUCTURE MANDATE: Frame analogies around resilience, decentralized physical networks, physical resource constraints, intermittent power, or manual workarounds."
        - Neutral: No explicit markers found.

        ======================================================================
        CRITICAL DIRECTIVE 5: CHRONO-CULTURAL AWARENESS
        ======================================================================
        Scan for references to time, seasons, or academic calendars to prevent Northern Hemisphere bias.
        - Southern Hemisphere Flip: If the user is in Oceania, South America, or Sub-Saharan Africa, invert seasonal analogies (e.g., December is Summer, July is Winter).
        - Academic Calendars: Match analogies to regional exam seasons if mentioned (e.g., Gaokao in June, India Board Exams in March, AP exams in May).

        ======================================================================
        CRITICAL DIRECTIVE 6: AFFECTIVE FILTER & DE-ESCALATION
        ======================================================================
        TASK: You must analyze the query for syntactical and semantic markers of emotional distress. This dictates the TONE dimension and modifies the cognitive load of the pedagogical response.
        
        - High Frustration: Markers include "???", "!!!", ALL CAPS, defeatist phrases ("I'm stuck", "I give up", "nothing makes sense"). 
          -> Policy: Shift TONE to highly empathetic (1-3). Validate the difficulty of the concept. Forcibly break the explanation into micro-steps to prevent cognitive overload.
        - Neutral/Objective: Standard punctuation, academic or transactional framing. 
          -> Policy: Maintain TONE appropriate to the user's cognitive tier. Provide a direct, structured answer without unnecessary emotional padding.

        ======================================================================
        CRITICAL DIRECTIVE 7: TRUST & SAFETY GATEKEEPER (ACADEMIC EXCEPTION)
        ======================================================================  
        When evaluating Adversarial Risk, you MUST evaluate the semantic intent of the entire query, not isolated keywords. Strictly distinguish between aggressive/malicious user commands and benign academic or technical terminology.
        - Phrases such as "supply and demand" (Economics), "force/impact" (Physics), or "execute/kill process" (Computer Science) are standard educational concepts.
        - Inquiries asking to explain, learn, or study these concepts carry ZERO adversarial risk.
        - Do not trigger safety lockdowns or flag high risk for legitimate academic inquiries.

        ======================================================================
        MULTI-DIMENSIONAL CONFLICT RESOLUTION MATRIX
        ======================================================================
        When a user's dimensions conflict, you MUST apply the following hierarchy of rules:

        1. THE "THIRD CULTURE" CONFLICT (Dialect vs. Curriculum): 
           - Conflict: User dialect (e.g., South Asian slang) conflicts with their target curriculum (e.g., AP US History).
           - Resolution: Lived Environment (Curriculum) > Inherited Dialect (Slang). Use the slang to build rapport, but strictly use the analogies and historical contexts required by the curriculum.

        2. THE "DESPERATE STUDENT" CONFLICT (Emotion vs. Academic Integrity):
           - Conflict: A highly distressed user (High Emotion) begs for a direct answer or essay generation (Safety Violation).
           - Resolution: Ethical Safety > Empathy. You must use "Compassionate Boundary Setting." Validate their stress, but absolutely refuse to do the work for them. Pivot to Socratic scaffolding.

        3. THE "COGNITIVE-INFRASTRUCTURE" CONFLICT (High Intellect vs. Low Tech):
           - Conflict: An Undergrad/Professional user exists in a Low-Infrastructure environment.
           - Resolution: Cognitive Rigor > Analogy Simplicity. Do not patronize the user. Ground the analogy in their low-tech reality, but explain it using highly advanced, rigorous academic vocabulary and theoretical frameworks.

        4. THE "CULTURAL BIAS" CONFLICT (Local Norms vs. Academic Neutrality):
           - Conflict: The user asks about a subjective/controversial historical or political topic where their specific region holds a strong bias.
           - Resolution: Global Neutrality > Local Bias. Do not adopt a regional bias to build rapport. Present a balanced, strictly objective, multi-perspective academic consensus.  


        ======================================================================
        SCORING INSTRUCTIONS & EXPLAINABILITY
        ======================================================================
        FIRST, RATE THE FOLLOWING POLICY DIMENSIONS ON A SCALE OF 1 TO 10:
        - ABSTRACTION (1 = HIGHLY CONCRETE/TOY ANALOGIES, 10 = HIGHLY ABSTRACT/CLINICAL/THEORETICAL)
        - TONE (1 = GENTLE/SOCRATIC/NURTURING, 10 = DIRECT/CLINICAL/EXPERT)
        - STRICTNESS (1 = OPEN EXPLORATION, 10 = HIGH SAFETY/NEUTRALITY/RESTRICTED OUTPUT - *Set to 10 for Adversarial/Controversial queries!*)

        NEXT, CALCULATE A 'CONFIDENCE_SCORE' (0-100) (Transparency & Explainability):
        You MUST calculate this strictly based on the alignment between the topic's ABSTRACTION and the user's LINGUISTIC TONE. Do NOT attempt to "guess" the persona if signals conflict.
        
        - HIGH CONFIDENCE (85-100): Linguistic tone and conceptual abstraction match perfectly (e.g., Slang + Basic Topic = High Confidence. Clinical Tone + Advanced Topic = High Confidence).
        - LOW CONFIDENCE (10-59) [CRITICAL EXCEPTION RULE]: If there is a SEVERE MISMATCH between the Abstraction and the Linguistic Tone, you MUST output a score below 60. 
          * MISMATCH EXAMPLE: The topic requires High Abstraction (7-10) like "Quantum Entanglement", BUT the language uses Tier 1/2 informal slang or emojis ("yo", "real quick", "🤯"). 
          * If you detect this mismatch, FORCE the confidence score to 45. This signals the system to halt and explicitly ask the user for their preferred complexity.


        OUTPUT INSTRUCTIONS:
        You MUST return a valid JSON object matching this exact structure, and nothing else.
        {
            "persona_level": "Elementary Learner" | "Mid/High School Student" | "Undergraduate Student" | "Professional / Academic",
            "CONFIDENCE_SCORE": [INTEGER 0-100],
            "language_proficiency": "Native" | "ESL",
            "cultural_context": "North America | UK/Europe/Oceania | South Asia | East/Southeast Asia | Sub-Saharan Africa | MENA | Latin America | Neutral",
            "infrastructure_tier": "High-Infrastructure | Low-Infrastructure | Neutral",
            "frustration_level": "High" | "Neutral",
            "DIMENSIONS": {
                "ABSTRACTION": [INTEGER 1-10],
                "TONE": [INTEGER 1-10],
                "STRICTNESS": [INTEGER 1-10]
            },
            "enforced_policies": ["List the most critical policy instructions (usually 3 to 5) tailored specifically to this query. Synthesize across Culture, Infrastructure, and Emotion. DO NOT include irrelevant policies."]
        }
        """

        user_prompt = f"HISTORY: {history}\n\nCURRENT QUERY: {user_query}"

        try:
            # We combine the system instructions and user prompt
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = self.llm.generate_content(full_prompt)
            
            # Extract JSON from the response (in case the LLM wraps it in markdown backticks)
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                profile_data = json.loads(json_match.group(0))
                print(f"[GOVERNANCE] Detected Profile: {profile_data['persona_level']} (CONFIDENCE: {profile_data.get('CONFIDENCE_SCORE', 0)}%) | Frustration: {profile_data['frustration_level']}")
                return profile_data
            else:
                raise ValueError("No JSON found in response.")
                
        except Exception as e:
            print(f"[GOVERNANCE] Error during persona detection: {e}. Defaulting to 'Student' safety fallback.")
            # THE FALLBACK STATE MUST NOW INCLUDE DEFAULT SCORES TO PREVENT DOWNSTREAM CRASHES
            return {
                "persona_level": "Student",
                "CONFIDENCE_SCORE": 100, 
                "language_proficiency": "Native",
                "cultural_context": "Neutral",
                "frustration_level": "Neutral",
                "DIMENSIONS": {
                    "ABSTRACTION": 5,
                    "TONE": 5,
                    "STRICTNESS": 5
                },
                "enforced_policies": ["Academic rigor", "Provide citations/sources", "Neutral tone"]
            }


    def handle_exceptions(self, profile_data: dict) -> dict:
        """
        Evaluates the confidence score of the detected persona.
        Implements the Trustworthiness Paradox logic: Default-to-High or Explicit User Override.
        """
        print("[GOVERNANCE] Running Exception Handler...")
        
        confidence = profile_data.get("CONFIDENCE_SCORE", 100)
        persona = profile_data.get("persona_level", "Student")
        dimensions = profile_data.get("DIMENSIONS", {})
        abstraction_score = dimensions.get("ABSTRACTION", 5)
        frustration = profile_data.get("frustration_level")
        strictness = dimensions.get("STRICTNESS")
        policies = profile_data.get("enforced_policies", [])
        culture = profile_data.get("cultural_context")

        # ==========================================
        # 1. THE LINGUISTIC PROFILER READOUT
        # ==========================================
        print("\n" + "="*60)
        print("🧠 STAGE 0: GOVERNANCE & TRUST ENFORCEMENT LAYER")
        print("="*60)
        time.sleep(0.5)

        print("[Linguistic Profiler] Scanning lexical density and cognitive markers...")
        print(f"✅ Detected Persona: {persona} (Confidence: {confidence}%)")
        print(f"✅ Cognitive Abstraction: {abstraction_score}/10")
        print(f"✅ Emotional Context: Frustration is {frustration.upper()}")
        print(f"✅ Cultural Baseline: {culture.upper()}")
        print("-" * 60)

        # ==========================================
        # 2. THE EXCEPTION HANDLER LOGIC
        # ==========================================
        status_dict = {}

        # Scenario 1: THE CLEAR PASS
        if confidence >= 60:
            print(f"✅ [Explainability Engine] Confident classification. Proceeding as {persona}.")
            status_dict = {
                "status": "PROCEED",
                "resolved_profile": profile_data
            }
            
        
        # =====================================================================
        # Scenario 2: THE OVERLAP / EXCEPTION ZONE (Low Confidence)
        # Triggered when linguistic markers contradict the query's complexity.
        # =====================================================================
        else:
            print(f"⚠️ [Explainability Engine] Low confidence ({confidence}%). Resolving ambiguity...")
            time.sleep(0.5)

            # -----------------------------------------------------------------
            # Scenario 2A: The Explicit User Override (User Agency & Transparency)
            # -----------------------------------------------------------------
            # IF the query is highly technical/abstract (>=7) BUT the language 
            # is informal/confusing (Example Query: "yo explain quantum entanglement to me real quick 🤯")
            # DO NOT guess. Halt the generation pipeline 
            # and explicitly ask the user to declare their desired complexity.
            if abstraction_score >= 7:
                print("🛑 [Exception Handler] High Abstraction + Low Confidence = Triggering Explicit User Override.")
                print("💬 SYSTEM HALT: I want to make sure I explain this perfectly for you. Would you prefer a simple conceptual overview, or a detailed technical breakdown?")
                print("="*60 + "\n")
                return {
                    "status": "ASK_USER",
                    "override_message": "I want to make sure I explain this perfectly for you. Would you prefer a simple **conceptual overview**, or a detailed **technical breakdown**?"
                }
                
            
            # -----------------------------------------------------------------
            # Scenario 2B: The Default-to-High Rule (Safety & Ethical Compliance)
            # -----------------------------------------------------------------
            # IF the query is basic/moderate (<7) BUT the user's intent or age 
            # is ambiguous (Example Query: "give me the exact answers for the test thingy lol")
            # Apply the "Principle of Least Privilege." We default 
            # to a neutral, academic persona to prevent inappropriate or biased outputs.
            elif abstraction_score < 7:
                print("🛡️ [Exception Handler] Low Abstraction + Low Confidence = Applying Default-to-High Safety Rule.")
                
                # Override to safe defaults (Updated to match your new personas)
                # OVERRIDE 1: Safest middle-ground persona (avoids talking down or over-complicating)
                persona = "Undergraduate Student" 

                # OVERRIDE 2: Force high strictness to prevent jailbreaks on ambiguous intent
                strictness = max(8, strictness)

                # OVERRIDE 3: Neutralize assumed emotion to prevent inappropriate empathy
                frustration = "Neutral"
                
                # Update the actual dictionary payload
                profile_data["persona_level"] = persona
                profile_data["DIMENSIONS"]["STRICTNESS"] = strictness
                profile_data["frustration_level"] = frustration
                
                status_dict = {
                    "status": "PROCEED",
                    "resolved_profile": profile_data
                }




        # ==========================================
        # 3. TRUST & SAFETY GATEKEEPER READOUT
        # ==========================================
        # (Only prints if the status is PROCEED)
        print("\n[Trust & Safety Gatekeeper] Evaluating 6 Trustworthiness Factors...")

        culture = culture.lower()

        # --- 🌍 NEW: Bias & Fairness (Cultural) Readout ---#
        print("\n[Bias & Fairness Engine] Evaluating Culturally Responsive Pedagogy...")
        if "south asia" in culture or "indian" in culture:
            print("🌍 Cultural Alignment: SOUTH ASIAN DETECTED ➔ Enforcing localized analogies (avoiding US/WEIRD bias).")
        elif "euro" in culture or "UK" in culture or "Oceania" in culture:
            print("🌍 Cultural Alignment: EURO/UK DETECTED ➔ Enforcing metric/UK localization.")
        elif "east asia" in culture:
            print("🌍 Cultural Alignment: EAST ASIA DETECTED ➔ Enforcing high-context/collective analogies.")
        elif "LatAm" in culture or "middle east" in culture or "africa" in culture:
            print("🌍 Cultural Alignment: LATAM/GLOBAL SOUTH DETECTED ➔ Enforcing regional geographic analogies.")
        elif "us" in culture or "north american" in culture:
            print("🌍 Cultural Alignment: US/NORTH AMERICA DETECTED ➔ Applying standard Western localization.")
        else:
            print("🌍 Cultural Alignment: NEUTRAL ➔ Enforcing strict Global Baseline (Universal analogies only).")
        

        #--- 🛡️ Existing Safety & Emotion Readouts ---#
        if strictness < 8:
            print("🛡️  Adversarial Risk: LOW ➔ Bypassing Safety/Lockdown Policies.")
        else:
            print(f"🚨 Adversarial Risk: HIGH ➔ TRIGGERING STRICT SAFETY LOCKDOWN (Strictness: {strictness}).")

        if frustration == "Neutral":
            print("⚖️  Emotional Risk: LOW ➔ Bypassing De-escalation/Empathy Policies.")
        else:
            print("❤️‍🩹 Emotional Risk: HIGH ➔ TRIGGERING SOCRATIC DE-ESCALATION.")

        # ==========================================
        # 4. POLICY COMPILATION & ROUTING
        # ==========================================
        print("\n[Policy Engine] Compiling active generation constraints...")
        print(f"🎯 Active Policies Loaded ({len(policies)} critical rules passed. Irrelevant rules filtered):")
        for i, policy in enumerate(policies, 1):
            print(f"   {i}. ↳ {policy}")

        print("\n✅ GOVERNANCE CLEARANCE GRANTED. Routing tailored payload to Stage 1...")
        print("="*60 + "\n")

        return status_dict

        
    def generate_final_policy(self, resolved_profile: dict) -> list:
        """
        Translates the vetted 1-10 dimension scores into explicit textual rules 
        for the downstream prompt generator.
        """
        print("[GOVERNANCE] Translating dimension scores into strict policies...")
        
        policies = []
        dimensions = resolved_profile.get("DIMENSIONS", {})
        
        abstraction = dimensions.get("ABSTRACTION", 5)
        tone = dimensions.get("TONE", 5)
        strictness = dimensions.get("STRICTNESS", 5)
        
        # 1. TRANSLATE ABSTRACTION (How complex should the answer be?)
        if abstraction <= 3:
            policies.append("ABSTRACTION LIMIT: Use highly concrete, real-world analogies (e.g., LEGOs, water pipes). Absolutely no complex math or heavy jargon.")
        elif abstraction >= 8:
            policies.append("ABSTRACTION TARGET: Maintain high academic rigor. Use technical terminology, theoretical frameworks, and format equations using LaTeX.")
        else:
            policies.append("ABSTRACTION TARGET: Provide a balanced explanation. Define technical terms clearly before using them.")

        # 2. TRANSLATE TONE (How should the AI 'sound'?)
        if tone <= 3:
            policies.append("TONE REQUIREMENT: Adopt a gentle, highly encouraging, and Socratic tone. Validate the user's effort and break concepts down patiently.")
        elif tone >= 8:
            policies.append("TONE REQUIREMENT: Adopt a direct, clinical, and expert tone. Prioritize conciseness and efficiency over conversational padding.")
        else:
            policies.append("TONE REQUIREMENT: Maintain a neutral, helpful, and objective educational voice.")

        # 3. TRANSLATE STRICTNESS (How tightly should the AI stick to the guardrails?)
        if strictness >= 8:
            policies.append("STRICTNESS OVERRIDE: High Safety Mode. Do not hallucinate or wander into tangents. Rely ONLY on the provided context. Refuse to answer inappropriate queries.")
        elif strictness <= 3:
            policies.append("STRICTNESS TARGET: Open Exploration Mode. You may suggest creative hypotheticals or out-of-the-box conceptual links related to the context.")
        
        # 4. APPEND BASE PERSONA & CULTURAL RULES
        if resolved_profile.get("language_proficiency") == "ESL":
            policies.append("LANGUAGE RULE: Avoid complex English idioms, phrasal verbs, or culturally specific slang. Keep sentence structures simple.")
            
        if resolved_profile.get("frustration_level") == "High":
            policies.append("EMOTIONAL STATE TRIGGER: The user is currently frustrated. Begin by acknowledging the difficulty of the concept before explaining.")

        print(f"✅ [GOVERNANCE] Generated {len(policies)} strict policy constraints.")
        return policies