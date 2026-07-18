# import ssl
# import nltk
# ssl._create_default_https_context = ssl._create_unverified_context
# nltk.download('stopwords', quiet=True)
# nltk.download('punkt_tab', quiet=True)
# nltk.download('punkt', quiet=True)

# import os
# from dotenv import load_dotenv
# load_dotenv()

# from flask import Flask, render_template, jsonify, request
# import json
# from services.tutor_service import TutorService
# from config import config as app_config
# from core.rag import EduRAGConfig

# # 🟣 LAYER III — Trust Enforcement imports
# from core.trust_agents.agent1_factual_accuracy import FactualAccuracyAgent
# from core.trust_agents.agent2_transparency     import TransparencyAgent
# from core.trust_agents.agent3_pedagogical_alignment import PedagogicalAlignmentAgent
# from core.trust_agents.agent4_bias_fairness    import BiasFairnessAgent
# from core.trust_agents.agent5_safety_ethics    import SafetyEthicsAgent
# from core.trust_agents.agent6_age_appropriateness   import AgeAppropriatenessAgent

# app = Flask(__name__)

# rag_config = EduRAGConfig()

# tutor_service = TutorService(
#     config=rag_config,
#     pinecone_api_key=os.environ.get("PINECONE_API_KEY"),
#     google_creds_path=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "google_credentials.json")
# )

# # 🟣 LAYER III — Agent initialisations
# agent1 = FactualAccuracyAgent(llm_client=tutor_service.tutor_engine.llm)
# agent2 = TransparencyAgent(llm_client=tutor_service.tutor_engine.llm)
# agent3 = PedagogicalAlignmentAgent(llm_client=tutor_service.tutor_engine.llm)
# agent4 = BiasFairnessAgent(llm_client=tutor_service.tutor_engine.llm)
# agent5 = SafetyEthicsAgent(llm_client=tutor_service.tutor_engine.llm)
# agent6 = AgeAppropriatenessAgent(llm_client=tutor_service.tutor_engine.llm)
 


# @app.route("/")
# def index():
#     return render_template("chat.html")


# @app.route("/api/chat", methods=["POST"])
# async def chat():
#     try:
#         data    = request.get_json() or {}
#         message = data.get("message", "")

#         if not message:
#             return jsonify({"error": "Message is required"}), 400

#         # ══════════════════════════════════════════════════════════════════
#         # LAYER III — AGENT 5: Safety & Ethics (PRE-GENERATION FIREWALL)
#         # Runs BEFORE tutor_service — intercepts unsafe queries before any
#         # LLM inference is invoked.
#         # Hard FAIL → return immediately, Layers I + II never called.
#         # ══════════════════════════════════════════════════════════════════
#         trust_verdicts = {}

#         safety_verdict = agent5.verify(
#             question      = message,
#             draft_answer  = "",
#             persona_level = "Undergraduate Student",
#         )
#         trust_verdicts["agent5_safety"] = safety_verdict.to_dict()

#         if safety_verdict.verdict == "FAIL":
#             app.logger.warning(
#                 f"[AGENT 5 FAIL — PRE-GEN] score={safety_verdict.score:.2f} "
#                 f"| jailbreak={safety_verdict.jailbreak_detected} "
#                 f"| crisis={safety_verdict.crisis_detected} "
#                 f"| flags={safety_verdict.flags} "
#                 f"| query='{message[:80]}'"
#             )
#             if safety_verdict.crisis_detected and not safety_verdict.crisis_escalated:
#                 final_answer = (
#                     "I'm concerned about what you've shared. Please reach out to "
#                     "a mental health professional or contact the 988 Suicide & "
#                     "Crisis Lifeline (call or text 988) — available 24/7. "
#                     "You don't have to face this alone."
#                 )
#             else:
#                 final_answer = (
#                     "I'm not able to help with that request. "
#                     "If you have a question about your course material, "
#                     "I'd be happy to help — try asking about a concept, "
#                     "assignment guidance, or anything from your NLP or ML syllabus. "
#                     "For academic integrity concerns, please contact your course "
#                     "instructor (Sagnik.Raychoudhury@unt.edu) or the university's "
#                     "Academic Integrity Office."
#                 )
#             return jsonify({
#                 "answer":         final_answer,
#                 "sources":        [],
#                 "status":         "safety_block",
#                 "trust_verdicts": trust_verdicts,
#             })

#         elif safety_verdict.verdict == "WARN":
#             app.logger.info(
#                 f"[AGENT 5 WARN] flags={safety_verdict.flags} "
#                 f"| query='{message[:80]}'"
#             )

#         # ── LAYER I + II: Governance + Capability ─────────────────────────
#         # Only reached if Agent 5 cleared the query as safe.
#         # ───────────────────────────────────────────────────────────────────
#         raw = await tutor_service.generate_answer(message)

#         if isinstance(raw, str):
#             return jsonify({"answer": raw, "sources": [], "status": "ask_user"})

#         refined_chunks     = raw.get("refined_chunks", [])
#         governance_profile = raw.get("resolved_profile", {})
#         app.logger.info(f"[DEBUG] governance_profile keys: {list(governance_profile.keys())}")

#         intent_route       = raw.get("intent_route", "GENERAL_ASSISTANCE")
#         final_answer       = raw["answer"]

#         # ══════════════════════════════════════════════════════════════════
#         # LAYER III — POST-GENERATION AGENTS
#         # Each agent receives raw["answer"] — original unmodified draft.
#         # ══════════════════════════════════════════════════════════════════


#         # # ── AGENT 6 — Age-Appropriateness (ALL routes, Hard BLOCK) ────────
#         # # Runs on ALL routes. Hard BLOCK on FAIL — same tier as Agent 5.
#         # # Distinct from Agent 5: asks "safe for THIS age?" not "safe for anyone?"
#         # # ──────────────────────────────────────────────────────────────────
#         # if governance_profile:
#         #     age_verdict = agent6.verify(
#         #         question           = message,
#         #         draft_answer       = raw["answer"],
#         #         governance_profile = governance_profile,
#         #     )
#         #     trust_verdicts["agent6_age"] = age_verdict.to_dict()
 
