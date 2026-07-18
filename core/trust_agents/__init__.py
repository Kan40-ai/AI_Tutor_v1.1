"""
=============================================================================
ETHOS AI — Agent 1 Integration Guide for tutor_service.py
=============================================================================

THREE CHANGES ONLY. Nothing else in tutor_service.py needs to change.

CHANGE 1: Add the import (top of file, after existing imports)
CHANGE 2: Initialise the agent in __init__ (one line)
CHANGE 3: Replace the raw judge_prompt block in generate_answer (Stage 4)
          AND fix the sources key bug in the Stage 5 return

Also included below:
  - Folder structure to create
  - The __init__.py file needed for the trust_agents package

=============================================================================
"""


# =============================================================================
# FOLDER STRUCTURE — create this inside your project root
# =============================================================================
#
#   AI Tutor - v1.1/
#   └── core/
#       ├── trust_agents/                 ← NEW folder
#       │   ├── __init__.py               ← NEW (empty or with exports)
#       │   └── agent1_factual_accuracy.py  ← the file you just received
#       ├── governance.py
#       ├── intent_router.py
#       ├── rag.py
#       └── ...
#
# =============================================================================


# =============================================================================
# core/trust_agents/__init__.py   (create this file — content below)
# =============================================================================

INIT_PY_CONTENT = """
# Trust Enforcement Layer — Agent Package
# Agents 1-6 live here, one file per trust criterion.
from .agent1_factual_accuracy import FactualAccuracyAgent, FactualVerdict

__all__ = [
    "FactualAccuracyAgent",
    "FactualVerdict",
]
"""


# =============================================================================
# CHANGE 1 — ADD IMPORT at top of tutor_service.py
# =============================================================================
# Find this existing block near the top of tutor_service.py:
#
#   from core.governance import GovernanceLayer
#
# ADD the line immediately after it:
#
#   from core.trust_agents.agent1_factual_accuracy import FactualAccuracyAgent
#


# =============================================================================
# CHANGE 2 — INITIALISE in TutorService.__init__()
# =============================================================================
# Find this existing line in __init__ (around line 253):
#
#   self.governance = GovernanceLayer(self.tutor_engine.llm)
#
# ADD the line immediately after it:
#
#   self.agent1 = FactualAccuracyAgent(llm_client=self.tutor_engine.llm)
#


