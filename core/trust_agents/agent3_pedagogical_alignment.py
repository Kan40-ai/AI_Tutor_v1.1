"""
=============================================================================
ETHOS AI — TRUST ENFORCEMENT LAYER
Agent 3: Pedagogical Alignment
=============================================================================

RESEARCH GROUNDING:
    - Learner-aware prompt templates, syllabus-guided generation,
      adaptive feedback loops, scaffolding concepts:
        Liu et al. (2025). "LPITutor: An LLM-based personalized intelligent
        tutoring system using RAG and prompt engineering."
        PeerJ Computer Science, vol. 11, p. e2991.
        doi: 10.7717/peerj-cs.2991.
    - LLM-as-judge evaluation pattern:
        Zheng et al. (2023). "Judging LLM-as-a-Judge with MT-Bench
        and Chatbot Arena." NeurIPS 2023.
    - Pedagogical Alignment row (High Gap):
        Slide 14 framework — metrics: clarity, completeness, difficulty
        alignment, coherence, relevance, BLEU/ROUGE vs syllabus.

WHAT THIS AGENT CHECKS:
    Check A — Difficulty Alignment (rule-based, weight 0.35)
        Lexical density proxy — average word length and sentence length
        cross-checked against the persona_level from governance_profile.
        Four tiers: Elementary / Mid-High School / Undergraduate / Professional.
        Note: deliberately overlaps with Agent 4 Check C — Agent 4 uses
        difficulty as a bias signal (identity vs mastery). Agent 3 uses it
        as a pedagogical quality signal (is the student being served well?).

    Check B — Pedagogical Quality Judge (LLM call, weight 0.50)
        Evaluates: clarity, completeness, coherence, relevance.
        Does the response actually teach, or just state facts?
        Does it scaffold understanding for the detected persona level?
        Does it use appropriate examples and structure?

    Check C — Syllabus Alignment (rule-based, weight 0.15)
        For RAG responses: verifies the response stays on-topic for the
        detected course route (COURSE_NLP / COURSE_ML).
        For General LLM: always passes (no syllabus constraint applies).

SEVERITY: Advisory LOG only.
    FAIL  → response delivered untouched, pedagogical drift event logged.
    WARN  → response delivered untouched, logged for longitudinal analysis.
    PASS  → response delivered untouched.
    No student-facing annotation. No blocking.
    Research purpose: longitudinal pedagogical drift tracking for EduTrust-Eval.

OUTPUT CONTRACT (dict consumed by trust_aggregator.py):
    {
        "agent":                   "pedagogical_alignment",
        "verdict":                 "PASS" | "WARN" | "FAIL",
        "score":                   float 0.0-1.0,
        "difficulty_alignment":    float 0.0-1.0,
        "pedagogical_quality":     float 0.0-1.0,
        "syllabus_alignment":      float 0.0-1.0,
        "persona_match_score":     float 0.0-1.0,
        "flags":                   list[str],
        "reasoning":               str,
        "source":                  "Agent3_PedagogicalAlignment",
        "latency_ms":              float
    }

FILE LOCATION:
    core/trust_agents/agent3_pedagogical_alignment.py

RUNS ON: ALL routes (RAG + GENERAL_ASSISTANCE + YOUTUBE)
=============================================================================
"""

import re
import json
import time
from dataclasses import dataclass, field


@dataclass
class PedagogicalVerdict:
    agent:                str   = "pedagogical_alignment"
    verdict:              str   = "PASS"
    score:                float = 1.0
    difficulty_alignment: float = 1.0
    pedagogical_quality:  float = 1.0
    syllabus_alignment:   float = 1.0
    persona_match_score:  float = 1.0
    flags:                list  = field(default_factory=list)
    reasoning:            str   = ""
    source:               str   = "Agent3_PedagogicalAlignment"
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
            "difficulty_alignment": safe(self.difficulty_alignment),
            "pedagogical_quality":  safe(self.pedagogical_quality),
            "syllabus_alignment":   safe(self.syllabus_alignment),
            "persona_match_score":  safe(self.persona_match_score),
            "flags":                self.flags,
            "reasoning":            self.reasoning,
            "source":               self.source,
            "latency_ms":           safe(self.latency_ms),
        }


