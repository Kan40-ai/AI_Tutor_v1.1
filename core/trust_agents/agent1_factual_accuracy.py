"""
=============================================================================
ETHOS AI — TRUST ENFORCEMENT LAYER
Agent 1: Factual Accuracy & Hallucination Detection
=============================================================================

RESEARCH GROUNDING:
    - NLI-as-judge pattern:
        Zheng et al. (2023). "Judging LLM-as-a-Judge with MT-Bench
        and Chatbot Arena." NeurIPS 2023.
    - Factual grounding in educational RAG:
        Li et al. (2025). "Retrieval-augmented generation for educational
        application: A systematic survey." Computers & Education: AI.
    - Evaluation framework baseline:
        Es et al. (2023). "RAGAS: Automated Evaluation of Retrieval
        Augmented Generation." arXiv:2309.15217.

ROLE IN ARCHITECTURE:
    Layer III — Trust Enforcement Layer (parallel agent panel)
    Severity tier: SOFT WARN
        FAIL  → response delivered WITH uncertainty disclaimer + audit log
        WARN  → response delivered with mild caveat + audit log
        PASS  → response delivered as-is

WHAT THIS AGENT CHECKS:
    Check A — NLI Entailment Judge (LLM call, weight 0.70)
        Is every factual claim in the draft grounded in the retrieved
        context chunks? Detects hallucination and outside-knowledge leakage.

    Check B — Citation Coverage (rule-based, no LLM call, weight 0.30)
        Does the draft use [File: X, Page: Y] citations that
        tutor_service.py's draft_prompt requires?

OUTPUT CONTRACT (dict consumed by trust_aggregator.py):
    {
        "agent":              "factual_accuracy",
        "verdict":            "PASS" | "WARN" | "FAIL",
        "score":              float 0.0-1.0,
        "hallucination_rate": float 0.0-1.0,
        "citation_coverage":  float 0.0-1.0,
        "flags":              list[str],
        "reasoning":          str,
        "source":             "Agent1_FactualAccuracy",
        "latency_ms":         float
    }

FILE LOCATION:
    core/trust_agents/agent1_factual_accuracy.py

IMPORT IN tutor_service.py:
    from core.trust_agents.agent1_factual_accuracy import FactualAccuracyAgent
=============================================================================
"""

import json
import re
import time
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# OUTPUT DATA CONTRACT
# ---------------------------------------------------------------------------

@dataclass
class FactualVerdict:
    """
    Structured output from Agent 1.
    Call .to_dict() before passing to the trust aggregator.
    """
    agent:              str   = "factual_accuracy"
    verdict:            str   = "PASS"
    score:              float = 1.0
    hallucination_rate: float = 0.0
    citation_coverage:  float = 1.0
    flags:              list  = field(default_factory=list)
    reasoning:          str   = ""
    source:             str   = "Agent1_FactualAccuracy"
    latency_ms:         float = 0.0

    def to_dict(self) -> dict:
        return {
            "agent":              self.agent,
            "verdict":            self.verdict,
            "score":              round(self.score, 3),
            "hallucination_rate": round(self.hallucination_rate, 3),
            "citation_coverage":  round(self.citation_coverage, 3),
            "flags":              self.flags,
            "reasoning":          self.reasoning,
            "source":             self.source,
            "latency_ms":         round(self.latency_ms, 1),
        }


# ---------------------------------------------------------------------------
# AGENT CLASS
# ---------------------------------------------------------------------------

