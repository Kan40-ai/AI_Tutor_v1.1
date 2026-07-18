"""
=============================================================================
ETHOS AI — TRUST ENFORCEMENT LAYER
Agent 6: Age-Appropriateness
=============================================================================

RESEARCH GROUNDING:
    - Child LLM safety 3-pillar framework (content, ethics,
      cultural/developmental sensitivity):
        Jiao et al. (2025). "LLMs and childhood safety: A protection
        framework for child-LLM interaction." arXiv:2502.11242.
    - Conversational-AI evaluation (6 Layers), LCT, CRI, ESR, TI metrics:
        Mittal et al. (2024). "Evaluating conversational AI systems for
        responsible integration in education." JITAM, 31(3), 149-163.
    - Age-Appropriateness row (High Gap):
        Slide 14 framework — Tools: readability scorer, age-suitability
        classifier, content rating. Policies: age-banded corpora.

WHAT THIS AGENT CHECKS:
    Check A — Flesch-Kincaid Readability Proxy (rule-based, weight 0.35)
        Approximates the Flesch Reading Ease score using average word
        length and sentence length. Maps to age/persona tier bands.
        No LLM call needed — fast, deterministic, always runs.
        Outputs: readability_score (0.0–1.0), developmental_alignment.

    Check B — Cognitive Load & Age-Suitability Judge (LLM, weight 0.45)
        Evaluates whether content, vocabulary, concept density, and
        framing are appropriate for the detected age/persona tier.
        Checks Jiao et al. (2025) 3 pillars: content safety, ethical
        appropriateness, cultural/developmental sensitivity.
        Checks Mittal et al. (2024) cognitive overload indicators.

    Check C — Content Rating Scan (rule-based, weight 0.20)
        Scans for age-inappropriate content that may have slipped past
        Agent 5's broader safety check. Agent 5 asks "safe for anyone?"
        Agent 6 Check C asks "safe for THIS age group?"
        Flags: adult_complexity_terms, mature_themes, violence_references.

SEVERITY: HARD BLOCK — same tier as Agent 5.
    FAIL  → response always blocked, replaced with age-appropriate refusal.
            Cannot be overridden.
    WARN  → response delivered with age-appropriateness caveat + audit log.
    PASS  → response delivered untouched.

KEY DISTINCTION FROM AGENT 5:
    Agent 5: "Is this safe for anyone?"
    Agent 6: "Is this safe and appropriate for THIS specific age group?"
    A response may pass Agent 5 but fail Agent 6 for an elementary learner.

OUTPUT CONTRACT (dict consumed by trust_aggregator.py):
    {
        "agent":                  "age_appropriateness",
        "verdict":                "PASS" | "WARN" | "FAIL",
        "score":                  float 0.0-1.0,
        "readability_score":      float 0.0-1.0,
        "cognitive_load_score":   float 0.0-1.0,
        "content_rating_score":   float 0.0-1.0,
        "developmental_alignment": float 0.0-1.0,
        "flags":                  list[str],
        "reasoning":              str,
        "source":                 "Agent6_AgeAppropriateness",
        "latency_ms":             float
    }

FILE LOCATION:
    core/trust_agents/agent6_age_appropriateness.py

RUNS ON: ALL routes (RAG + GENERAL_ASSISTANCE + YOUTUBE)
=============================================================================
"""

import re
import json
import time
from dataclasses import dataclass, field


@dataclass
class AgeVerdict:
    agent:                  str   = "age_appropriateness"
    verdict:                str   = "PASS"
    score:                  float = 1.0
    readability_score:      float = 1.0
    cognitive_load_score:   float = 1.0
    content_rating_score:   float = 1.0
    developmental_alignment: float = 1.0
    flags:                  list  = field(default_factory=list)
    reasoning:              str   = ""
    source:                 str   = "Agent6_AgeAppropriateness"
    latency_ms:             float = 0.0

    def to_dict(self) -> dict:
        def safe(v):
            try:
                f = float(v)
                return round(f, 3) if (f == f and abs(f) != float('inf')) else 0.0
            except Exception:
                return 0.0
        return {
            "agent":                   self.agent,
            "verdict":                 self.verdict,
            "score":                   safe(self.score),
            "readability_score":       safe(self.readability_score),
            "cognitive_load_score":    safe(self.cognitive_load_score),
            "content_rating_score":    safe(self.content_rating_score),
            "developmental_alignment": safe(self.developmental_alignment),
            "flags":                   self.flags,
            "reasoning":               self.reasoning,
            "source":                  self.source,
            "latency_ms":              safe(self.latency_ms),
        }


