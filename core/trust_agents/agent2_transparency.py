"""
=============================================================================
ETHOS AI — TRUST ENFORCEMENT LAYER
Agent 2: Transparency & Explainability
=============================================================================

RESEARCH GROUNDING:
    - RAG citation pipelines; audit logs in enterprise guardrails:
        Li et al. (2025). "Retrieval-augmented generation for educational
        application: A systematic survey." Computers & Education: AI.
    - LLM-as-judge evaluation pattern:
        Zheng et al. (2023). "Judging LLM-as-a-Judge with MT-Bench
        and Chatbot Arena." NeurIPS 2023.
    - Transparency & Explainability row (Moderate Gap):
        Slide 14 framework — Tools: plan/trace logger, evidence highlighter.
        Policies: citation-required for claims; step logs for audit.

RUNS ON: ALL routes.
    RAG route:          checks [File: X, Page: Y] course citations.
    General LLM route:  checks web URLs as transparency signal.
    YouTube route:      checks web URLs as transparency signal.

SEVERITY: Soft WARN — FAIL annotates response, does not hard-block.
=============================================================================
"""

# import re
# import json
# import time
# from dataclasses import dataclass, field


# @dataclass
# class TransparencyVerdict:
#     agent:                str   = "transparency"
#     verdict:              str   = "PASS"
#     score:                float = 1.0
#     citation_coverage:    float = 1.0
#     uncertainty_score:    float = 1.0
#     explainability_score: float = 1.0
#     audit_completeness:   float = 1.0
#     flags:                list  = field(default_factory=list)
#     reasoning:            str   = ""
#     source:               str   = "Agent2_Transparency"
#     latency_ms:           float = 0.0

#     def to_dict(self) -> dict:
#         def safe(v):
#             try:
#                 f = float(v)
#                 return round(f, 3) if (f == f and abs(f) != float('inf')) else 0.0
#             except Exception:
#                 return 0.0
#         return {
#             "agent":                self.agent,
#             "verdict":              self.verdict,
#             "score":                safe(self.score),
#             "citation_coverage":    safe(self.citation_coverage),
#             "uncertainty_score":    safe(self.uncertainty_score),
#             "explainability_score": safe(self.explainability_score),
#             "audit_completeness":   safe(self.audit_completeness),
#             "flags":                self.flags,
#             "reasoning":            self.reasoning,
#             "source":               self.source,
#             "latency_ms":           safe(self.latency_ms),
#         }


# class TransparencyAgent:
#     """
#     Agent 2 — Transparency & Explainability.

#     Runs on ALL routes with mode-switching:
#       - RAG mode (context_chunks non-empty):
#             Check A counts [File: X, Page: Y] course citations.
#             Check C evaluates source traceability against retrieved chunks.
#       - General LLM / YouTube mode (context_chunks empty):
#             Check A counts web URLs as transparency signals.
#             Check C evaluates reasoning visibility and web source quality.
#     """

#     CITATION_PATTERN = re.compile(
#         r'\[File:\s*.+?,\s*Page:\s*[\w\-/\.]+\]',
#         re.IGNORECASE
#     )

#     WEB_URL_PATTERN = re.compile(
#         r'https?://[^\s<>"\']+',
#         re.IGNORECASE
#     )

#     UNCERTAINTY_POSITIVE = [
#         r"\baccording to\b",
#         r"\bbased on\b",
#         r"\bthe (context|document|source|material|slide|textbook) (states?|says?|indicates?|shows?|suggests?)\b",
#         r"\bas (stated|mentioned|described|outlined|explained) in\b",
#         r"\bper the (provided|course|available) (context|material|document)\b",
#         r"\bthe (provided|retrieved|available) context\b",
#         r"\bi('m| am) not (certain|sure|confident)\b",
#         r"\bthis may\b",
#         r"\bthis might\b",
#         r"\bit (appears?|seems?|suggests?)\b",
#         r"\bpossibly\b",
#         r"\blikely\b",
#     ]

#     UNCERTAINTY_NEGATIVE = [
#         r"\bit is (definitely|absolutely|certainly|always|never) (true|the case|correct)\b",
#         r"\bthe (fact|truth) is\b",
#         r"\bwithout (a )?doubt\b",
#         r"\b(definitely|absolutely|certainly) (means?|shows?|proves?|demonstrates?)\b",
#     ]

#     def __init__(self, llm_client):
#         self.llm = llm_client
#         self._positive_regex = [
#             re.compile(p, re.IGNORECASE) for p in self.UNCERTAINTY_POSITIVE
#         ]
#         self._negative_regex = [
#             re.compile(p, re.IGNORECASE) for p in self.UNCERTAINTY_NEGATIVE
#         ]