class FactualAccuracyAgent:
    """
    Agent 1 — Factual Accuracy & Hallucination Detection.

    Runs two independent checks on every RAG draft before delivery.
    Designed to execute in parallel with Agents 2-6 via asyncio.gather()
    in the trust aggregator.

    Usage in tutor_service.py:
        verdict = self.agent1.verify(question, draft_answer, refined_chunks)
        result  = verdict.to_dict()
    """

    # Matches [File: NLP-Week1-sp-2026.pdf, Page: 4]
    CITATION_PATTERN = re.compile(
        r'\[File:\s*.+?,\s*Page:\s*[\w\-/]+\]',
        re.IGNORECASE
    )

    CITATION_PATTERN = re.compile(
    r'\[File:\s*.+?,\s*Page:\s*[\w\-/\.]+\]',
    re.IGNORECASE
)

    ESCAPE_HATCH_TOKEN = "INSUFFICIENT_CONTEXT"

    def __init__(self, llm_client):
        """
        Args:
            llm_client: Gemini GenerativeModel instance from TutorService.
                        Pass: self.tutor_engine.llm
        """
        self.llm = llm_client

    # ------------------------------------------------------------------
    # PUBLIC INTERFACE
    # ------------------------------------------------------------------

    def verify(
        self,
        question:       str,
        draft_answer:   str,
        context_chunks: list,
    ) -> FactualVerdict:
        """
        Main entry point. Call after draft generation, before returning
        the response to the student.

        Args:
            question:        Original student question.
            draft_answer:    Raw text from the draft_prompt LLM call.
            context_chunks:  Reranked chunk dicts from tutor_service._rerank().
                             Each must have: {'metadata': {'text', 'filepath', 'page'}}

        Returns:
            FactualVerdict
        """
        t0 = time.time()

        print("\n" + "=" * 60)
        print("🔍 [AGENT 1] Factual Accuracy & Hallucination Check")
        print("=" * 60)

        # Edge case: escape hatch fired correctly
        if self.ESCAPE_HATCH_TOKEN in draft_answer:
            print("✅ [Agent 1] Escape hatch detected — correct refusal, "
                  "skipping verification.")
            return FactualVerdict(
                verdict           = "PASS",
                score             = 1.0,
                hallucination_rate= 0.0,
                citation_coverage = 1.0,
                reasoning         = "Draft correctly triggered INSUFFICIENT_CONTEXT "
                                    "escape hatch rather than hallucinating.",
                latency_ms        = (time.time() - t0) * 1000,
            )

        # Edge case: empty draft
        if not draft_answer or not draft_answer.strip():
            print("❌ [Agent 1] Empty draft — returning FAIL.")
            return FactualVerdict(
                verdict           = "FAIL",
                score             = 0.0,
                hallucination_rate= 1.0,
                citation_coverage = 0.0,
                flags             = ["EMPTY_DRAFT"],
                reasoning         = "Draft answer was empty or whitespace only.",
                latency_ms        = (time.time() - t0) * 1000,
            )

        # Edge case: no context chunks passed
        if not context_chunks:
            print("⚠️  [Agent 1] No context chunks — cannot verify.")
            return FactualVerdict(
                verdict           = "WARN",
                score             = 0.5,
                hallucination_rate= 0.5,
                citation_coverage = 0.0,
                flags             = ["NO_CONTEXT_PROVIDED"],
                reasoning         = "Factual verification skipped — no retrieved "
                                    "context chunks were supplied to the agent.",
                latency_ms        = (time.time() - t0) * 1000,
            )

        context_str = self._build_context_string(context_chunks)

        print("   → Check A: NLI Entailment Judge (LLM)...")
        check_a = self._run_nli_judge(question, draft_answer, context_str)

        print("   → Check B: Citation Coverage (rule-based)...")
        check_b = self._check_citation_coverage(draft_answer)

        verdict            = self._combine_checks(check_a, check_b)
        verdict.latency_ms = (time.time() - t0) * 1000

        self._print_summary(verdict)
        return verdict

    # ------------------------------------------------------------------
    # CHECK A — NLI ENTAILMENT JUDGE
    # ------------------------------------------------------------------

    def _run_nli_judge(
        self,
        question:     str,
        draft_answer: str,
        context_str:  str,
    ) -> dict:
        """
        LLM-as-judge: verifies every claim in the draft is entailed
        by the retrieved context.
        """
        judge_prompt = f"""
You are a strict NLI (Natural Language Inference) Entailment Judge for an
educational AI system. Your ONLY job is to verify whether the DRAFT ANSWER
is fully supported by the RETRIEVED CONTEXT.

DEFINITIONS:
- ENTAILED: A claim explicitly stated or directly inferable from the context.
  No outside knowledge permitted.
- HALLUCINATED: A claim that goes beyond, contradicts, or cannot be confirmed
  by the context — even if factually correct in the real world.

RETRIEVED CONTEXT (ground truth):
{context_str}

STUDENT QUESTION:
{question}

DRAFT ANSWER (to verify):
{draft_answer}

EVALUATION STEPS:
1. Identify each distinct factual claim in the DRAFT ANSWER.
2. Classify each as ENTAILED or HALLUCINATED against the context only.
3. Compute hallucination_rate = hallucinated_claims / total_claims.
4. Quote verbatim any hallucinated or ungrounded statements.

VERDICT RULES:
- "PASS" → hallucination_rate == 0.0
- "WARN" → 0.0 < hallucination_rate <= 0.25
- "FAIL" → hallucination_rate > 0.25

Respond ONLY with valid JSON. No markdown, no extra text.

{{
    "verdict": "PASS" | "WARN" | "FAIL",
    "hallucination_rate": <float 0.0-1.0>,
    "ungrounded_claims": ["<exact quote from draft not in context>"],
    "reasoning": "<one paragraph explaining your verdict>"
}}
"""
        try:
            response = self.llm.generate_content(
                judge_prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            result = json.loads(response.text)

            verdict = result.get("verdict", "WARN")
            if verdict not in ("PASS", "WARN", "FAIL"):
                verdict = "WARN"

            rate = float(result.get("hallucination_rate", 0.5))
            rate = max(0.0, min(1.0, rate))

            return {
                "verdict":            verdict,
                "hallucination_rate": rate,
                "ungrounded_claims":  result.get("ungrounded_claims", []),
                "reasoning":          result.get("reasoning", ""),
            }

        except Exception as e:
            print(f"⚠️  [Agent 1 / NLI Judge] LLM call failed: {e}. "
                  "Defaulting to WARN.")
            return {
                "verdict":            "WARN",
                "hallucination_rate": 0.5,
                "ungrounded_claims":  [],
                "reasoning":          f"NLI judge LLM call failed ({e}).",
            }

    # ------------------------------------------------------------------
    # CHECK B — CITATION COVERAGE (RULE-BASED)
    # ------------------------------------------------------------------

    def _check_citation_coverage(self, draft_answer: str) -> dict:
        """
        Counts [File: ..., Page: ...] citations. Zero = transparency failure.
        """
        found = self.CITATION_PATTERN.findall(draft_answer)
        count = len(found)
        flags = []

        if count == 0:
            coverage = 0.0
            flags.append("NO_INLINE_CITATIONS")
            print(f"      0 citations found — flagging NO_INLINE_CITATIONS.")
        elif count == 1:
            coverage = 0.5
            flags.append("LOW_CITATION_COUNT")
            print(f"      1 citation found — partial coverage.")
        else:
            coverage = 1.0
            print(f"      {count} citations found — good coverage.")

        return {
            "citation_count":    count,
            "citation_coverage": coverage,
            "flags":             flags,
        }

    # ------------------------------------------------------------------
    # COMBINE CHECKS → FINAL VERDICT
    # ------------------------------------------------------------------

    def _combine_checks(self, check_a: dict, check_b: dict) -> FactualVerdict:
        """
        NLI weight: 0.70 | Citation weight: 0.30

        Hard override rules:
          - NLI FAIL always → FAIL regardless of citations
          - citation == 0.0 AND NLI PASS → WARN (transparency issue)
        """
        nli_verdict        = check_a["verdict"]
        hallucination_rate = check_a["hallucination_rate"]
        citation_coverage  = check_b["citation_coverage"]

        # score = (1.0 - hallucination_rate) * 0.70 + citation_coverage * 0.30

        if hallucination_rate == 0.0:
            score = 0.80 + (citation_coverage * 0.20)
        else:
            score = (1.0 - hallucination_rate) * 0.85 + citation_coverage * 0.15

        flags = list(check_b["flags"])
        for claim in check_a.get("ungrounded_claims", []):
            flags.append(f"UNGROUNDED: {claim[:120]}")

        if nli_verdict == "FAIL":
            final_verdict = "FAIL"
        elif citation_coverage == 0.0 and nli_verdict == "PASS":
            final_verdict = "WARN"
            flags.append("PASS_BUT_NO_CITATIONS")
        elif nli_verdict == "WARN" or citation_coverage < 1.0:
            final_verdict = "WARN"
        else:
            final_verdict = "PASS"

        reasoning = (
            f"NLI Judge: {nli_verdict} (hallucination_rate={hallucination_rate:.2f}). "
            f"Citation coverage: {citation_coverage:.1f}. "
            f"Composite score: {score:.3f}. "
            f"Detail: {check_a.get('reasoning', 'N/A')}"
        )

        return FactualVerdict(
            verdict           = final_verdict,
            score             = score,
            hallucination_rate= hallucination_rate,
            citation_coverage = citation_coverage,
            flags             = flags,
            reasoning         = reasoning,
        )

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _build_context_string(self, context_chunks: list) -> str:
        """
        Mirrors the format used in tutor_service.py's draft_prompt
        so the NLI judge sees exactly what the generator saw.
        """
        blocks = []
        for i, chunk in enumerate(context_chunks, 1):
            meta     = chunk.get("metadata", {})
            course   = meta.get("course_id", "Unknown")
            filepath = meta.get("filepath", meta.get("source", "Unknown"))
            page     = meta.get("page", "N/A")
            text     = meta.get("text", "")
            blocks.append(
                f"SOURCE {i} [Course: {course}, File: {filepath}, "
                f"Page: {page}]:\n{text}"
            )
        return "\n\n---\n\n".join(blocks)

    def _print_summary(self, v: FactualVerdict):
        icons = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}
        print(f"\n{icons.get(v.verdict, '?')} [Agent 1] VERDICT: {v.verdict}")
        print(f"   Score              : {v.score:.3f}")
        print(f"   Hallucination rate : {v.hallucination_rate:.3f}")
        print(f"   Citation coverage  : {v.citation_coverage:.3f}")
        if v.flags:
            print(f"   Flags              : {', '.join(v.flags)}")
        print(f"   Latency            : {v.latency_ms:.0f} ms")
        print("=" * 60 + "\n")