#         #     if age_verdict.verdict == "FAIL":
#         #         app.logger.warning(
#         #             f"[AGENT 6 FAIL] score={age_verdict.score:.2f} "
#         #             f"| flags={age_verdict.flags} | query='{message[:80]}'"
#         #         )
#         #         # Hard BLOCK — content not age-appropriate
#         #         final_answer = (
#         #             "I'm not able to deliver this response as it may not be "
#         #             "appropriate for your learning level. Please rephrase your "
#         #             "question or ask your instructor for guidance."
#         #         )
 
#         #     elif age_verdict.verdict == "WARN":
#         #         app.logger.info(
#         #             f"[AGENT 6 WARN] flags={age_verdict.flags} "
#         #             f"| query='{message[:80]}'"
#         #         )
#         #         # Soft warn — annotate for younger learners only
#         #         persona = governance_profile.get("persona_level", "")
#         #         if persona in ("Elementary Learner", "Mid/High School Student"):
#         #             final_answer += (
#         #                 f"\n\n---\n⚠️ *Note: Some parts of this response may be "
#         #                 f"challenging for your current level. Ask your teacher "
#         #                 f"if you need help understanding any concepts.*"
#         #             )
#         # else:
#         #     trust_verdicts["agent6_age"] = "skipped — no governance profile"


#         # ── AGENT 6 — Age-Appropriateness (ALL routes, Hard BLOCK) ────────
#         # Runs FIRST post-generation — hard block protects younger learners
#         # before Agents 1-4 run. Mirrors Agent 5 pre-generation firewall.
#         # Distinct from Agent 5: asks "safe for THIS age?" not "safe for anyone?"
#         # ──────────────────────────────────────────────────────────────────
#         if governance_profile is not None:
#             age_verdict = agent6.verify(
#                 question           = message,
#                 draft_answer       = raw["answer"],
#                 governance_profile = governance_profile,
#             )
#             trust_verdicts["agent6_age"] = age_verdict.to_dict()

#             if age_verdict.verdict == "FAIL":
#                 app.logger.warning(
#                     f"[AGENT 6 FAIL] score={age_verdict.score:.2f} "
#                     f"| flags={age_verdict.flags} | query='{message[:80]}'"
#                 )
#                 final_answer = (
#                     "I'm not able to deliver this response as it may not be "
#                     "appropriate for your learning level. Please rephrase your "
#                     "question or ask your instructor for guidance."
#                 )
#                 # Return immediately — Agents 1-4 never called
#                 return jsonify({
#                     "answer":         final_answer,
#                     "sources":        [],
#                     "status":         "age_block",
#                     "trust_verdicts": trust_verdicts,
#                 })

#             elif age_verdict.verdict == "WARN":
#                 app.logger.info(
#                     f"[AGENT 6 WARN] flags={age_verdict.flags} "
#                     f"| query='{message[:80]}'"
#                 )
#                 # Soft warn — annotate for younger learners only
#                 persona = governance_profile.get("persona_level", "")
#                 if persona in ("Elementary Learner", "Mid/High School Student"):
#                     final_answer += (
#                         f"\n\n---\n⚠️ *Note: Some parts of this response may be "
#                         f"challenging for your current level. Ask your teacher "
#                         f"if you need help understanding any concepts.*"
#                     )
#         else:
#             trust_verdicts["agent6_age"] = "skipped — no governance profile"
 

#         # ── AGENT 1 — Factual Accuracy (RAG route only) ───────────────────
#         # Severity: SOFT WARN
#         # ──────────────────────────────────────────────────────────────────
#         factual_verdict = None  # initialise so Agent 2 can safely reference it

#         if refined_chunks:
#             factual_verdict = agent1.verify(
#                 question       = message,
#                 draft_answer   = raw["answer"],
#                 context_chunks = refined_chunks,
#             )
#             trust_verdicts["agent1_factual"] = factual_verdict.to_dict()

#             if factual_verdict.verdict == "FAIL":
#                 app.logger.warning(
#                     f"[AGENT 1 FAIL] rate={factual_verdict.hallucination_rate:.2f} "
#                     f"| flags={factual_verdict.flags} | query='{message[:80]}'"
#                 )
#                 final_answer = (
#                     "I was unable to verify this answer against your course materials. "
#                     "Please consult your textbook or ask your instructor."
#                 )

#             elif factual_verdict.verdict == "WARN":
#                 app.logger.info(
#                     f"[AGENT 1 WARN] flags={factual_verdict.flags} "
#                     f"| query='{message[:80]}'"
#                 )
#                 warn_flags = (
#                     ", ".join(factual_verdict.flags)
#                     if factual_verdict.flags else "low citation coverage"
#                 )
#                 final_answer += (
#                     f"\n\n---\n⚠️ *Transparency note: Minor grounding gaps detected "
#                     f"({warn_flags}). Please verify against your course materials.*"
#                 )
#         else:
#             trust_verdicts["agent1_factual"] = "skipped — non-RAG route"

#         # ── AGENT 2 — Transparency & Explainability (ALL routes) ──────────
#         # RAG mode:     checks [File: X, Page: Y] course citations.
#         # General mode: checks web URLs as transparency signal.
#         # Severity: SOFT WARN — FAIL annotates response, does not block.
#         # ──────────────────────────────────────────────────────────────────
#         transparency_verdict = agent2.verify(
#             question       = message,
#             draft_answer   = raw["answer"],
#             context_chunks = refined_chunks,  # empty list for non-RAG
#         )
#         trust_verdicts["agent2_transparency"] = transparency_verdict.to_dict()