#     def verify(
#         self,
#         question:       str,
#         draft_answer:   str,
#         context_chunks: list,
#     ) -> TransparencyVerdict:
#         t0 = time.time()
#         has_course_context = len(context_chunks) > 0
#         mode = "RAG" if has_course_context else "General LLM"

#         print("\n" + "=" * 60)
#         print(f"🔍 [AGENT 2] Transparency & Explainability Check [{mode} mode]")
#         print("=" * 60)

#         if not draft_answer or not draft_answer.strip():
#             return TransparencyVerdict(
#                 verdict    = "WARN",
#                 score      = 0.0,
#                 flags      = ["EMPTY_DRAFT"],
#                 reasoning  = "Draft answer was empty — cannot assess transparency.",
#                 latency_ms = (time.time() - t0) * 1000,
#             )

#         print("   → Check A: Source coverage (rule-based)...")
#         check_a = self._check_source_coverage(draft_answer, has_course_context)

#         print("   → Check B: Uncertainty acknowledgment (rule-based)...")
#         check_b = self._check_uncertainty_language(draft_answer)

#         print("   → Check C: Explainability & audit completeness (LLM)...")
#         check_c = self._run_explainability_judge(
#             question, draft_answer, context_chunks, has_course_context
#         )

#         verdict            = self._combine_checks(check_a, check_b, check_c)
#         verdict.latency_ms = (time.time() - t0) * 1000

#         self._print_summary(verdict)
#         return verdict

#     # ------------------------------------------------------------------
#     # CHECK A — SOURCE COVERAGE (mode-switching, rule-based)
#     # ------------------------------------------------------------------

#     def _check_source_coverage(
#         self, draft_answer: str, has_course_context: bool
#     ) -> dict:
#         if has_course_context:
#             # RAG mode — course citations [File: X, Page: Y]
#             matches = self.CITATION_PATTERN.findall(draft_answer)
#             count   = len(matches)
#             if count == 0:
#                 print(f"      ❌ No course citations found.")
#                 return {"citation_coverage": 0.0, "flags": ["NO_INLINE_CITATIONS"]}
#             elif count == 1:
#                 print(f"      ⚠️  One citation found: {matches[0]}")
#                 return {"citation_coverage": 0.5, "flags": ["LOW_CITATION_COUNT"]}
#             else:
#                 print(f"      ✅ {count} course citations found.")
#                 return {"citation_coverage": 1.0, "flags": []}
#         else:
#             # General LLM / YouTube mode — web URLs as transparency signal
#             matches = self.WEB_URL_PATTERN.findall(draft_answer)
#             count   = len(matches)
#             if count == 0:
#                 print(f"      ❌ No web sources found.")
#                 return {"citation_coverage": 0.0, "flags": ["NO_WEB_SOURCES"]}
#             elif count < 2:
#                 print(f"      ⚠️  Only {count} web source found.")
#                 return {"citation_coverage": 0.5, "flags": ["LOW_WEB_SOURCE_COUNT"]}
#             else:
#                 print(f"      ✅ {count} web sources found.")
#                 return {"citation_coverage": 1.0, "flags": []}

#     # ------------------------------------------------------------------
#     # CHECK B — UNCERTAINTY ACKNOWLEDGMENT (rule-based)
#     # ------------------------------------------------------------------

#     def _check_uncertainty_language(self, draft_answer: str) -> dict:
#         positive_hits = sum(
#             1 for p in self._positive_regex if p.search(draft_answer)
#         )
#         negative_hits = sum(
#             1 for p in self._negative_regex if p.search(draft_answer)
#         )
#         flags = []

#         if positive_hits == 0 and negative_hits == 0:
#             score = 0.6
#             flags.append("NO_UNCERTAINTY_LANGUAGE")
#             print(f"      ⚠️  No uncertainty language detected.")
#         elif positive_hits > 0 and negative_hits == 0:
#             score = 1.0
#             print(f"      ✅ {positive_hits} epistemic markers found.")
#         elif positive_hits > 0 and negative_hits > 0:
#             score = 0.7
#             flags.append("MIXED_UNCERTAINTY_SIGNALS")
#             print(f"      ⚠️  Mixed signals: {positive_hits} positive, "
#                   f"{negative_hits} overconfident.")
#         else:
#             score = 0.3
#             flags.append("OVERCONFIDENT_LANGUAGE")
#             print(f"      ❌ Overconfident language without attribution.")

#         return {
#             "uncertainty_score": score,
#             "positive_hits":     positive_hits,
#             "negative_hits":     negative_hits,
#             "flags":             flags,
#         }

#     # ------------------------------------------------------------------
#     # CHECK C — EXPLAINABILITY JUDGE (LLM, mode-switching)
#     # ------------------------------------------------------------------