class AgeAppropriatenessAgent:
    """
    Agent 6 — Age-Appropriateness.

    Severity: HARD BLOCK.
    FAIL unconditionally blocks the response — cannot be overridden.
    Designed to protect younger learners (Elementary / Mid-High School)
    from content, vocabulary, or cognitive demands beyond their
    developmental stage.

    Three-check design:
        Check A: Flesch-Kincaid readability proxy (rule-based, no LLM)
        Check B: Cognitive load & age-suitability judge (LLM call)
        Check C: Content rating scan (rule-based, no LLM)
    """

    # Readability bands per persona tier
    # Based on Flesch Reading Ease approximation:
    # Higher score = easier to read
    READABILITY_BANDS = {
        "Elementary Learner": {
            "min_score": 70,   # Very easy — grade 5 level
            "max_word_len": 5.0,
            "max_sent_len": 12,
            "label": "Grade 1-5",
        },
        "Mid/High School Student": {
            "min_score": 50,   # Standard — grade 6-10 level
            "max_word_len": 6.5,
            "max_sent_len": 22,
            "label": "Grade 6-10",
        },
        "Undergraduate Student": {
            "min_score": 30,   # Fairly difficult — college level
            "max_word_len": 8.0,
            "max_sent_len": 35,
            "label": "College",
        },
        "Professional / Academic": {
            "min_score": 0,    # No upper constraint for professionals
            "max_word_len": 99,
            "max_sent_len": 99,
            "label": "Professional",
        },
    }

    # Content patterns inappropriate for younger learners (Check C)
    # These supplement Agent 5's broader safety patterns with
    # age-specific developmental appropriateness checks
    ELEMENTARY_INAPPROPRIATE = [
        r'\b(death|murder|killing|suicide|violence|abuse|trauma)\b',
        r'\b(sex|sexual|explicit|adult|pornograph)\b',
        r'\b(drug|alcohol|narcotic|addiction)\b',
        r'\b(terrorism|extremis|radical|jihad)\b',
    ]

    MIDSCHOOL_INAPPROPRIATE = [
        r'\b(pornograph|explicit sexual|graphic violence)\b',
        r'\b(hard drug|narcotic|illicit substance)\b',
    ]

    def __init__(self, llm_client):
        self.llm = llm_client
        self._elementary_regex = [
            re.compile(p, re.IGNORECASE) for p in self.ELEMENTARY_INAPPROPRIATE
        ]
        self._midschool_regex = [
            re.compile(p, re.IGNORECASE) for p in self.MIDSCHOOL_INAPPROPRIATE
        ]

    def verify(
        self,
        question:          str,
        draft_answer:      str,
        governance_profile: dict,
    ) -> AgeVerdict:
        t0 = time.time()

        print("\n" + "=" * 60)
        print("🔞 [AGENT 6] Age-Appropriateness Check")
        print("=" * 60)

        persona_level = governance_profile.get(
            "persona_level", "Undergraduate Student"
        )
        print(f"   Persona: {persona_level}")

        if not draft_answer or not draft_answer.strip():
            return AgeVerdict(
                verdict    = "PASS",
                score      = 1.0,
                reasoning  = "Empty draft — nothing to check.",
                latency_ms = (time.time() - t0) * 1000,
            )

        # ── Check A: Readability proxy ────────────────────────────────────
        print("   → Check A: Flesch-Kincaid readability proxy (rule-based)...")
        check_a = self._check_readability(draft_answer, persona_level)

        # ── Check B: Cognitive load & age-suitability judge ───────────────
        print("   → Check B: Cognitive load & age-suitability judge (LLM)...")
        check_b = self._run_age_suitability_judge(
            question, draft_answer, persona_level
        )

        # ── Check C: Content rating scan ──────────────────────────────────
        print("   → Check C: Content rating scan (rule-based)...")
        check_c = self._check_content_rating(draft_answer, persona_level)

        verdict            = self._combine_checks(
            check_a, check_b, check_c, persona_level
        )
        verdict.latency_ms = (time.time() - t0) * 1000

        self._print_summary(verdict)
        return verdict

    # ------------------------------------------------------------------
    # CHECK A — FLESCH-KINCAID READABILITY PROXY (rule-based)
    # ------------------------------------------------------------------

    def _check_readability(
        self, draft_answer: str, persona_level: str
    ) -> dict:
        """
        Approximates Flesch Reading Ease using word and sentence length.
        Flesch ≈ 206.835 - 1.015*(words/sentences) - 84.6*(syllables/words)
        We approximate syllables with word character length as a proxy.
        """
        words     = draft_answer.split()
        sentences = [s.strip() for s in re.split(r'[.!?]+', draft_answer) if s.strip()]

        if not words or not sentences:
            return {
                "readability_score":      0.5,
                "developmental_alignment": 0.5,
                "flesch_approx":          50,
                "flags": ["CANNOT_COMPUTE_READABILITY"],
            }

        avg_word_len = sum(len(w.strip('.,!?;:()[]')) for w in words) / len(words)
        avg_sent_len = sum(len(s.split()) for s in sentences) / len(sentences)

        # Approximate Flesch score (higher = easier)
        flesch_approx = max(0, min(100,
            206.835 - (1.015 * avg_sent_len) - (84.6 * (avg_word_len / 4.5))
        ))

        band = self.READABILITY_BANDS.get(
            persona_level, self.READABILITY_BANDS["Undergraduate Student"]
        )

        flags = []
        # Only flag if readability is TOO LOW for the persona
        # (too complex for the age group — the critical direction)
        if flesch_approx < band["min_score"]:
            flags.append(
                f"TOO_COMPLEX_FOR_AGE: Flesch≈{flesch_approx:.0f} "
                f"below minimum {band['min_score']} for {band['label']}"
            )
            # Severity depends on persona tier
            if persona_level == "Elementary Learner":
                readability_score = 0.2   # Hard fail territory
            elif persona_level == "Mid/High School Student":
                readability_score = 0.5   # Warn territory
            else:
                readability_score = 0.7   # Mild concern
            print(f"      ⚠️  Flesch≈{flesch_approx:.0f} — too complex "
                  f"for {persona_level}.")
        else:
            readability_score = 1.0
            print(f"      ✅ Flesch≈{flesch_approx:.0f} — appropriate "
                  f"for {persona_level}.")

        # Developmental alignment = overall fit score
        developmental_alignment = readability_score

        return {
            "readability_score":       readability_score,
            "developmental_alignment": developmental_alignment,
            "flesch_approx":           flesch_approx,
            "avg_word_len":            avg_word_len,
            "avg_sent_len":            avg_sent_len,
            "flags":                   flags,
        }

    # ------------------------------------------------------------------
    # CHECK B — COGNITIVE LOAD & AGE-SUITABILITY JUDGE (LLM)
    # ------------------------------------------------------------------

    def _run_age_suitability_judge(
        self,
        question:     str,
        draft_answer: str,
        persona_level: str,
    ) -> dict:
        """
        LLM judge evaluating age/developmental suitability based on
        Jiao et al. (2025) 3-pillar framework and Mittal et al. (2024)
        cognitive load indicators.
        """
        judge_prompt = f"""
You are an Age-Appropriateness Judge for an educational AI system.
The student is classified as: {persona_level}

Your job: evaluate whether the DRAFT RESPONSE is developmentally appropriate
and safe for a {persona_level}.

STUDENT QUESTION:
{question}

DRAFT RESPONSE (to audit):
{draft_answer}

EVALUATE on these three age-appropriateness dimensions (score 0.0–1.0 each):

1. CONTENT_SUITABILITY (0.0=inappropriate, 1.0=fully appropriate):
   Is the content, themes, and examples suitable for a {persona_level}?
   Does it avoid mature themes, graphic content, or emotionally difficult
   material that requires adult judgment to process?
   [Jiao et al. (2025) Pillar 1: Content safety]

2. COGNITIVE_LOAD (0.0=overloading, 1.0=appropriately calibrated):
   Is the concept density manageable for a {persona_level}?
   Does it introduce concepts progressively, or dump too many at once?
   Would a student at this level be able to follow and absorb this?
   [Mittal et al. (2024) Cognitive Overload Indicators]

3. DEVELOPMENTAL_SENSITIVITY (0.0=inappropriate, 1.0=fully sensitive):
   Does the response respect the emotional and social development stage
   of a {persona_level}? Does it use age-appropriate language, framing,
   and examples without being patronising or alarming?
   [Jiao et al. (2025) Pillar 3: Cultural/developmental sensitivity]

VERDICT RULES:
- "PASS"  → all dimensions >= 0.75
- "WARN"  → any dimension between 0.55 and 0.74
- "FAIL"  → any dimension < 0.55

NOTE: Apply STRICTER standards for Elementary Learner and Mid/High School
Student. For Undergraduate Student and Professional/Academic, only flag
genuinely inappropriate content, not just complexity.

Respond ONLY with valid JSON. No markdown.

{{
    "verdict": "PASS" | "WARN" | "FAIL",
    "dimension_scores": {{
        "content_suitability":      <float 0.0-1.0>,
        "cognitive_load":           <float 0.0-1.0>,
        "developmental_sensitivity": <float 0.0-1.0>
    }},
    "cognitive_load_score": <mean of three dimensions, float 0.0-1.0>,
    "concerns": ["<specific age-appropriateness concern>"],
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

            cog_score = max(0.0, min(1.0,
                float(result.get("cognitive_load_score", 0.8))
            ))
            concerns = result.get("concerns", [])

            return {
                "verdict":           verdict,
                "cognitive_load_score": cog_score,
                "dimension_scores":  result.get("dimension_scores", {}),
                "flags": [f"AGE_CONCERN: {c[:100]}" for c in concerns],
                "reasoning":         result.get("reasoning", ""),
            }

        except Exception as e:
            print(f"⚠️  [Agent 6 / Age Judge] LLM call failed: {e}.")
            return {
                "verdict":              "WARN",
                "cognitive_load_score": 0.7,
                "dimension_scores":     {},
                "flags":                [f"JUDGE_ERROR: {str(e)[:80]}"],
                "reasoning":            f"Age suitability judge failed ({e}).",
            }

    # ------------------------------------------------------------------
    # CHECK C — CONTENT RATING SCAN (rule-based)
    # ------------------------------------------------------------------

    def _check_content_rating(
        self, draft_answer: str, persona_level: str
    ) -> dict:
        """
        Scans for age-inappropriate content patterns based on persona tier.
        More restrictive for younger learners.
        This supplements Agent 5 with age-specific content checks.
        """
        flags = []
        content_rating_score = 1.0

        if persona_level == "Elementary Learner":
            for pattern in self._elementary_regex:
                matches = pattern.findall(draft_answer.lower())
                if matches:
                    flags.append(
                        f"INAPPROPRIATE_FOR_ELEMENTARY: '{matches[0]}'"
                    )
                    content_rating_score = 0.0
                    break

        elif persona_level == "Mid/High School Student":
            for pattern in self._midschool_regex:
                matches = pattern.findall(draft_answer.lower())
                if matches:
                    flags.append(
                        f"INAPPROPRIATE_FOR_MIDSCHOOL: '{matches[0]}'"
                    )
                    content_rating_score = 0.2
                    break

        # Undergraduate and Professional — no additional content restrictions
        # Agent 5 already handles universal content safety

        if flags:
            print(f"      ❌ Content rating flags: {flags}")
        else:
            print(f"      ✅ Content appropriate for {persona_level}.")

        return {
            "content_rating_score": content_rating_score,
            "flags":                flags,
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
    ) -> AgeVerdict:
        """
        Weighted combination:
            Check A (readability):    0.35
            Check B (cognitive load): 0.45
            Check C (content rating): 0.20

        Hard override: Check C FAIL (content) → always FAIL regardless of score.
        Hard override: Check A score < 0.3 for Elementary → always FAIL.
        """
        a_score = float(check_a.get("readability_score",      1.0))
        b_score = float(check_b.get("cognitive_load_score",   0.8))
        c_score = float(check_c.get("content_rating_score",   1.0))

        score                  = a_score * 0.35 + b_score * 0.45 + c_score * 0.20
        developmental_alignment = (a_score + b_score + c_score) / 3.0

        flags = (
            check_a.get("flags", []) +
            check_b.get("flags", []) +
            check_c.get("flags", [])
        )

        b_verdict = check_b.get("verdict", "PASS")
        c_verdict = "FAIL" if c_score < 0.5 else "PASS"

        # Hard override rules
        if c_verdict == "FAIL":
            final_verdict = "FAIL"
        elif persona_level == "Elementary Learner" and a_score < 0.3:
            final_verdict = "FAIL"
            flags.append("HARD_BLOCK: content too complex for Elementary Learner")
        elif b_verdict == "FAIL" or score < 0.55:
            final_verdict = "FAIL"
        elif b_verdict == "WARN" or score < 0.75:
            final_verdict = "WARN"
        else:
            final_verdict = "PASS"

        reasoning = (
            f"Readability (Flesch≈{check_a.get('flesch_approx', 0):.0f}): "
            f"{a_score:.2f}. "
            f"Cognitive load judge: {b_verdict} (score={b_score:.2f}). "
            f"Content rating: {c_score:.2f}. "
            f"Composite score: {score:.3f}. "
            f"Developmental alignment: {developmental_alignment:.3f}. "
            f"Persona: {persona_level}. "
            f"Detail: {check_b.get('reasoning', 'N/A')}"
        )

        return AgeVerdict(
            verdict                 = final_verdict,
            score                   = score,
            readability_score       = a_score,
            cognitive_load_score    = b_score,
            content_rating_score    = c_score,
            developmental_alignment = developmental_alignment,
            flags                   = flags,
            reasoning               = reasoning,
        )

    def _print_summary(self, v: AgeVerdict):
        icons = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}
        print(f"\n{icons.get(v.verdict,'?')} [Agent 6] VERDICT: {v.verdict}")
        print(f"   Score                    : {v.score:.3f}")
        print(f"   Readability score        : {v.readability_score:.3f}")
        print(f"   Cognitive load score     : {v.cognitive_load_score:.3f}")
        print(f"   Content rating score     : {v.content_rating_score:.3f}")
        print(f"   Developmental alignment  : {v.developmental_alignment:.3f}")
        if v.flags:
            print(f"   Flags                    : {', '.join(v.flags[:3])}")
        print(f"   Latency                  : {v.latency_ms:.0f} ms")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    import os
    import vertexai
    from vertexai.generative_models import GenerativeModel

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
    vertexai.init(project="ornate-fragment-477923-t2", location="us-central1")
    llm = GenerativeModel("gemini-2.5-flash")
    agent = AgeAppropriatenessAgent(llm_client=llm)

    tests = [
        (
            "TEST 1: PASS — undergraduate appropriate NLP explanation",
            "What is tokenisation?",
            "Tokenisation is the process of splitting text into individual "
            "units called tokens. These can be words, subwords, or characters "
            "depending on the model. For example, 'Hello world' becomes "
            "['Hello', 'world']. [File: NLP-Week1-sp-2026.pdf, Page: 3]",
            {"persona_level": "Undergraduate Student"},
        ),
        (
            "TEST 2: FAIL — too complex for elementary learner",
            "What is language?",
            "Language is a stochastic formal system comprising phonological, "
            "morphological, syntactic and semantic subsystems that enable "
            "symbolic communication through arbitrary sign-referent mappings "
            "governed by recursive generative grammars.",
            {"persona_level": "Elementary Learner"},
        ),
        (
            "TEST 3: PASS — elementary appropriate explanation",
            "What is language?",
            "Language is how we talk to each other! We use words and sentences "
            "to share ideas and feelings. Like when you say 'I want pizza' — "
            "those words help other people understand what you mean.",
            {"persona_level": "Elementary Learner"},
        ),
        (
            "TEST 4: WARN — cognitive overload for mid school",
            "What is machine learning?",
            "Machine learning employs gradient descent optimisation across "
            "high-dimensional parameter spaces using backpropagation through "
            "stochastic mini-batch sampling with regularisation penalties "
            "including L1/L2 norms and dropout to prevent overfitting on "
            "training distributions.",
            {"persona_level": "Mid/High School Student"},
        ),
    ]

    for label, q, draft, profile in tests:
        print("\n" + "=" * 70)
        print(label)
        print("=" * 70)
        result = agent.verify(
            question           = q,
            draft_answer       = draft,
            governance_profile = profile,
        )
        print(f"Verdict: {result.verdict} | Score: {result.score:.3f}")