#         if transparency_verdict.verdict == "FAIL":
#             app.logger.warning(
#                 f"[AGENT 2 FAIL] score={transparency_verdict.score:.2f} "
#                 f"| flags={transparency_verdict.flags} | query='{message[:80]}'"
#             )
#             # Only annotate if Agent 1 hasn't already annotated
#             # Safe check — factual_verdict is None for non-RAG routes
#             agent1_already_annotated = (
#                 factual_verdict is not None and
#                 factual_verdict.verdict in ("FAIL", "WARN")
#             )
#             if not agent1_already_annotated:
#                 trans_flags = (
#                     ", ".join(transparency_verdict.flags)
#                     if transparency_verdict.flags else "low traceability"
#                 )
#                 final_answer += (
#                     f"\n\n---\n⚠️ *Transparency note: This response has "
#                     f"traceability gaps ({trans_flags}). Consider verifying "
#                     f"claims against authoritative sources.*"
#                 )

#         elif transparency_verdict.verdict == "WARN":
#             app.logger.info(
#                 f"[AGENT 2 WARN] flags={transparency_verdict.flags} "
#                 f"| query='{message[:80]}'"
#             )
#             # Audit log only — WARN does not annotate student-facing answer
        


#         # ── AGENT 3 — Pedagogical Alignment (ALL routes) ──────────────────
#         # Severity: ADVISORY LOG only.
#         # Response always delivered untouched regardless of verdict.
#         # FAIL/WARN logged as pedagogical drift events for EduTrust-Eval.
#         # ──────────────────────────────────────────────────────────────────
#         if governance_profile:
#             pedagogical_verdict = agent3.verify(
#                 question           = message,
#                 draft_answer       = raw["answer"],
#                 governance_profile = governance_profile,
#                 intent_route       = intent_route,
#             )
#             trust_verdicts["agent3_pedagogical"] = pedagogical_verdict.to_dict()
 
#             if pedagogical_verdict.verdict == "FAIL":
#                 app.logger.warning(
#                     f"[AGENT 3 FAIL — ADVISORY] score={pedagogical_verdict.score:.2f} "
#                     f"| flags={pedagogical_verdict.flags} | query='{message[:80]}'"
#                 )
#                 # Advisory only — response NOT modified, NOT blocked
 
#             elif pedagogical_verdict.verdict == "WARN":
#                 app.logger.info(
#                     f"[AGENT 3 WARN — ADVISORY] flags={pedagogical_verdict.flags} "
#                     f"| query='{message[:80]}'"
#                 )
#                 # Advisory only — logged for longitudinal drift analysis
#         else:
#             trust_verdicts["agent3_pedagogical"] = "skipped — no governance profile"
 



#         # ── AGENT 4 — Bias & Fairness (ALL routes) ────────────────────────
#         # Only agent with cross-layer dependency: reads governance_profile.
#         # Severity: SOFT WARN — logged for EduTrust-Eval, does not block.
#         # ──────────────────────────────────────────────────────────────────
#         if governance_profile:
#             bias_verdict = agent4.verify(
#                 question           = message,
#                 draft_answer       = raw["answer"],
#                 governance_profile = governance_profile,
#             )
#             trust_verdicts["agent4_bias"] = bias_verdict.to_dict()

#             if bias_verdict.verdict == "FAIL":
#                 app.logger.warning(
#                     f"[AGENT 4 FAIL] score={bias_verdict.score:.2f} "
#                     f"| pvr={bias_verdict.policy_violation_rate:.2f} "
#                     f"| flags={bias_verdict.flags} | query='{message[:80]}'"
#                 )

#             elif bias_verdict.verdict == "WARN":
#                 app.logger.info(
#                     f"[AGENT 4 WARN] flags={bias_verdict.flags} "
#                     f"| query='{message[:80]}'"
#                 )
#         else:
#             trust_verdicts["agent4_bias"] = "skipped — no governance profile"
        

#         # ════════════════════════════════════════════════════════════════
#         # 🔬 TRUST AGGREGATOR — EduTrust-Eval Overall Score
#         # Severity-weighted: Hard Block > Soft WARN > Advisory LOG
#         # ════════════════════════════════════════════════════════════════
#         def compute_trust_aggregate(trust_verdicts: dict) -> dict:
#             """
#             Computes a final cumulative trust score and verdict across all
#             6 agents. Mirrors the severity-weighted architecture from Slide 16.

#             Hard Block agents (5, 6): FAIL = immediate overall FAIL, score=0.
#             Soft WARN agents (1, 2, 4): FAIL/WARN contributes to score, no block.
#             Advisory agent (3): always contributes to score, never blocks.

#             Weights (sum to 1.0 across all 6 agents):
#                 Agent 5 Safety:        0.25  (highest — pre-gen firewall)
#                 Agent 6 Age:           0.20  (hard block post-gen)
#                 Agent 1 Factual:       0.20  (RAG route only, else redistributed)
#                 Agent 2 Transparency:  0.15
#                 Agent 4 Bias:          0.12
#                 Agent 3 Pedagogical:   0.08  (advisory — lowest weight)
#             """

#             WEIGHTS = {
#                 "agent5_safety":      0.25,
#                 "agent6_age":         0.20,
#                 "agent1_factual":     0.20,
#                 "agent2_transparency":0.15,
#                 "agent4_bias":        0.12,
#                 "agent3_pedagogical": 0.08,
#             }

#             # ── Hard Block check first ────────────────────────────────────
#             for hard_block_agent in ["agent5_safety", "agent6_age"]:
#                 verdict = trust_verdicts.get(hard_block_agent, {})
#                 if isinstance(verdict, dict) and verdict.get("verdict") == "FAIL":
#                     return {
#                         "overall_verdict": "BLOCKED",
#                         "overall_score":   0.0,
#                         "breakdown":       {k: _extract_score(v) for k, v in trust_verdicts.items()},
#                         "agents_fired":    [k for k, v in trust_verdicts.items() if isinstance(v, dict)],
#                         "blocked_by":      hard_block_agent,
#                     }