# =============================================================================
# CHANGE 3 — REPLACE Stage 4 block in generate_answer()
# =============================================================================
#
# FIND AND DELETE these lines (approximately lines 682-712 in your file):
#
# ─────────────────────────────────────────────────────────────────────────────
#   # ==========================================
#   # STAGE 4: THE VERIFICATION AGENT (Post-Generation NLI)
#   # ==========================================
#   print(f"🕵️ Step 4: Verification Agent (LLM-Judge) validating evidence-claim entailment...")
#   judge_prompt = f"""
#   You are a strict NLI (Natural Language Inference) Entailment Judge.
#   Read the CONTEXT, then evaluate the DRAFT ANSWER.
#
#   Your ONLY job is to determine if the DRAFT ANSWER is 100% mathematically and factually entailed by the CONTEXT.
#   If the DRAFT ANSWER hallucinates details, uses outside knowledge, or makes claims not explicitly found in the CONTEXT, you must reject it.
#
#   CONTEXT:
#   {context_str}
#
#   DRAFT ANSWER:
#   {draft_answer}
#
#   If fully entailed by the context, output exactly: PASS
#   If it contains hallucinations or ungrounded claims, output exactly: FAIL
#   """
#
#   judge_verdict = self.tutor_engine.llm.generate_content(judge_prompt).text.strip()
#
#   # Catch overconfident LLM hallucinations post-generation
#   if "FAIL" in judge_verdict:
#       print("\n" + "="*60)
#       print("🛑 [STEP 4 ROUTING] NLI JUDGE VETO")
#       print("Diagnosis: Hallucination Detected! The draft contained ungrounded facts.")
#       print("Action: Blocking false citation. Routing to General Fallback...")
#       print("="*60 + "\n")
#       return trigger_fallback("Verification Agent Detected Hallucination/Entailment Failure")
# ─────────────────────────────────────────────────────────────────────────────
#
# REPLACE WITH:
#
# ─────────────────────────────────────────────────────────────────────────────
#   # ==========================================
#   # STAGE 4: AGENT 1 — FACTUAL ACCURACY & HALLUCINATION CHECK
#   # Trust Enforcement Layer (parallel agent panel — Agent 1 of 6)
#   # Severity tier: SOFT WARN
#   # ==========================================
#   print(f"\n🔍 Step 4: Routing to Agent 1 — Factual Accuracy & Hallucination Check...")
#
#   factual_verdict = self.agent1.verify(
#       question       = question,
#       draft_answer   = draft_answer,
#       context_chunks = refined_chunks,
#   )
#
#   # Hard FAIL: hallucination detected — route to fallback
#   if factual_verdict.verdict == "FAIL":
#       print("🛑 [AGENT 1] FAIL — Hallucination detected. Routing to fallback.")
#       return trigger_fallback(
#           f"Agent 1 (Factual Accuracy) FAIL — "
#           f"hallucination_rate={factual_verdict.hallucination_rate:.2f}, "
#           f"flags={factual_verdict.flags}"
#       )
#
#   # Soft WARN: log it, annotate the answer, but still deliver
#   agent1_disclaimer = ""
#   if factual_verdict.verdict == "WARN":
#       print("⚠️  [AGENT 1] WARN — Minor grounding issue detected. Annotating response.")
#       warn_flags = ", ".join(factual_verdict.flags) if factual_verdict.flags else "low citation coverage"
#       agent1_disclaimer = (
#           f"\n\n---\n"
#           f"⚠️ *Transparency note: This response may have minor grounding gaps "
#           f"({warn_flags}). Please verify key facts against your course materials.*"
#       )
# ─────────────────────────────────────────────────────────────────────────────


# =============================================================================
# CHANGE 3b — FIX the Stage 5 return (same area, a few lines below)
# =============================================================================
#
# FIND (approximately line 725):
#
#   return {
#       "answer": draft_answer,
#       "sources": [c['metadata'].get('source') for c in refined_chunks],
#       "confidence_score": "High (Verified by Agent)"
#   }
#
# REPLACE WITH:
#
# ─────────────────────────────────────────────────────────────────────────────
#   # ==========================================
#   # STAGE 5: VERIFIED OUTPUT
#   # ==========================================
#   print(f"✅ Step 5: Agent 1 passed. Returning grounded answer.")
#   print("\n" + "=" * 60)
#   print("📚 VERIFIED RAG RESPONSE (Grounded, Trust-Enforced):")
#   print("=" * 60)
#   print(draft_answer)
#   print()
#
#   # Fix: use 'filepath' key (not 'source') — matches your Pinecone metadata
#   sources = list({
#       c['metadata'].get('filepath', c['metadata'].get('source', 'Unknown'))
#       for c in refined_chunks
#   })
#
#   return {
#       "answer":           draft_answer + agent1_disclaimer,
#       "sources":          sources,
#       "confidence_score": f"Agent1={factual_verdict.verdict} "
#                           f"(score={factual_verdict.score:.2f})",
#       "trust_verdicts":   {"agent1_factual": factual_verdict.to_dict()},
#   }
# ─────────────────────────────────────────────────────────────────────────────


# =============================================================================
# FULL CONTEXT — what generate_answer() Stage 4 + 5 looks like AFTER changes
# Copy-paste this entire block to replace lines 682-729 in tutor_service.py
# =============================================================================