#     def _run_explainability_judge(
#         self,
#         question:          str,
#         draft_answer:      str,
#         context_chunks:    list,
#         has_course_context: bool,
#     ) -> dict:
#         if has_course_context:
#             # RAG mode — evaluate against retrieved course chunks
#             # context_preview = "\n---\n".join([
#             #     f"[Chunk {i+1}] "
#             #     f"{str(c.get('text', c.get('page_content', str(c))))[:600]}..."
#             #     for i, c in enumerate(context_chunks[:5])
#             # ])

#             context_preview = "\n---\n".join([
#                     f"[Chunk {i+1}] "
#                     f"[File: {c.get('metadata', {}).get('filepath', c.get('metadata', {}).get('source', 'Unknown'))}, "
#                     f"Page: {c.get('metadata', {}).get('page', 'N/A')}]\n"
#                     f"{str(c.get('text', c.get('page_content', str(c))))[:600]}..."
#                     for i, c in enumerate(context_chunks[:5])
#                 ]) if context_chunks else "No context chunks available."

#             mode_note = (
#                 "NOTE: The factual accuracy of this response has already been "
#                 "independently verified by an NLI entailment judge (Agent 1). "
#                 "Do NOT re-evaluate factual accuracy. Your job is ONLY to evaluate "
#                 "transparency quality — citation formatting, reasoning visibility, "
#                 "and uncertainty acknowledgment."
#             )
#             source_traceability_desc = (
#                 "Can a student or educator verify each factual claim by going to "
#                 "the cited [File: X, Page: Y] source? Are citations specific enough?"
#             )
#             context_section = f"RETRIEVED CONTEXT (first 5 chunks):\n{context_preview}"
#         else:
#             # General LLM mode — evaluate web source quality
#             mode_note = (
#                 "This is a general knowledge response — no course materials were "
#                 "retrieved. Evaluate transparency based on web source quality, "
#                 "reasoning visibility, and appropriate acknowledgment that this "
#                 "is general knowledge rather than course-specific content."
#             )
#             source_traceability_desc = (
#                 "Does the response provide credible web sources (URLs) that the "
#                 "student can visit to verify the information? Are the sources "
#                 "reputable (e.g. academic, government, established organisations)?"
#             )
#             context_section = (
#                 "CONTEXT TYPE: General knowledge response — no course chunks retrieved.\n"
#                 "Evaluate based on web sources and reasoning quality only."
#             )

#         judge_prompt = f"""
# You are a Transparency & Explainability Judge for an educational AI system.

# {mode_note}

# STUDENT QUESTION:
# {question}

# {context_section}

# DRAFT RESPONSE (to audit):
# {draft_answer}

# EVALUATE on these three explainability dimensions (score 0.0–1.0 each):

# 1. REASONING_VISIBILITY (0.0=opaque, 1.0=fully transparent):
#    Does the response show its reasoning — explaining WHY, not just WHAT?
#    Does it connect claims to sources or evidence explicitly?

# 2. SOURCE_TRACEABILITY (0.0=untraceable, 1.0=fully traceable):
#    {source_traceability_desc}

# 3. UNCERTAINTY_ACKNOWLEDGMENT (0.0=overconfident, 1.0=appropriately humble):
#    Does the response acknowledge its knowledge limits appropriately?
#    Does it avoid presenting uncertain claims as established facts?

# VERDICT RULES:
# - "PASS"  → all dimensions >= 0.75
# - "WARN"  → any dimension between 0.50 and 0.74
# - "FAIL"  → any dimension < 0.50

# Respond ONLY with valid JSON. No markdown, no extra text.

# {{
#     "verdict": "PASS" | "WARN" | "FAIL",
#     "dimension_scores": {{
#         "reasoning_visibility":       <float 0.0-1.0>,
#         "source_traceability":        <float 0.0-1.0>,
#         "uncertainty_acknowledgment": <float 0.0-1.0>
#     }},
#     "explainability_score": <mean of three dimensions, float 0.0-1.0>,
#     "gaps": ["<specific transparency gap identified>"],
#     "reasoning": "<one paragraph explaining your verdict>"
# }}
# """
#         try:
#             response = self.llm.generate_content(
#                 judge_prompt,
#                 generation_config={
#                     "response_mime_type": "application/json",
#                     "temperature":        0.0,
#                 }
#             )
#             result  = json.loads(response.text)
#             verdict = result.get("verdict", "WARN")
#             if verdict not in ("PASS", "WARN", "FAIL"):
#                 verdict = "WARN"

#             explainability = max(0.0, min(1.0,
#                 float(result.get("explainability_score", 0.6))
#             ))
#             gaps = result.get("gaps", [])

#             return {
#                 "verdict":              verdict,
#                 "explainability_score": explainability,
#                 "dimension_scores":     result.get("dimension_scores", {}),
#                 "flags": [f"TRANSPARENCY_GAP: {g[:100]}" for g in gaps],
#                 "reasoning":            result.get("reasoning", ""),
#             }