#             # ── Weighted mean for remaining agents ────────────────────────
#             total_weight = 0.0
#             weighted_sum = 0.0
#             agents_fired = []
#             breakdown    = {}

#             for agent_key, weight in WEIGHTS.items():
#                 verdict = trust_verdicts.get(agent_key)

#                 # Skipped agents (non-RAG route for Agent 1, no governance profile)
#                 if isinstance(verdict, str) and "skipped" in verdict:
#                     breakdown[agent_key] = "skipped"
#                     continue

#                 if not isinstance(verdict, dict):
#                     breakdown[agent_key] = "not_run"
#                     continue

#                 score = _extract_score(verdict)
#                 breakdown[agent_key]  = round(score, 3)
#                 weighted_sum          += score * weight
#                 total_weight          += weight
#                 agents_fired.append(agent_key)

#             # Normalise by actual weight fired (handles skipped agents)
#             overall_score = (weighted_sum / total_weight) if total_weight > 0 else 0.0
#             overall_score = round(overall_score, 3)

#             # Verdict thresholds
#             if overall_score >= 0.75:
#                 overall_verdict = "PASS"
#             elif overall_score >= 0.50:
#                 overall_verdict = "WARN"
#             else:
#                 overall_verdict = "FAIL"

#             return {
#                 "overall_verdict": overall_verdict,
#                 "overall_score":   overall_score,
#                 "breakdown":       breakdown,
#                 "agents_fired":    agents_fired,
#                 "blocked_by":      None,
#             }


#         def _extract_score(verdict) -> float:
#             """Safely extract numeric score from agent verdict dict."""
#             if not isinstance(verdict, dict):
#                 return 0.0
#             try:
#                 return float(verdict.get("score", 0.0))
#             except (TypeError, ValueError):
#                 return 0.0


#         # # ── Trust Aggregator ──────────────────────────────────────────────
#         # trust_aggregate = compute_trust_aggregate(trust_verdicts)

#         # # ── Return verified response ───────────────────────────────────────
#         # print(f"\n{'='*60}")
#         # print(f"QUERY: {message[:80]}")
#         # print(f"ROUTE: {intent_route}")
#         # print(f"OVERALL: {trust_aggregate['overall_verdict']} "
#         #       f"| SCORE: {trust_aggregate['overall_score']}")
#         # print(f"BREAKDOWN: {trust_aggregate['breakdown']}")
#         # print(f"FULL VERDICTS:")
#         # print(json.dumps(trust_verdicts, indent=2, default=str))




#         # # ── Only show aggregate score when all applicable agents ran ──
#         # agent5_verdict = trust_verdicts.get("agent5_safety", {})
#         # hard_blocked   = (isinstance(agent5_verdict, dict) and
#         #                 agent5_verdict.get("verdict") == "FAIL" and
#         #                 "agent1_factual" not in trust_verdicts and
#         #                 "agent2_transparency" not in trust_verdicts)

#         # if hard_blocked:
#         #     print(f"OVERALL:  🚫 HARD BLOCKED — Response suppressed before LLM call")
#         #     print(f"AGENT 5:  FAIL | Score: {agent5_verdict.get('score', 0.0)}")
#         #     print(f"          Jailbreak: {agent5_verdict.get('jailbreak_detected')}")
#         #     print(f"          Crisis:    {agent5_verdict.get('crisis_detected')}")
#         #     print(f"          Agents 1,2,3,4,6: NOT INVOKED (latency saved)")
#         # else:
#         #     print(f"OVERALL:  {trust_aggregate['overall_verdict']} | SCORE: {trust_aggregate['overall_score']}")
#         #     print(f"BREAKDOWN:{trust_aggregate['breakdown']}")

#         # print(f"{'='*60}\n")





#         # ── Trust Aggregator ──────────────────────────────────────────────
#         trust_aggregate = compute_trust_aggregate(trust_verdicts)

#         # ── Terminal print ────────────────────────────────────────────────
#         agent5_verdict = trust_verdicts.get("agent5_safety", {})
#         hard_blocked   = (isinstance(agent5_verdict, dict) and
#                         agent5_verdict.get("verdict") == "FAIL" and
#                         "agent1_factual" not in trust_verdicts and
#                         "agent2_transparency" not in trust_verdicts)

#         print(f"\n{'='*60}")
#         print(f"QUERY:    {message[:80]}")
#         print(f"ROUTE:    {intent_route}")

#         if hard_blocked:
#             print(f"OVERALL:  🚫 HARD BLOCKED — Response suppressed before LLM call")
#             print(f"AGENT 5:  FAIL | Score: {agent5_verdict.get('score', 0.0)}")
#             print(f"          Jailbreak: {agent5_verdict.get('jailbreak_detected')}")
#             print(f"          Crisis:    {agent5_verdict.get('crisis_detected')}")
#             print(f"          Agents 1,2,3,4,6: NOT INVOKED (latency saved)")
#         else:
#             print(f"OVERALL:  {trust_aggregate['overall_verdict']} "
#                 f"| SCORE: {trust_aggregate['overall_score']}")
#             print(f"BREAKDOWN:{trust_aggregate['breakdown']}")
#             print(f"FULL VERDICTS:")
#             print(json.dumps(trust_verdicts, indent=2, default=str))

#         print(f"{'='*60}\n")

        
        
#         return jsonify({
#             "answer":         final_answer,
#             "sources":        raw.get("sources", []),
#             "status":         "success",
#             "trust_verdicts": trust_verdicts,
#             "trust_aggregate": trust_aggregate,
#         })

#     except Exception as e:
#         app.logger.error(f"Chat Error: {str(e)}")
#         return jsonify({
#             "error":   "Tutor encountered an issue. Check backend logs.",
#             "details": str(e)
#         }), 500