STAGE_4_AND_5_REPLACEMENT = '''
            # ==========================================
            # STAGE 4: AGENT 1 — FACTUAL ACCURACY & HALLUCINATION CHECK
            # Trust Enforcement Layer (parallel agent panel — Agent 1 of 6)
            # Severity tier: SOFT WARN
            # Research: Zheng et al. (2023) NLI-as-judge, Li et al. (2025) RAG grounding
            # ==========================================
            print(f"\\n🔍 Step 4: Routing to Agent 1 — Factual Accuracy & Hallucination Check...")

            factual_verdict = self.agent1.verify(
                question       = question,
                draft_answer   = draft_answer,
                context_chunks = refined_chunks,
            )

            # Hard FAIL: hallucination detected — block and route to fallback
            if factual_verdict.verdict == "FAIL":
                print("🛑 [AGENT 1] FAIL — Hallucination detected. Routing to fallback.")
                return trigger_fallback(
                    f"Agent 1 (Factual Accuracy) FAIL — "
                    f"hallucination_rate={factual_verdict.hallucination_rate:.2f}, "
                    f"flags={factual_verdict.flags}"
                )

            # Soft WARN: annotate the response but still deliver it
            agent1_disclaimer = ""
            if factual_verdict.verdict == "WARN":
                print("⚠️  [AGENT 1] WARN — Minor grounding issue. Annotating response.")
                warn_flags = ", ".join(factual_verdict.flags) if factual_verdict.flags else "low citation coverage"
                agent1_disclaimer = (
                    f"\\n\\n---\\n"
                    f"⚠️ *Transparency note: This response may have minor grounding gaps "
                    f"({warn_flags}). Please verify key facts against your course materials.*"
                )

            # ==========================================
            # STAGE 5: VERIFIED OUTPUT
            # ==========================================
            print(f"✅ Step 5: Agent 1 passed. Returning grounded answer.")
            print("\\n" + "=" * 60)
            print("📚 VERIFIED RAG RESPONSE (Grounded, Trust-Enforced):")
            print("=" * 60)
            print(draft_answer)
            print()

            # Fix: use 'filepath' key (matches Pinecone metadata schema)
            sources = list({
                c["metadata"].get("filepath", c["metadata"].get("source", "Unknown"))
                for c in refined_chunks
            })

            return {
                "answer":           draft_answer + agent1_disclaimer,
                "sources":          sources,
                "confidence_score": f"Agent1={factual_verdict.verdict} "
                                    f"(score={factual_verdict.score:.2f})",
                "trust_verdicts":   {"agent1_factual": factual_verdict.to_dict()},
            }
'''



# Trust Enforcement Layer — Agent Package
# One file per trust criterion. Agents run in parallel via trust_aggregator.py.
#
# Agents implemented:
#   Agent 1 — Factual Accuracy    (agent1_factual_accuracy.py)  — Moderate gap
#   Agent 2 — Transparency        (agent2_transparency.py)      — Moderate gap
#   Agent 3 — Pedagogical Alignment   (agent3_pedagogical_alignment.py)   — High gap
#   Agent 4 — Bias & Fairness     (agent4_bias_fairness.py)     — High gap
#   Agent 5 — Safety & Ethics     (agent5_safety_ethics.py)     — High gap
#   Agent 6 — Age-Appropriateness     (agent6_age_appropriateness.py)     — High gap
 
from .agent1_factual_accuracy import FactualAccuracyAgent, FactualVerdict
from .agent2_transparency      import TransparencyAgent,     TransparencyVerdict
from .agent3_pedagogical_alignment import PedagogicalAlignmentAgent,  PedagogicalVerdict
from .agent4_bias_fairness    import BiasFairnessAgent,    BiasVerdict
from .agent5_safety_ethics    import SafetyEthicsAgent,    SafetyVerdict
from .agent6_age_appropriateness   import AgeAppropriatenessAgent,    AgeVerdict
 
__all__ = [
    "FactualAccuracyAgent",
    "FactualVerdict",
    "TransparencyAgent",     
    "TransparencyVerdict",
    "PedagogicalAlignmentAgent", 
    "PedagogicalVerdict",
    "BiasFairnessAgent",
    "BiasVerdict",
    "SafetyEthicsAgent",
    "SafetyVerdict",
    "AgeAppropriatenessAgent",   
    "AgeVerdict",
]