class PedagogicalAlignmentAgent:
    """
    Agent 3 — Pedagogical Alignment.

    Severity: Advisory LOG only.
    Response is always delivered untouched regardless of verdict.
    FAIL/WARN events are logged as pedagogical drift events for
    longitudinal analysis in the EduTrust-Eval evaluation pipeline.

    Three-check design:
        Check A: Difficulty alignment (rule-based, no LLM)
        Check B: Pedagogical quality judge (LLM call)
        Check C: Syllabus alignment (rule-based, no LLM)
    """

    # Expected readability ranges per persona tier
    PERSONA_BANDS = {
        "Elementary Learner": {
            "word_len": (3.5, 5.0),
            "sent_len": (6, 14),
        },
        "Mid/High School Student": {
            "word_len": (4.5, 6.0),
            "sent_len": (10, 20),
        },
        "Undergraduate Student": {
            "word_len": (5.0, 7.5),
            "sent_len": (12, 28),
        },
        "Professional / Academic": {
            "word_len": (6.0, 9.0),
            "sent_len": (15, 40),
        },
    }

    # Syllabus keywords per course route
    COURSE_KEYWORDS = {
        "COURSE_NLP": [
            "nlp", "natural language", "tokeniz", "n-gram", "bigram", "trigram",
            "language model", "text classif", "sentiment", "named entity",
            "part of speech", "parsing", "embedding", "transformer", "attention",
            "word2vec", "bert", "corpus", "vocabulary", "perplexity", "smoothing",
            "naive bayes", "logistic regression", "neural", "sequence",
        ],
        "COURSE_ML": [
            "machine learning", "neural network", "deep learning", "regression",
            "classification", "clustering", "gradient", "backpropagation",
            "supervised", "unsupervised", "reinforcement", "feature", "model",
            "training", "validation", "overfitting", "regularization", "loss",
            "accuracy", "precision", "recall", "f1", "cross-validation",
        ],
    }

    def __init__(self, llm_client):
        self.llm = llm_client

    def verify(
        self,
        question:          str,
        draft_answer:      str,
        governance_profile: dict,
        intent_route:      str = "GENERAL_ASSISTANCE",
    ) -> PedagogicalVerdict:
        """
        Main entry point. Runs on ALL routes.

        Args:
            question:           Original student query.
            draft_answer:       Raw LLM draft from tutor_service.
            governance_profile: Resolved profile from Layer I governance.
            intent_route:       Routing decision (COURSE_NLP, COURSE_ML,
                                GENERAL_ASSISTANCE, YOUTUBE_SEARCH).
        Returns:
            PedagogicalVerdict
        """
        t0 = time.time()

        print("\n" + "=" * 60)
        print("📚 [AGENT 3] Pedagogical Alignment Check")
        print("=" * 60)

        if not draft_answer or not draft_answer.strip():
            return PedagogicalVerdict(
                verdict    = "WARN",
                score      = 0.0,
                flags      = ["EMPTY_DRAFT"],
                reasoning  = "Draft answer was empty — cannot assess pedagogy.",
                latency_ms = (time.time() - t0) * 1000,
            )

        persona_level = governance_profile.get(
            "persona_level", "Undergraduate Student"
        )
        print(f"   Persona: {persona_level} | Route: {intent_route}")

        # ── Check A: Difficulty alignment ─────────────────────────────────
        print("   → Check A: Difficulty alignment (rule-based)...")
        check_a = self._check_difficulty_alignment(draft_answer, persona_level)

        # ── Check B: Pedagogical quality judge ────────────────────────────
        print("   → Check B: Pedagogical quality judge (LLM)...")
        check_b = self._run_pedagogical_judge(
            question, draft_answer, persona_level
        )

        # ── Check C: Syllabus alignment ───────────────────────────────────
        print("   → Check C: Syllabus alignment (rule-based)...")
        check_c = self._check_syllabus_alignment(
            draft_answer, intent_route
        )

        verdict            = self._combine_checks(check_a, check_b, check_c, persona_level)
        verdict.latency_ms = (time.time() - t0) * 1000

        self._print_summary(verdict)
        return verdict

    # ------------------------------------------------------------------
    # CHECK A — DIFFICULTY ALIGNMENT (rule-based)
    # ------------------------------------------------------------------

    def _check_difficulty_alignment(
        self, draft_answer: str, persona_level: str
    ) -> dict:
        """
        Lexical density proxy — average word length and sentence length
        cross-checked against persona tier bands.
        """
        words     = draft_answer.split()
        sentences = [s.strip() for s in re.split(r'[.!?]+', draft_answer) if s.strip()]

        if not words or not sentences:
            return {
                "difficulty_alignment": 0.5,
                "avg_word_len": 0,
                "avg_sent_len": 0,
                "flags": ["CANNOT_COMPUTE_DIFFICULTY"],
            }

        avg_word_len = sum(
            len(w.strip('.,!?;:()[]')) for w in words
        ) / len(words)
        avg_sent_len = sum(len(s.split()) for s in sentences) / len(sentences)

        band   = self.PERSONA_BANDS.get(
            persona_level, self.PERSONA_BANDS["Undergraduate Student"]
        )
        w_lo, w_hi = band["word_len"]
        s_lo, s_hi = band["sent_len"]

        flags      = []
        alignment  = 1.0

        if avg_word_len < w_lo - 1.0:
            flags.append(
                f"TOO_SIMPLE: avg word length {avg_word_len:.1f} "
                f"below {w_lo} for {persona_level}"
            )
            alignment -= 0.35
        elif avg_word_len > w_hi + 1.5:
            flags.append(
                f"TOO_COMPLEX: avg word length {avg_word_len:.1f} "
                f"above {w_hi} for {persona_level}"
            )
            alignment -= 0.25

        if avg_sent_len < s_lo - 3:
            flags.append(
                f"SENTENCES_TOO_SHORT: avg {avg_sent_len:.1f} words "
                f"below {s_lo} for {persona_level}"
            )
            alignment -= 0.15
        elif avg_sent_len > s_hi + 5:
            flags.append(
                f"SENTENCES_TOO_LONG: avg {avg_sent_len:.1f} words "
                f"above {s_hi} for {persona_level}"
            )
            alignment -= 0.10

        alignment = max(0.0, min(1.0, alignment))

        if flags:
            print(f"      ⚠️  Difficulty flags: {flags}")
        else:
            print(f"      ✅ word_len={avg_word_len:.1f}, "
                  f"sent_len={avg_sent_len:.1f} — within band for {persona_level}")

        return {
            "difficulty_alignment": alignment,
            "avg_word_len":         avg_word_len,
            "avg_sent_len":         avg_sent_len,
            "flags":                flags,
        }

    # ------------------------------------------------------------------
    # CHECK B — PEDAGOGICAL QUALITY JUDGE (LLM)
    # ------------------------------------------------------------------

    def _run_pedagogical_judge(
        self,
        question:     str,
        draft_answer: str,
        persona_level: str,
    ) -> dict:
        """
        LLM-as-judge evaluating pedagogical quality across four dimensions:
        clarity, completeness, coherence, and relevance.
        """
        judge_prompt = f"""
You are a Pedagogical Quality Judge for an educational AI tutoring system.

The student is classified as: {persona_level}

Your job: evaluate whether the DRAFT RESPONSE effectively teaches the student
and is appropriately calibrated for their cognitive level.

STUDENT QUESTION:
{question}

DRAFT RESPONSE (to audit):
{draft_answer}

EVALUATE on these four pedagogical dimensions (score 0.0–1.0 each):

1. CLARITY (0.0=confusing, 1.0=crystal clear):
   Is the response easy to understand for a {persona_level}?
   Are technical terms explained before use?
   Is the language appropriate for the cognitive level?

2. COMPLETENESS (0.0=incomplete, 1.0=fully complete):
   Does the response fully answer the student's question?
   Are all key aspects addressed?
   Does it leave the student with actionable understanding?

3. COHERENCE (0.0=disjointed, 1.0=well-structured):
   Is the response logically structured and easy to follow?
   Does it build understanding progressively?
   Is there a clear flow from introduction to conclusion?

4. RELEVANCE (0.0=off-topic, 1.0=fully relevant):
   Does the response directly address what the student asked?
   Does it stay focused without unnecessary tangents?
   Is every part of the response useful to the student?

VERDICT RULES:
- "PASS"  → all dimensions >= 0.75
- "WARN"  → any dimension between 0.55 and 0.74
- "FAIL"  → any dimension < 0.55

NOTE: This is an advisory check only. Verdict does not block the response.
Focus on whether the student is genuinely served pedagogically.

Respond ONLY with valid JSON. No markdown.

{{
    "verdict": "PASS" | "WARN" | "FAIL",
    "dimension_scores": {{
        "clarity":      <float 0.0-1.0>,
        "completeness": <float 0.0-1.0>,
        "coherence":    <float 0.0-1.0>,
        "relevance":    <float 0.0-1.0>
    }},
    "pedagogical_quality": <mean of four dimensions, float 0.0-1.0>,
    "improvement_notes": ["<specific improvement suggestion>"],
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
            verdict = result.get("verdict", "PASS")
            if verdict not in ("PASS", "WARN", "FAIL"):
                verdict = "PASS"

            quality = max(0.0, min(1.0,
                float(result.get("pedagogical_quality", 0.8))
            ))
            notes = result.get("improvement_notes", [])

            return {
                "verdict":            verdict,
                "pedagogical_quality": quality,
                "dimension_scores":   result.get("dimension_scores", {}),
                "flags": [f"PEDAGOGY_GAP: {n[:100]}" for n in notes],
                "reasoning":          result.get("reasoning", ""),
            }

        except Exception as e:
            print(f"⚠️  [Agent 3 / Pedagogical Judge] LLM call failed: {e}.")
            return {
                "verdict":             "WARN",
                "pedagogical_quality": 0.7,
                "dimension_scores":    {},
                "flags":               [f"JUDGE_ERROR: {str(e)[:80]}"],
                "reasoning":           f"Pedagogical judge failed ({e}).",
            }

    # ------------------------------------------------------------------
    # CHECK C — SYLLABUS ALIGNMENT (rule-based)
    # ------------------------------------------------------------------

    def _check_syllabus_alignment(
        self, draft_answer: str, intent_route: str
    ) -> dict:
        """
        For course routes (COURSE_NLP / COURSE_ML): verifies the response
        uses domain-appropriate vocabulary.
        For other routes: always passes — no syllabus constraint applies.
        """
        if intent_route not in ("COURSE_NLP", "COURSE_ML"):
            print(f"      ✅ Non-course route — syllabus check N/A.")
            return {
                "syllabus_alignment": 1.0,
                "flags": [],
                "reasoning": f"Route is {intent_route} — no syllabus constraint.",
            }

        keywords    = self.COURSE_KEYWORDS.get(intent_route, [])
        answer_low  = draft_answer.lower()
        hits        = sum(1 for kw in keywords if kw in answer_low)
        coverage    = min(hits / max(len(keywords) * 0.15, 1), 1.0)

        flags = []
        if coverage < 0.3:
            flags.append(
                f"LOW_SYLLABUS_COVERAGE: only {hits} domain keywords "
                f"detected for {intent_route}"
            )
            print(f"      ⚠️  Low syllabus coverage: {hits} keywords.")
        else:
            print(f"      ✅ {hits} domain keywords detected — good coverage.")

        return {
            "syllabus_alignment": coverage,
            "keyword_hits":       hits,
            "flags":              flags,
            "reasoning": (
                f"{hits} domain-specific keywords detected for "
                f"{intent_route} route. Coverage score: {coverage:.2f}."
            ),
        }

    # ------------------------------------------------------------------
    # COMBINE CHECKS → FINAL VERDICT
    # ------------------------------------------------------------------

    def _combine_checks(
        self,
        check_a:      dict,
        check_b:      dict,
        check_c:      dict,
        persona_level: str,
    ) -> PedagogicalVerdict:
        """
        Weighted combination:
            Check A (difficulty alignment):   0.35
            Check B (pedagogical quality):    0.50
            Check C (syllabus alignment):     0.15

        Persona match score = mean of all three (unweighted).
        """
        a_score = float(check_a.get("difficulty_alignment",  1.0))
        b_score = float(check_b.get("pedagogical_quality",   0.8))
        c_score = float(check_c.get("syllabus_alignment",    1.0))

        score             = a_score * 0.35 + b_score * 0.50 + c_score * 0.15
        persona_match     = (a_score + b_score + c_score) / 3.0

        flags = (
            check_a.get("flags", []) +
            check_b.get("flags", []) +
            check_c.get("flags", [])
        )

        b_verdict = check_b.get("verdict", "PASS")

        if b_verdict == "FAIL" or score < 0.55:
            final_verdict = "FAIL"
        elif b_verdict == "WARN" or score < 0.75:
            final_verdict = "WARN"
        else:
            final_verdict = "PASS"

        reasoning = (
            f"Difficulty alignment: {a_score:.2f} (persona={persona_level}). "
            f"Pedagogical quality: {b_verdict} (score={b_score:.2f}). "
            f"Syllabus alignment: {c_score:.2f}. "
            f"Composite score: {score:.3f}. "
            f"Persona match: {persona_match:.3f}. "
            f"Detail: {check_b.get('reasoning', 'N/A')}"
        )

        return PedagogicalVerdict(
            verdict              = final_verdict,
            score                = score,
            difficulty_alignment = a_score,
            pedagogical_quality  = b_score,
            syllabus_alignment   = c_score,
            persona_match_score  = persona_match,
            flags                = flags,
            reasoning            = reasoning,
        )

    def _print_summary(self, v: PedagogicalVerdict):
        icons = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}
        print(f"\n{icons.get(v.verdict,'?')} [Agent 3] VERDICT: {v.verdict}")
        print(f"   Score                : {v.score:.3f}")
        print(f"   Difficulty alignment : {v.difficulty_alignment:.3f}")
        print(f"   Pedagogical quality  : {v.pedagogical_quality:.3f}")
        print(f"   Syllabus alignment   : {v.syllabus_alignment:.3f}")
        print(f"   Persona match score  : {v.persona_match_score:.3f}")
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
    agent = PedagogicalAlignmentAgent(llm_client=llm)

    UNDERGRAD_PROFILE = {
        "persona_level": "Undergraduate Student",
        "cultural_context": "Neutral",
    }

    tests = [
        (
            "TEST 1: PASS — clear, complete NLP explanation",
            "What is the Bigram Markov Assumption?",
            "The Bigram Markov Assumption simplifies language modeling by assuming "
            "each word depends only on the immediately preceding word. Formally: "
            "P(w_i | w_1...w_{i-1}) ≈ P(w_i | w_{i-1}). This reduces computational "
            "complexity significantly while still capturing local word dependencies. "
            "[File: NLP-Week2-sp-2026.pdf, Page: 4]",
            "COURSE_NLP",
        ),
        (
            "TEST 2: WARN — too brief, incomplete",
            "Explain N-gram language models",
            "N-gram models use previous words to predict the next word.",
            "COURSE_NLP",
        ),
        (
            "TEST 3: PASS — general LLM response",
            "What is stress management?",
            "Stress management involves identifying stressors and employing techniques "
            "such as mindfulness, exercise, and time management to regulate their "
            "impact. According to the APA, chronic stress negatively affects both "
            "mental and physical health. See https://www.apa.org/topics/stress",
            "GENERAL_ASSISTANCE",
        ),
        (
            "TEST 4: FAIL — too complex for persona",
            "What is tokenisation?",
            "Tokenisation employs sophisticated morphological disambiguation "
            "algorithms leveraging probabilistic graphical models with stochastic "
            "context-free grammar induction paradigms to decompose heterogeneous "
            "orthographic representations into canonical lexical primitives.",
            "COURSE_NLP",
        ),
    ]

    for label, q, draft, route in tests:
        print("\n" + "=" * 70)
        print(label)
        print("=" * 70)
        result = agent.verify(
            question           = q,
            draft_answer       = draft,
            governance_profile = UNDERGRAD_PROFILE,
            intent_route       = route,
        )
        print(f"Verdict: {result.verdict} | Score: {result.score:.3f}")