# if __name__ == "__main__":
#     app.run(debug=True, port=5001, use_reloader=False)







# RAG Baseline Block:

import ssl
import nltk
ssl._create_default_https_context = ssl._create_unverified_context
nltk.download('stopwords', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('punkt', quiet=True)

import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, jsonify, request
import json
from services.tutor_service import TutorService
from config import config as app_config
from core.rag import EduRAGConfig

# 🟣 LAYER III — Trust Enforcement imports
from core.trust_agents.agent1_factual_accuracy import FactualAccuracyAgent
from core.trust_agents.agent2_transparency     import TransparencyAgent
from core.trust_agents.agent3_pedagogical_alignment import PedagogicalAlignmentAgent
from core.trust_agents.agent4_bias_fairness    import BiasFairnessAgent
from core.trust_agents.agent5_safety_ethics    import SafetyEthicsAgent
from core.trust_agents.agent6_age_appropriateness   import AgeAppropriatenessAgent

app = Flask(__name__)

rag_config = EduRAGConfig()

tutor_service = TutorService(
    config=rag_config,
    pinecone_api_key=os.environ.get("PINECONE_API_KEY"),
    google_creds_path=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "google_credentials.json")
)

# 🟣 LAYER III — Agent initialisations
agent1 = FactualAccuracyAgent(llm_client=tutor_service.tutor_engine.llm)
agent2 = TransparencyAgent(llm_client=tutor_service.tutor_engine.llm)
agent3 = PedagogicalAlignmentAgent(llm_client=tutor_service.tutor_engine.llm)
agent4 = BiasFairnessAgent(llm_client=tutor_service.tutor_engine.llm)
agent5 = SafetyEthicsAgent(llm_client=tutor_service.tutor_engine.llm)
agent6 = AgeAppropriatenessAgent(llm_client=tutor_service.tutor_engine.llm)
 


@app.route("/")
def index():
    return render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