#         except Exception as e:
#             print(f"⚠️  [Agent 2 / Explainability Judge] LLM call failed: {e}.")
#             return {
#                 "verdict":              "WARN",
#                 "explainability_score": 0.6,
#                 "dimension_scores":     {},
#                 "flags":                [f"JUDGE_ERROR: {str(e)[:80]}"],
#                 "reasoning":            f"Explainability judge failed ({e}).",
#             }

#     # ------------------------------------------------------------------
#     # COMBINE CHECKS → FINAL VERDICT
#     # ------------------------------------------------------------------

#     def _combine_checks(
#         self, check_a: dict, check_b: dict, check_c: dict
#     ) -> TransparencyVerdict:
#         a_score = float(check_a.get("citation_coverage",    0.0))
#         b_score = float(check_b.get("uncertainty_score",    0.6))
#         c_score = float(check_c.get("explainability_score", 0.6))

#         score              = a_score * 0.40 + b_score * 0.30 + c_score * 0.30
#         audit_completeness = (a_score + b_score + c_score) / 3.0

#         flags = (
#             check_a.get("flags", []) +
#             check_b.get("flags", []) +
#             check_c.get("flags", [])
#         )

#         c_verdict = check_c.get("verdict", "WARN")

#         if c_verdict == "FAIL" or score < 0.50:
#             final_verdict = "FAIL"
#         elif c_verdict == "WARN" or score < 0.75:
#             final_verdict = "WARN"
#         else:
#             final_verdict = "PASS"

#         reasoning = (
#             f"Source coverage: {a_score:.2f} "
#             f"({'none' if a_score == 0 else 'partial' if a_score < 1 else 'full'}). "
#             f"Uncertainty language: {b_score:.2f}. "
#             f"Explainability judge: {c_verdict} (score={c_score:.2f}). "
#             f"Composite score: {score:.3f}. "
#             f"Audit completeness: {audit_completeness:.3f}. "
#             f"Detail: {check_c.get('reasoning', 'N/A')}"
#         )

#         return TransparencyVerdict(
#             verdict              = final_verdict,
#             score                = score,
#             citation_coverage    = a_score,
#             uncertainty_score    = b_score,
#             explainability_score = c_score,
#             audit_completeness   = audit_completeness,
#             flags                = flags,
#             reasoning            = reasoning,
#         )

#     def _print_summary(self, v: TransparencyVerdict):
#         icons = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}
#         print(f"\n{icons.get(v.verdict,'?')} [Agent 2] VERDICT: {v.verdict}")
#         print(f"   Score                : {v.score:.3f}")
#         print(f"   Source coverage      : {v.citation_coverage:.3f}")
#         print(f"   Uncertainty score    : {v.uncertainty_score:.3f}")
#         print(f"   Explainability score : {v.explainability_score:.3f}")
#         print(f"   Audit completeness   : {v.audit_completeness:.3f}")
#         if v.flags:
#             print(f"   Flags                : {', '.join(v.flags[:3])}")
#         print(f"   Latency              : {v.latency_ms:.0f} ms")
#         print("=" * 60 + "\n")


# if __name__ == "__main__":
#     import os
#     import vertexai
#     from vertexai.generative_models import GenerativeModel

#     os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
#     vertexai.init(project="ornate-fragment-477923-t2", location="us-central1")
#     llm = GenerativeModel("gemini-2.5-flash")
#     agent = TransparencyAgent(llm_client=llm)

#     MOCK_CHUNKS = [
#         {"text": "Sagnik Ray Choudhury is the NLP instructor. "
#                  "Email: Sagnik.Raychoudhury@unt.edu",
#          "metadata": {"filepath": "NLP-Week1-sp-2026.pdf", "page": 6}},
#     ]

#     tests = [
#         ("TEST 1 RAG PASS", "Who is the NLP instructor?",
#          "The instructor is Sagnik Ray Choudhury [File: NLP-Week1-sp-2026.pdf, Page: 6.0]. "
#          "According to the syllabus, their email is Sagnik.Raychoudhury@unt.edu "
#          "[File: NLP-Week1-sp-2026.pdf, Page: 6.0].",
#          MOCK_CHUNKS),
#         ("TEST 2 RAG WARN", "Who is the NLP instructor?",
#          "The instructor is Sagnik Ray Choudhury and their email is "
#          "Sagnik.Raychoudhury@unt.edu [File: NLP-Week1-sp-2026.pdf, Page: 6.0].",
#          MOCK_CHUNKS),
#         ("TEST 3 General LLM PASS", "What is stress management?",
#          "Stress management involves techniques to control stress levels. "
#          "See https://en.wikipedia.org/wiki/Stress_management and "
#          "https://www.apa.org/topics/stress for more information.",
#          []),
#         ("TEST 4 General LLM WARN", "What is stress management?",
#          "Stress management is about controlling your stress. It involves "
#          "breathing exercises and time management.",
#          []),
#     ]