# =============================================================================
# STANDALONE TEST
# Run: python core/trust_agents/agent1_factual_accuracy.py
# =============================================================================

if __name__ == "__main__":
    import os
    import vertexai
    from vertexai.generative_models import GenerativeModel

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
    vertexai.init(project="ornate-fragment-477923-t2", location="global")
    llm = GenerativeModel("gemini-2.5-flash")

    agent = FactualAccuracyAgent(llm_client=llm)

    MOCK_CHUNKS = [{
        "metadata": {
            "course_id": "CSCE_5290_NLP",
            "filepath":  "NLP-Week2-sp-2026.pdf",
            "page":      4,
            "text": (
                "The Bigram Markov Assumption states that the probability "
                "of a word depends only on the immediately preceding word. "
                "This simplifies N-gram language models significantly."
            ),
        }
    }]

    tests = [
        ("TEST 1: Happy path — grounded + cited",
         "What is the Bigram Markov Assumption?",
         "The Bigram Markov Assumption states that the probability of a word "
         "depends only on the immediately preceding word. "
         "[File: NLP-Week2-sp-2026.pdf, Page: 4] "
         "This simplifies N-gram modelling significantly."),

        ("TEST 2: Hallucination trap — invented facts",
         "Who invented the Bigram Markov Assumption?",
         "The Bigram Markov Assumption was invented by Claude Shannon in 1948 "
         "in his paper A Mathematical Theory of Communication. "
         "[File: NLP-Week2-sp-2026.pdf, Page: 4]"),

        ("TEST 3: Escape hatch — should auto-PASS",
         "What year was Markov born?",
         "INSUFFICIENT_CONTEXT"),

        ("TEST 4: Grounded but no citations — expect WARN",
         "What is the Bigram Markov Assumption?",
         "The Bigram Markov Assumption states that each word depends only on "
         "the previous word. This reduces complexity in N-gram models."),
    ]

    for label, q, draft in tests:
        print("\n" + "=" * 70)
        print(label)
        print("=" * 70)
        result = agent.verify(
            question       = q,
            draft_answer   = draft,
            context_chunks = MOCK_CHUNKS,
        )
        print(json.dumps(result.to_dict(), indent=2))