async def chat():
    try:
        data        = request.get_json() or {}
        message     = data.get("message", "")
        skip_agents = data.get("skip_agents", False)  # RAG baseline mode

        if not message:
            return jsonify({"error": "Message is required"}), 400

        # ── RAG BASELINE MODE ─────────────────────────────────────────────────────
        # When skip_agents=True: runs RAG pipeline only, bypasses all 6
        # trust agents. Used for EduTrust-Eval RAG baseline evaluation.
        # Triggered by POST {"message": "...", "skip_agents": true}
        # ─────────────────────────────────────────────────────
        if skip_agents:
            raw = await tutor_service.generate_answer(message)
            if isinstance(raw, str):
                return jsonify({"answer": raw, "sources": [], "status": "ask_user"})
            print(f"\n{'='*60}")
            print(f"[RAG BASELINE] QUERY: {message[:80]}")
            print(f"[RAG BASELINE] ROUTE: {raw.get('intent_route', 'UNKNOWN')}")
            print(f"[RAG BASELINE] All 6 agents SKIPPED")
            print(f"{'='*60}\n")
            return jsonify({
                "answer":          raw.get("answer", ""),
                "sources":         raw.get("sources", []),
                "status":          "rag_baseline",
                "trust_verdicts":  {"skipped": "RAG baseline mode — all agents disabled"},
                "trust_aggregate": {
                    "overall_verdict": "SKIPPED",
                    "overall_score":   None,
                    "breakdown":       {},
                    "agents_fired":    [],
                    "blocked_by":      None,
                },
            })

        # ══════════════════════════════════════════════════════════════════
        # LAYER III — AGENT 5: Safety & Ethics (PRE-GENERATION FIREWALL)
        # Runs BEFORE tutor_service — intercepts unsafe queries before any
        # LLM inference is invoked.
        # Hard FAIL → return immediately, Layers I + II never called.
        # ══════════════════════════════════════════════════════════════════
        trust_verdicts = {}

        safety_verdict = agent5.verify(
            question      = message,
            draft_answer  = "",
            persona_level = "Undergraduate Student",
        )
        trust_verdicts["agent5_safety"] = safety_verdict.to_dict()

        if safety_verdict.verdict == "FAIL":
            app.logger.warning(
                f"[AGENT 5 FAIL — PRE-GEN] score={safety_verdict.score:.2f} "
                f"| jailbreak={safety_verdict.jailbreak_detected} "
                f"| crisis={safety_verdict.crisis_detected} "
                f"| flags={safety_verdict.flags} "
                f"| query='{message[:80]}'"
            )
            if safety_verdict.crisis_detected and not safety_verdict.crisis_escalated:
                final_answer = (
                    "I'm concerned about what you've shared. Please reach out to "
                    "a mental health professional or contact the 988 Suicide & "
                    "Crisis Lifeline (call or text 988) — available 24/7. "
                    "You don't have to face this alone."
                )
            else:
                final_answer = (
                    "I'm not able to help with that request. "
                    "If you have a question about your course material, "
                    "I'd be happy to help — try asking about a concept, "
                    "assignment guidance, or anything from your NLP or ML syllabus. "
                    "For academic integrity concerns, please contact your course "
                    "instructor (Sagnik.Raychoudhury@unt.edu) or the university's "
                    "Academic Integrity Office."
                )
            return jsonify({
                "answer":         final_answer,
                "sources":        [],
                "status":         "safety_block",
                "trust_verdicts": trust_verdicts,
            })

        elif safety_verdict.verdict == "WARN":
            app.logger.info(
                f"[AGENT 5 WARN] flags={safety_verdict.flags} "
                f"| query='{message[:80]}'"
            )

        # ── LAYER I + II: Governance + Capability ─────────────────────────
        # Only reached if Agent 5 cleared the query as safe.
        # ───────────────────────────────────────────────────────────────────
        raw = await tutor_service.generate_answer(message)

        if isinstance(raw, str):
            return jsonify({"answer": raw, "sources": [], "status": "ask_user"})

        refined_chunks     = raw.get("refined_chunks", [])
        governance_profile = raw.get("resolved_profile", {})
        app.logger.info(f"[DEBUG] governance_profile keys: {list(governance_profile.keys())}")

        intent_route       = raw.get("intent_route", "GENERAL_ASSISTANCE")
        final_answer       = raw["answer"]

        # ══════════════════════════════════════════════════════════════════
        # LAYER III — POST-GENERATION AGENTS
        # Each agent receives raw["answer"] — original unmodified draft.
        # ══════════════════════════════════════════════════════════════════


        # # ── AGENT 6 — Age-Appropriateness (ALL routes, Hard BLOCK) ────────
        # # Runs on ALL routes. Hard BLOCK on FAIL — same tier as Agent 5.
        # # Distinct from Agent 5: asks "safe for THIS age?" not "safe for anyone?"
        # # ──────────────────────────────────────────────────────────────────
        # if governance_profile:
        #     age_verdict = agent6.verify(
        #         question           = message,
        #         draft_answer       = raw["answer"],
        #         governance_profile = governance_profile,
        #     )
        #     trust_verdicts["agent6_age"] = age_verdict.to_dict()
 
        #     if age_verdict.verdict == "FAIL":
        #         app.logger.warning(
        #             f"[AGENT 6 FAIL] score={age_verdict.score:.2f} "
        #             f"| flags={age_verdict.flags} | query='{message[:80]}'"
        #         )
        #         # Hard BLOCK — content not age-appropriate
        #         final_answer = (
        #             "I'm not able to deliver this response as it may not be "
        #             "appropriate for your learning level. Please rephrase your "
        #             "question or ask your instructor for guidance."
        #         )
 
        #     elif age_verdict.verdict == "WARN":
        #         app.logger.info(
        #             f"[AGENT 6 WARN] flags={age_verdict.flags} "
        #             f"| query='{message[:80]}'"
        #         )
        #         # Soft warn — annotate for younger learners only
        #         persona = governance_profile.get("persona_level", "")
        #         if persona in ("Elementary Learner", "Mid/High School Student"):
        #             final_answer += (
        #                 f"\n\n---\n⚠️ *Note: Some parts of this response may be "
        #                 f"challenging for your current level. Ask your teacher "
        #                 f"if you need help understanding any concepts.*"
        #             )
        # else:
        #     trust_verdicts["agent6_age"] = "skipped — no governance profile"


        # ── AGENT 6 — Age-Appropriateness (ALL routes, Hard BLOCK) ────────
        # Runs FIRST post-generation — hard block protects younger learners
        # before Agents 1-4 run. Mirrors Agent 5 pre-generation firewall.
        # Distinct from Agent 5: asks "safe for THIS age?" not "safe for anyone?"
        # ──────────────────────────────────────────────────────────────────
        if governance_profile is not None:
            age_verdict = agent6.verify(
                question           = message,
                draft_answer       = raw["answer"],
                governance_profile = governance_profile,
            )
            trust_verdicts["agent6_age"] = age_verdict.to_dict()

            if age_verdict.verdict == "FAIL":
                app.logger.warning(
                    f"[AGENT 6 FAIL] score={age_verdict.score:.2f} "
                    f"| flags={age_verdict.flags} | query='{message[:80]}'"
                )
                final_answer = (
                    "I'm not able to deliver this response as it may not be "
                    "appropriate for your learning level. Please rephrase your "
                    "question or ask your instructor for guidance."
                )
                # Return immediately — Agents 1-4 never called
                return jsonify({
                    "answer":         final_answer,
                    "sources":        [],
                    "status":         "age_block",
                    "trust_verdicts": trust_verdicts,
                })

            elif age_verdict.verdict == "WARN":
                app.logger.info(
                    f"[AGENT 6 WARN] flags={age_verdict.flags} "
                    f"| query='{message[:80]}'"
                )
                # Soft warn — annotate for younger learners only
                persona = governance_profile.get("persona_level", "")
                if persona in ("Elementary Learner", "Mid/High School Student"):
                    final_answer += (
                        f"\n\n---\n⚠️ *Note: Some parts of this response may be "
                        f"challenging for your current level. Ask your teacher "
                        f"if you need help understanding any concepts.*"
                    )
        else:
            trust_verdicts["agent6_age"] = "skipped — no governance profile"
 

        # ── AGENT 1 — Factual Accuracy (RAG route only) ───────────────────
        # Severity: SOFT WARN
        # ──────────────────────────────────────────────────────────────────
        factual_verdict = None  # initialise so Agent 2 can safely reference it

        if refined_chunks:
            factual_verdict = agent1.verify(
                question       = message,
                draft_answer   = raw["answer"],
                context_chunks = refined_chunks,
            )
            trust_verdicts["agent1_factual"] = factual_verdict.to_dict()

            if factual_verdict.verdict == "FAIL":
                app.logger.warning(
                    f"[AGENT 1 FAIL] rate={factual_verdict.hallucination_rate:.2f} "
                    f"| flags={factual_verdict.flags} | query='{message[:80]}'"
                )
                final_answer = (
                    "I was unable to verify this answer against your course materials. "
                    "Please consult your textbook or ask your instructor."
                )

            elif factual_verdict.verdict == "WARN":
                app.logger.info(
                    f"[AGENT 1 WARN] flags={factual_verdict.flags} "
                    f"| query='{message[:80]}'"
                )
                warn_flags = (
                    ", ".join(factual_verdict.flags)
                    if factual_verdict.flags else "low citation coverage"
                )
                final_answer += (
                    f"\n\n---\n⚠️ *Transparency note: Minor grounding gaps detected "
                    f"({warn_flags}). Please verify against your course materials.*"
                )
        else:
            trust_verdicts["agent1_factual"] = "skipped — non-RAG route"

        # ── AGENT 2 — Transparency & Explainability (ALL routes) ──────────
        # RAG mode:     checks [File: X, Page: Y] course citations.
        # General mode: checks web URLs as transparency signal.
        # Severity: SOFT WARN — FAIL annotates response, does not block.
        # ──────────────────────────────────────────────────────────────────
        transparency_verdict = agent2.verify(
            question       = message,
            draft_answer   = raw["answer"],
            context_chunks = refined_chunks,  # empty list for non-RAG
        )
        trust_verdicts["agent2_transparency"] = transparency_verdict.to_dict()

        if transparency_verdict.verdict == "FAIL":
            app.logger.warning(
                f"[AGENT 2 FAIL] score={transparency_verdict.score:.2f} "
                f"| flags={transparency_verdict.flags} | query='{message[:80]}'"
            )
            # Only annotate if Agent 1 hasn't already annotated
            # Safe check — factual_verdict is None for non-RAG routes
            agent1_already_annotated = (
                factual_verdict is not None and
                factual_verdict.verdict in ("FAIL", "WARN")
            )
            if not agent1_already_annotated:
                trans_flags = (
                    ", ".join(transparency_verdict.flags)
                    if transparency_verdict.flags else "low traceability"
                )
                final_answer += (
                    f"\n\n---\n⚠️ *Transparency note: This response has "
                    f"traceability gaps ({trans_flags}). Consider verifying "
                    f"claims against authoritative sources.*"
                )

        elif transparency_verdict.verdict == "WARN":
            app.logger.info(
                f"[AGENT 2 WARN] flags={transparency_verdict.flags} "
                f"| query='{message[:80]}'"
            )
            # Audit log only — WARN does not annotate student-facing answer
        


        # ── AGENT 3 — Pedagogical Alignment (ALL routes) ──────────────────
        # Severity: ADVISORY LOG only.
        # Response always delivered untouched regardless of verdict.
        # FAIL/WARN logged as pedagogical drift events for EduTrust-Eval.
        # ──────────────────────────────────────────────────────────────────
        if governance_profile:
            pedagogical_verdict = agent3.verify(
                question           = message,
                draft_answer       = raw["answer"],
                governance_profile = governance_profile,
                intent_route       = intent_route,
            )
            trust_verdicts["agent3_pedagogical"] = pedagogical_verdict.to_dict()
 
            if pedagogical_verdict.verdict == "FAIL":
                app.logger.warning(
                    f"[AGENT 3 FAIL — ADVISORY] score={pedagogical_verdict.score:.2f} "
                    f"| flags={pedagogical_verdict.flags} | query='{message[:80]}'"
                )
                # Advisory only — response NOT modified, NOT blocked
 
            elif pedagogical_verdict.verdict == "WARN":
                app.logger.info(
                    f"[AGENT 3 WARN — ADVISORY] flags={pedagogical_verdict.flags} "
                    f"| query='{message[:80]}'"
                )
                # Advisory only — logged for longitudinal drift analysis
        else:
            trust_verdicts["agent3_pedagogical"] = "skipped — no governance profile"
 



        # ── AGENT 4 — Bias & Fairness (ALL routes) ────────────────────────
        # Only agent with cross-layer dependency: reads governance_profile.
        # Severity: SOFT WARN — logged for EduTrust-Eval, does not block.
        # ──────────────────────────────────────────────────────────────────
        if governance_profile:
            bias_verdict = agent4.verify(
                question           = message,
                draft_answer       = raw["answer"],
                governance_profile = governance_profile,
            )
            trust_verdicts["agent4_bias"] = bias_verdict.to_dict()

            if bias_verdict.verdict == "FAIL":
                app.logger.warning(
                    f"[AGENT 4 FAIL] score={bias_verdict.score:.2f} "
                    f"| pvr={bias_verdict.policy_violation_rate:.2f} "
                    f"| flags={bias_verdict.flags} | query='{message[:80]}'"
                )

            elif bias_verdict.verdict == "WARN":
                app.logger.info(
                    f"[AGENT 4 WARN] flags={bias_verdict.flags} "
                    f"| query='{message[:80]}'"
                )
        else:
            trust_verdicts["agent4_bias"] = "skipped — no governance profile"
        

        # ════════════════════════════════════════════════════════════════
        # 🔬 TRUST AGGREGATOR — EduTrust-Eval Overall Score
        # Severity-weighted: Hard Block > Soft WARN > Advisory LOG
        # ════════════════════════════════════════════════════════════════
        def compute_trust_aggregate(trust_verdicts: dict) -> dict:
            """
            Computes a final cumulative trust score and verdict across all
            6 agents. Mirrors the severity-weighted architecture from Slide 16.

            Hard Block agents (5, 6): FAIL = immediate overall FAIL, score=0.
            Soft WARN agents (1, 2, 4): FAIL/WARN contributes to score, no block.
            Advisory agent (3): always contributes to score, never blocks.

            Weights (sum to 1.0 across all 6 agents):
                Agent 5 Safety:        0.25  (highest — pre-gen firewall)
                Agent 6 Age:           0.20  (hard block post-gen)
                Agent 1 Factual:       0.20  (RAG route only, else redistributed)
                Agent 2 Transparency:  0.15
                Agent 4 Bias:          0.12
                Agent 3 Pedagogical:   0.08  (advisory — lowest weight)
            """

            WEIGHTS = {
                "agent5_safety":      0.25,
                "agent6_age":         0.20,
                "agent1_factual":     0.20,
                "agent2_transparency":0.15,
                "agent4_bias":        0.12,
                "agent3_pedagogical": 0.08,
            }

            # ── Hard Block check first ────────────────────────────────────
            for hard_block_agent in ["agent5_safety", "agent6_age"]:
                verdict = trust_verdicts.get(hard_block_agent, {})
                if isinstance(verdict, dict) and verdict.get("verdict") == "FAIL":
                    return {
                        "overall_verdict": "BLOCKED",
                        "overall_score":   0.0,
                        "breakdown":       {k: _extract_score(v) for k, v in trust_verdicts.items()},
                        "agents_fired":    [k for k, v in trust_verdicts.items() if isinstance(v, dict)],
                        "blocked_by":      hard_block_agent,
                    }

            # ── Weighted mean for remaining agents ────────────────────────
            total_weight = 0.0
            weighted_sum = 0.0
            agents_fired = []
            breakdown    = {}

            for agent_key, weight in WEIGHTS.items():
                verdict = trust_verdicts.get(agent_key)

                # Skipped agents (non-RAG route for Agent 1, no governance profile)
                if isinstance(verdict, str) and "skipped" in verdict:
                    breakdown[agent_key] = "skipped"
                    continue

                if not isinstance(verdict, dict):
                    breakdown[agent_key] = "not_run"
                    continue

                score = _extract_score(verdict)
                breakdown[agent_key]  = round(score, 3)
                weighted_sum          += score * weight
                total_weight          += weight
                agents_fired.append(agent_key)

            # Normalise by actual weight fired (handles skipped agents)
            overall_score = (weighted_sum / total_weight) if total_weight > 0 else 0.0
            overall_score = round(overall_score, 3)

            # Verdict thresholds
            if overall_score >= 0.75:
                overall_verdict = "PASS"
            elif overall_score >= 0.50:
                overall_verdict = "WARN"
            else:
                overall_verdict = "FAIL"

            return {
                "overall_verdict": overall_verdict,
                "overall_score":   overall_score,
                "breakdown":       breakdown,
                "agents_fired":    agents_fired,
                "blocked_by":      None,
            }


        def _extract_score(verdict) -> float:
            """Safely extract numeric score from agent verdict dict."""
            if not isinstance(verdict, dict):
                return 0.0
            try:
                return float(verdict.get("score", 0.0))
            except (TypeError, ValueError):
                return 0.0


        # # ── Trust Aggregator ──────────────────────────────────────────────
        # trust_aggregate = compute_trust_aggregate(trust_verdicts)

        # # ── Return verified response ───────────────────────────────────────
        # print(f"\n{'='*60}")
        # print(f"QUERY: {message[:80]}")
        # print(f"ROUTE: {intent_route}")
        # print(f"OVERALL: {trust_aggregate['overall_verdict']} "
        #       f"| SCORE: {trust_aggregate['overall_score']}")
        # print(f"BREAKDOWN: {trust_aggregate['breakdown']}")
        # print(f"FULL VERDICTS:")
        # print(json.dumps(trust_verdicts, indent=2, default=str))




        # # ── Only show aggregate score when all applicable agents ran ──
        # agent5_verdict = trust_verdicts.get("agent5_safety", {})
        # hard_blocked   = (isinstance(agent5_verdict, dict) and
        #                 agent5_verdict.get("verdict") == "FAIL" and
        #                 "agent1_factual" not in trust_verdicts and
        #                 "agent2_transparency" not in trust_verdicts)

        # if hard_blocked:
        #     print(f"OVERALL:  🚫 HARD BLOCKED — Response suppressed before LLM call")
        #     print(f"AGENT 5:  FAIL | Score: {agent5_verdict.get('score', 0.0)}")
        #     print(f"          Jailbreak: {agent5_verdict.get('jailbreak_detected')}")
        #     print(f"          Crisis:    {agent5_verdict.get('crisis_detected')}")
        #     print(f"          Agents 1,2,3,4,6: NOT INVOKED (latency saved)")
        # else:
        #     print(f"OVERALL:  {trust_aggregate['overall_verdict']} | SCORE: {trust_aggregate['overall_score']}")
        #     print(f"BREAKDOWN:{trust_aggregate['breakdown']}")

        # print(f"{'='*60}\n")





        # ── Trust Aggregator ──────────────────────────────────────────────
        trust_aggregate = compute_trust_aggregate(trust_verdicts)

        # ── Terminal print ────────────────────────────────────────────────
        agent5_verdict = trust_verdicts.get("agent5_safety", {})
        hard_blocked   = (isinstance(agent5_verdict, dict) and
                        agent5_verdict.get("verdict") == "FAIL" and
                        "agent1_factual" not in trust_verdicts and
                        "agent2_transparency" not in trust_verdicts)

        print(f"\n{'='*60}")
        print(f"QUERY:    {message[:80]}")
        print(f"ROUTE:    {intent_route}")

        if hard_blocked:
            print(f"OVERALL:  🚫 HARD BLOCKED — Response suppressed before LLM call")
            print(f"AGENT 5:  FAIL | Score: {agent5_verdict.get('score', 0.0)}")
            print(f"          Jailbreak: {agent5_verdict.get('jailbreak_detected')}")
            print(f"          Crisis:    {agent5_verdict.get('crisis_detected')}")
            print(f"          Agents 1,2,3,4,6: NOT INVOKED (latency saved)")
        else:
            print(f"OVERALL:  {trust_aggregate['overall_verdict']} "
                f"| SCORE: {trust_aggregate['overall_score']}")
            print(f"BREAKDOWN:{trust_aggregate['breakdown']}")
            print(f"FULL VERDICTS:")
            print(json.dumps(trust_verdicts, indent=2, default=str))

        print(f"{'='*60}\n")

        
        
        return jsonify({
            "answer":         final_answer,
            "sources":        raw.get("sources", []),
            "status":         "success",
            "trust_verdicts": trust_verdicts,
            "trust_aggregate": trust_aggregate,
        })

    except Exception as e:
        app.logger.error(f"Chat Error: {str(e)}")
        return jsonify({
            "error":   "Tutor encountered an issue. Check backend logs.",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001, use_reloader=False)