#     for label, q, draft, chunks in tests:
#         print("\n" + "=" * 70)
#         print(label)
#         print("=" * 70)
#         result = agent.verify(question=q, draft_answer=draft, context_chunks=chunks)
#         print(f"Verdict: {result.verdict} | Score: {result.score:.3f}")















"""
=============================================================================
ETHOS AI — TRUST ENFORCEMENT LAYER
Agent 2: Transparency & Explainability
=============================================================================

RESEARCH GROUNDING:
    - RAG citation pipelines; audit logs in enterprise guardrails:
        Li et al. (2025). "Retrieval-augmented generation for educational
        application: A systematic survey." Computers & Education: AI.
    - LLM-as-judge evaluation pattern:
        Zheng et al. (2023). "Judging LLM-as-a-Judge with MT-Bench
        and Chatbot Arena." NeurIPS 2023.
    - Transparency & Explainability row (Moderate Gap):
        Slide 14 framework — Tools: plan/trace logger, evidence highlighter.
        Policies: citation-required for claims; step logs for audit.

RUNS ON: ALL routes.
    RAG route:          checks [File: X, Page: Y] course citations.
    General LLM route:  checks web URLs as transparency signal.
    YouTube route:      checks web URLs as transparency signal.

SEVERITY: Soft WARN — FAIL annotates response, does not hard-block.
=============================================================================
"""

import re
import json
import time
from dataclasses import dataclass, field


@dataclass
class TransparencyVerdict:
    agent:                str   = "transparency"
    verdict:              str   = "PASS"
    score:                float = 1.0
    citation_coverage:    float = 1.0
    uncertainty_score:    float = 1.0
    explainability_score: float = 1.0
    audit_completeness:   float = 1.0
    flags:                list  = field(default_factory=list)
    reasoning:            str   = ""
    source:               str   = "Agent2_Transparency"
    latency_ms:           float = 0.0

    def to_dict(self) -> dict:
        def safe(v):
            try:
                f = float(v)
                return round(f, 3) if (f == f and abs(f) != float('inf')) else 0.0
            except Exception:
                return 0.0
        return {
            "agent":                self.agent,
            "verdict":              self.verdict,
            "score":                safe(self.score),
            "citation_coverage":    safe(self.citation_coverage),
            "uncertainty_score":    safe(self.uncertainty_score),
            "explainability_score": safe(self.explainability_score),
            "audit_completeness":   safe(self.audit_completeness),
            "flags":                self.flags,
            "reasoning":            self.reasoning,
            "source":               self.source,
            "latency_ms":           safe(self.latency_ms),
        }


class TransparencyAgent:
    """
    Agent 2 — Transparency & Explainability.

    Runs on ALL routes with mode-switching:
      - RAG mode (context_chunks non-empty):
            Check A counts [File: X, Page: Y] course citations.
            Check C evaluates source traceability against retrieved chunks.
      - General LLM / YouTube mode (context_chunks empty):
            Check A counts web URLs as transparency signals.
            Check C evaluates reasoning visibility and web source quality.
    """

    CITATION_PATTERN = re.compile(
        r'\[File:\s*.+?,\s*Page:\s*[\w\-/\.]+\]',
        re.IGNORECASE
    )

    WEB_URL_PATTERN = re.compile(
        r'https?://[^\s<>"\']+',
        re.IGNORECASE
    )

    # UNCERTAINTY_POSITIVE = [                                          # REMOVED — professor review
    #     r"\baccording to\b",
    #     r"\bbased on\b",
    #     r"\bthe (context|document|source|material|slide|textbook) (states?|says?|indicates?|shows?|suggests?)\b",
    #     r"\bas (stated|mentioned|described|outlined|explained) in\b",
    #     r"\bper the (provided|course|available) (context|material|document)\b",
    #     r"\bthe (provided|retrieved|available) context\b",
    #     r"\bi('m| am) not (certain|sure|confident)\b",
    #     r"\bthis may\b",
    #     r"\bthis might\b",
    #     r"\bit (appears?|seems?|suggests?)\b",
    #     r"\bpossibly\b",
    #     r"\blikely\b",
    # ]

    # UNCERTAINTY_NEGATIVE = [                                          # REMOVED — professor review
    #     r"\bit is (definitely|absolutely|certainly|always|never) (true|the case|correct)\b",
    #     r"\bthe (fact|truth) is\b",
    #     r"\bwithout (a )?doubt\b",
    #     r"\b(definitely|absolutely|certainly) (means?|shows?|proves?|demonstrates?)\b",
    # ]

    def __init__(self, llm_client):
        self.llm = llm_client
        # self._positive_regex = [                                      # REMOVED — professor review
        #     re.compile(p, re.IGNORECASE) for p in self.UNCERTAINTY_POSITIVE
        # ]
        # self._negative_regex = [                                      # REMOVED — professor review
        #     re.compile(p, re.IGNORECASE) for p in self.UNCERTAINTY_NEGATIVE
        # ]

    def verify(
        self,
        question:       str,
        draft_answer:   str,
        context_chunks: list,
    ) -> TransparencyVerdict:
        t0 = time.time()
        has_course_context = len(context_chunks) > 0
        mode = "RAG" if has_course_context else "General LLM"

        print("\n" + "=" * 60)
        print(f"🔍 [AGENT 2] Transparency & Explainability Check [{mode} mode]")
        print("=" * 60)

        if not draft_answer or not draft_answer.strip():
            return TransparencyVerdict(
                verdict    = "WARN",
                score      = 0.0,
                flags      = ["EMPTY_DRAFT"],
                reasoning  = "Draft answer was empty — cannot assess transparency.",
                latency_ms = (time.time() - t0) * 1000,
            )

        print("   → Check A: Source coverage (rule-based)...")
        check_a = self._check_source_coverage(draft_answer, has_course_context)

        # print("   → Check B: Uncertainty acknowledgment (rule-based)...")  # REMOVED — professor review
        # check_b = self._check_uncertainty_language(draft_answer)            # REMOVED — professor review

        print("   → Check C: Explainability & audit completeness (LLM)...")
        check_c = self._run_explainability_judge(
            question, draft_answer, context_chunks, has_course_context
        )

        verdict            = self._combine_checks(check_a, check_c)
        verdict.latency_ms = (time.time() - t0) * 1000

        self._print_summary(verdict)
        return verdict

    # ------------------------------------------------------------------
    # CHECK A — SOURCE COVERAGE (mode-switching, rule-based)
    # ------------------------------------------------------------------

    def _check_source_coverage(
        self, draft_answer: str, has_course_context: bool
    ) -> dict:
        if has_course_context:
            # RAG mode — course citations [File: X, Page: Y]
            matches = self.CITATION_PATTERN.findall(draft_answer)
            count   = len(matches)
            if count == 0:
                print(f"      ❌ No course citations found.")
                return {"citation_coverage": 0.0, "flags": ["NO_INLINE_CITATIONS"]}
            elif count == 1:
                print(f"      ⚠️  One citation found: {matches[0]}")
                return {"citation_coverage": 0.5, "flags": ["LOW_CITATION_COUNT"]}
            else:
                print(f"      ✅ {count} course citations found.")
                return {"citation_coverage": 1.0, "flags": []}
        else:
            # General LLM / YouTube mode — web URLs as transparency signal
            matches = self.WEB_URL_PATTERN.findall(draft_answer)
            count   = len(matches)
            if count == 0:
                print(f"      ❌ No web sources found.")
                return {"citation_coverage": 0.0, "flags": ["NO_WEB_SOURCES"]}
            elif count < 2:
                print(f"      ⚠️  Only {count} web source found.")
                return {"citation_coverage": 0.5, "flags": ["LOW_WEB_SOURCE_COUNT"]}
            else:
                print(f"      ✅ {count} web sources found.")
                return {"citation_coverage": 1.0, "flags": []}

    # ------------------------------------------------------------------
    # CHECK B — UNCERTAINTY ACKNOWLEDGMENT (rule-based)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # CHECK B — UNCERTAINTY ACKNOWLEDGMENT (REMOVED — professor review)
    # Uncertainty acknowledgment removed as a separate scoring component.
    # The concept is retained in future work / Agent 3 Knowledge Boundary.
    # ------------------------------------------------------------------

    # def _check_uncertainty_language(self, draft_answer: str) -> dict:
    #     positive_hits = sum(
    #         1 for p in self._positive_regex if p.search(draft_answer)
    #     )
    #     negative_hits = sum(
    #         1 for p in self._negative_regex if p.search(draft_answer)
    #     )
    #     flags = []
    #
    #     if positive_hits == 0 and negative_hits == 0:
    #         score = 0.6
    #         flags.append("NO_UNCERTAINTY_LANGUAGE")
    #         print(f"      ⚠️  No uncertainty language detected.")
    #     elif positive_hits > 0 and negative_hits == 0:
    #         score = 1.0
    #         print(f"      ✅ {positive_hits} epistemic markers found.")
    #     elif positive_hits > 0 and negative_hits > 0:
    #         score = 0.7
    #         flags.append("MIXED_UNCERTAINTY_SIGNALS")
    #         print(f"      ⚠️  Mixed signals: {positive_hits} positive, "
    #               f"{negative_hits} overconfident.")
    #     else:
    #         score = 0.3
    #         flags.append("OVERCONFIDENT_LANGUAGE")
    #         print(f"      ❌ Overconfident language without attribution.")
    #
    #     return {
    #         "uncertainty_score": score,
    #         "positive_hits":     positive_hits,
    #         "negative_hits":     negative_hits,
    #         "flags":             flags,
    #     }

    # ------------------------------------------------------------------
    # CHECK C — EXPLAINABILITY JUDGE (LLM, mode-switching)
    # ------------------------------------------------------------------

    def _run_explainability_judge(
        self,
        question:          str,
        draft_answer:      str,
        context_chunks:    list,
        has_course_context: bool,
    ) -> dict:
        if has_course_context:
            # RAG mode — evaluate against retrieved course chunks
            # context_preview = "\n---\n".join([
            #     f"[Chunk {i+1}] "
            #     f"{str(c.get('text', c.get('page_content', str(c))))[:600]}..."
            #     for i, c in enumerate(context_chunks[:5])
            # ])

            context_preview = "\n---\n".join([
                    f"[Chunk {i+1}] "
                    f"[File: {c.get('metadata', {}).get('filepath', c.get('metadata', {}).get('source', 'Unknown'))}, "
                    f"Page: {c.get('metadata', {}).get('page', 'N/A')}]\n"
                    f"{str(c.get('text', c.get('page_content', str(c))))[:600]}..."
                    for i, c in enumerate(context_chunks[:5])
                ]) if context_chunks else "No context chunks available."

            mode_note = (
                "NOTE: The factual accuracy of this response has already been "
                "independently verified by an NLI entailment judge (Agent 1). "
                "Do NOT re-evaluate factual accuracy. Your job is ONLY to evaluate "
                "transparency quality — citation formatting and reasoning visibility."
            )
            source_traceability_desc = (
                "Can a student or educator verify each factual claim by going to "
                "the cited [File: X, Page: Y] source? Are citations specific enough?"
            )
            context_section = f"RETRIEVED CONTEXT (first 5 chunks):\n{context_preview}"
        else:
            # General LLM mode — evaluate web source quality
            mode_note = (
                "This is a general knowledge response — no course materials were "
                "retrieved. Evaluate transparency based on web source quality, "
                "reasoning visibility, and appropriate acknowledgment that this "
                "is general knowledge rather than course-specific content."
            )
            source_traceability_desc = (
                "Does the response provide credible web sources (URLs) that the "
                "student can visit to verify the information? Are the sources "
                "reputable (e.g. academic, government, established organisations)?"
            )
            context_section = (
                "CONTEXT TYPE: General knowledge response — no course chunks retrieved.\n"
                "Evaluate based on web sources and reasoning quality only."
            )

        judge_prompt = f"""
You are a Transparency & Explainability Judge for an educational AI system.

{mode_note}

STUDENT QUESTION:
{question}

{context_section}

DRAFT RESPONSE (to audit):
{draft_answer}

EVALUATE on these two explainability dimensions (score 0.0–1.0 each):

1. REASONING_VISIBILITY (0.0=opaque, 1.0=fully transparent):
   Does the response show its reasoning — explaining WHY, not just WHAT?
   Does it connect claims to sources or evidence explicitly?

2. SOURCE_TRACEABILITY (0.0=untraceable, 1.0=fully traceable):
   {source_traceability_desc}

# 3. UNCERTAINTY_ACKNOWLEDGMENT — REMOVED (professor review)          # REMOVED
#    Does the response acknowledge its knowledge limits appropriately?  # REMOVED
#    Does it avoid presenting uncertain claims as established facts?     # REMOVED

VERDICT RULES:
- "PASS"  → all dimensions >= 0.75
- "WARN"  → any dimension between 0.50 and 0.74
- "FAIL"  → any dimension < 0.50

Respond ONLY with valid JSON. No markdown, no extra text.

{{
    "verdict": "PASS" | "WARN" | "FAIL",
    "dimension_scores": {{
        "reasoning_visibility":       <float 0.0-1.0>,
        "source_traceability":        <float 0.0-1.0>
    }},
    "explainability_score": <mean of two dimensions, float 0.0-1.0>,
    "gaps": ["<specific transparency gap identified>"],
    "reasoning": "<one paragraph explaining your verdict>"
}}
"""
        try:
            response = self.llm.generate_content(
                judge_prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature":        0.0,
                }
            )
            result  = json.loads(response.text)
            verdict = result.get("verdict", "WARN")
            if verdict not in ("PASS", "WARN", "FAIL"):
                verdict = "WARN"

            explainability = max(0.0, min(1.0,
                float(result.get("explainability_score", 0.6))
            ))
            gaps = result.get("gaps", [])

            return {
                "verdict":              verdict,
                "explainability_score": explainability,
                "dimension_scores":     result.get("dimension_scores", {}),
                "flags": [f"TRANSPARENCY_GAP: {g[:100]}" for g in gaps],
                "reasoning":            result.get("reasoning", ""),
            }

        except Exception as e:
            print(f"⚠️  [Agent 2 / Explainability Judge] LLM call failed: {e}.")
            return {
                "verdict":              "WARN",
                "explainability_score": 0.6,
                "dimension_scores":     {},
                "flags":                [f"JUDGE_ERROR: {str(e)[:80]}"],
                "reasoning":            f"Explainability judge failed ({e}).",
            }

    # ------------------------------------------------------------------
    # COMBINE CHECKS → FINAL VERDICT
    # ------------------------------------------------------------------

    def _combine_checks(
        self, check_a: dict, check_c: dict
    ) -> TransparencyVerdict:
        a_score = float(check_a.get("citation_coverage",    0.0))
        # b_score removed — uncertainty acknowledgment removed (professor review)
        c_score = float(check_c.get("explainability_score", 0.6))

        score              = a_score * 0.55 + c_score * 0.45
        audit_completeness = (a_score + c_score) / 2.0

        flags = (
            check_a.get("flags", []) +
            # check_b.get("flags", []) +                               # REMOVED
            check_c.get("flags", [])
        )

        c_verdict = check_c.get("verdict", "WARN")

        if c_verdict == "FAIL" or score < 0.50:
            final_verdict = "FAIL"
        elif c_verdict == "WARN" or score < 0.75:
            final_verdict = "WARN"
        else:
            final_verdict = "PASS"

        reasoning = (
            f"Source coverage: {a_score:.2f} "
            f"({'none' if a_score == 0 else 'partial' if a_score < 1 else 'full'}). "
            # f"Uncertainty language: {b_score:.2f}. "                 # REMOVED
            f"Explainability judge: {c_verdict} (score={c_score:.2f}). "
            f"Composite score: {score:.3f}. "
            f"Audit completeness: {audit_completeness:.3f}. "
            f"Detail: {check_c.get('reasoning', 'N/A')}"
        )

        return TransparencyVerdict(
            verdict              = final_verdict,
            score                = score,
            citation_coverage    = a_score,
            # uncertainty_score  = b_score,                            # REMOVED
            explainability_score = c_score,
            audit_completeness   = audit_completeness,
            flags                = flags,
            reasoning            = reasoning,
        )

    def _print_summary(self, v: TransparencyVerdict):
        icons = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}
        print(f"\n{icons.get(v.verdict,'?')} [Agent 2] VERDICT: {v.verdict}")
        print(f"   Score                : {v.score:.3f}")
        print(f"   Source coverage      : {v.citation_coverage:.3f}")
        # print(f"   Uncertainty score    : {v.uncertainty_score:.3f}")  # REMOVED
        print(f"   Explainability score : {v.explainability_score:.3f}")
        print(f"   Audit completeness   : {v.audit_completeness:.3f}")
        if v.flags:
            print(f"   Flags                : {', '.join(v.flags[:3])}")
        print(f"   Latency              : {v.latency_ms:.0f} ms")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    import os
    import vertexai
    from vertexai.generative_models import GenerativeModel

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
    vertexai.init(project="ornate-fragment-477923-t2", location="us-central1")
    llm = GenerativeModel("gemini-2.5-flash")
    agent = TransparencyAgent(llm_client=llm)

    MOCK_CHUNKS = [
        {"text": "Sagnik Ray Choudhury is the NLP instructor. "
                 "Email: Sagnik.Raychoudhury@unt.edu",
         "metadata": {"filepath": "NLP-Week1-sp-2026.pdf", "page": 6}},
    ]

    tests = [
        ("TEST 1 RAG PASS", "Who is the NLP instructor?",
         "The instructor is Sagnik Ray Choudhury [File: NLP-Week1-sp-2026.pdf, Page: 6.0]. "
         "According to the syllabus, their email is Sagnik.Raychoudhury@unt.edu "
         "[File: NLP-Week1-sp-2026.pdf, Page: 6.0].",
         MOCK_CHUNKS),
        ("TEST 2 RAG WARN", "Who is the NLP instructor?",
         "The instructor is Sagnik Ray Choudhury and their email is "
         "Sagnik.Raychoudhury@unt.edu [File: NLP-Week1-sp-2026.pdf, Page: 6.0].",
         MOCK_CHUNKS),
        ("TEST 3 General LLM PASS", "What is stress management?",
         "Stress management involves techniques to control stress levels. "
         "See https://en.wikipedia.org/wiki/Stress_management and "
         "https://www.apa.org/topics/stress for more information.",
         []),
        ("TEST 4 General LLM WARN", "What is stress management?",
         "Stress management is about controlling your stress. It involves "
         "breathing exercises and time management.",
         []),
    ]

    for label, q, draft, chunks in tests:
        print("\n" + "=" * 70)
        print(label)
        print("=" * 70)
        result = agent.verify(question=q, draft_answer=draft, context_chunks=chunks)
        print(f"Verdict: {result.verdict} | Score: {result.score:.3f}")