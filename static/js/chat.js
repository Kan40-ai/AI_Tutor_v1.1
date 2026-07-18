// // ==========================================
// // ETHOS AI - FRONTEND CHAT LOGIC
// // ==========================================

// // --- Function triggered when a Prompt Pill is clicked ---
// function usePrompt(text) {
//     const inputField = document.getElementById('user-input');
//     inputField.value = text;
    
//     // Hide the welcome screen immediately
//     const welcomeScreen = document.getElementById('welcome-screen');
//     if (welcomeScreen) {
//         welcomeScreen.style.display = 'none';
//     }
    
//     sendMessage(); // Auto-send!
// }

// document.addEventListener('DOMContentLoaded', () => {
//     const sendBtn = document.getElementById('send-btn');
//     const inputField = document.getElementById('user-input');

//     // Allow pressing "Enter" to send
//     inputField.addEventListener('keypress', function (e) {
//         if (e.key === 'Enter') {
//             sendMessage();
//         }
//     });

//     sendBtn.addEventListener('click', sendMessage);
// });


// // ─────────────────────────────────────────────────────────────────────────────
// // 🛡️ TRUST VERDICT PANEL — Layer III Trust Enforcement (Agent 1 + 4 + 5)
// //
// // NEW FUNCTION — added below existing DOMContentLoaded block.
// // Everything above this line is unchanged from the original chat.js.
// //
// // Renders one card per active trust agent in the sidebar, appended below
// // the Sources section after every response.
// //
// // Paper purpose: provides screenshot-ready trust transparency evidence —
// //   • PASS/WARN/FAIL badge with colour coding per agent
// //   • Per-agent score bars and flags
// //   • Collapsible reasoning for paper figure captions
// //   • Verification latency in ms (cost-aware orchestration evidence)
// //
// // Data source: data.trust_verdicts returned by app.py
// //   — agent1_factual : Agent 1 (Factual Accuracy)  verdict dict | "skipped"
// //   — agent2_transparency : Agent 2 (Transparency)        verdict dict | always runs
// //   — agent4_bias    : Agent 4 (Bias & Fairness)    verdict dict | "skipped"
// //   — agent5_safety  : Agent 5 (Safety & Ethics)    verdict dict | always runs
// // ─────────────────────────────────────────────────────────────────────────────
// function renderTrustPanel(sidePanel, trustVerdicts, status, trustAggregate) {
//     if (!trustVerdicts) return;

//     const agent1 = trustVerdicts.agent1_factual;
//     const agent2 = trustVerdicts.agent2_transparency;  
//     const agent3 = trustVerdicts.agent3_pedagogical;
//     const agent4 = trustVerdicts.agent4_bias;
//     const agent6 = trustVerdicts.agent6_age;

//     // If Agent 5 hard-blocked, override Agent 1 and 4 skip messages
//     // so the panel clearly communicates the pipeline was short-circuited.
//     const safetyBlocked = (status === "safety_block" || status === "age_block");
//     const skipReason    = safetyBlocked
//         ? "Not invoked — query blocked by Agent 5 Safety firewall before generation."
//         : null;
//     const agent5 = trustVerdicts.agent5_safety;

//     // ── Shared helper: map verdict string → colour scheme ────────────────
//     function getScheme(verdict) {
//         return {
//             PASS: { bg: '#EAF3DE', border: '#639922', badgeBg: '#3B6D11', icon: '✅', label: 'PASS' },
//             WARN: { bg: '#FAEEDA', border: '#BA7517', badgeBg: '#633806', icon: '⚠️', label: 'WARN' },
//             FAIL: { bg: '#FCEBEB', border: '#E24B4A', badgeBg: '#791F1F', icon: '❌', label: 'FAIL' },
//         }[verdict] || { bg: '#F1F5F9', border: '#94A3B8', badgeBg: '#475569', icon: '?', label: verdict };
//     }

//     // ── Shared helper: render a single metric progress bar ───────────────
//     // isInverse: true if higher = worse (hallucination rate, violation rate)
//     function renderBar(label, rawValue, isInverse) {
//         const pct      = Math.round((rawValue || 0) * 100);
//         const barColor = isInverse ? (pct > 25 ? '#E24B4A' : '#639922') : (pct < 50 ? '#E24B4A' : '#639922');
//         const txtColor = isInverse ? (pct > 25 ? '#A32D2D' : '#3B6D11') : (pct < 50 ? '#A32D2D' : '#3B6D11');
//         return `<div style="margin-bottom: 8px;">
//             <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#475569; margin-bottom:3px;">
//                 <span>${label}</span><span style="font-weight:600; color:${txtColor};">${pct}%</span>
//             </div>
//             <div style="background:#E2E8F0; border-radius:4px; height:5px; overflow:hidden;">
//                 <div style="width:${pct}%; height:100%; background:${barColor}; border-radius:4px;"></div>
//             </div></div>`;
//     }

//     // ── Shared helper: render flag pills ─────────────────────────────────
//     function renderFlags(flags) {
//         return (flags || []).length > 0
//             ? flags.map(f => `<span style="display:inline-block; background:#F1F5F9; border:1px solid #CBD5E1;
//                 color:#475569; font-size:0.72rem; padding:2px 7px; border-radius:12px; margin:2px 2px 0 0;">${f}</span>`
//               ).join('')
//             : `<span style="color:#94A3B8; font-size:0.78rem;">None</span>`;
//     }

//     // ── Open the Trust Enforcement section wrapper ────────────────────────
//     let panelHTML = `
//         <div style="margin-top: 20px; border-top: 2px solid #E2E8F0; padding-top: 14px;">
//             <h3 style="margin: 0 0 10px 0; font-size: 1rem; color: #1E293B; font-weight: 600;">
//                 🛡️ Trust Enforcement
//             </h3>`;

//     // ─────────────────────────────────────────────────────────────────────
//     // AGENT 1 — FACTUAL ACCURACY CARD
//     // RAG route only. Skipped for GENERAL_ASSISTANCE / YouTube routes.
//     // ─────────────────────────────────────────────────────────────────────
//     if (!agent1 || typeof agent1 === 'string') {
//         panelHTML += `
//             <!-- Agent 1 — skipped (non-RAG route) -->
//             <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-left:4px solid #94A3B8;
//                         border-radius:8px; padding:10px 13px; font-size:0.82rem; color:#64748B;
//                         margin-bottom:10px;">
//                 <span style="font-size:0.75rem; font-weight:600; text-transform:uppercase;
//                              letter-spacing:0.05em; color:#94A3B8; display:block; margin-bottom:4px;">
//                     Agent 1 — Factual Accuracy
//                 </span>
//                 ⊘ ${skipReason || 'Not applicable — general knowledge or YouTube route. No course context to verify against.'}
//             </div>`;
//     } else {
//         const s1 = getScheme(agent1.verdict);
//         panelHTML += `
//             <!-- Agent 1 Verdict Card -->
//             <div style="background:${s1.bg}; border:1px solid ${s1.border};
//                         border-left:4px solid ${s1.border}; border-radius:8px;
//                         padding:12px 13px; font-size:0.82rem; margin-bottom:6px;">
//                 <!-- Header: agent label + verdict badge -->
//                 <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">
//                     <span style="font-size:0.75rem; font-weight:600; text-transform:uppercase;
//                                  letter-spacing:0.05em; color:#64748B;">Agent 1 — Factual Accuracy</span>
//                     <span style="background:${s1.badgeBg}; color:#fff; font-size:0.72rem;
//                                  font-weight:700; padding:3px 9px; border-radius:12px;
//                                  letter-spacing:0.06em;">${s1.icon} ${s1.label}</span>
//                 </div>
//                 ${renderBar('Trust score',        agent1.score              || 0, false)}
//                 ${renderBar('Hallucination rate', agent1.hallucination_rate || 0, true)}
//                 ${renderBar('Citation coverage',  agent1.citation_coverage  || 0, false)}
//                 <div style="margin-bottom:8px;">
//                     <div style="font-size:0.73rem; font-weight:600; color:#64748B;
//                                 text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px;">Flags</div>
//                     <div>${renderFlags(agent1.flags)}</div>
//                 </div>
//                 <div style="font-size:0.72rem; color:#94A3B8; text-align:right;
//                             border-top:1px solid rgba(0,0,0,0.06); padding-top:6px; margin-top:4px;">
//                     Verified in ${Math.round(agent1.latency_ms || 0)} ms
//                     &nbsp;·&nbsp; ${agent1.source || 'Agent1_FactualAccuracy'}
//                 </div>
//             </div>

//             <!-- Collapsible NLI reasoning — expand for paper screenshots -->
//             <!-- Collapsible NLI reasoning — expand for paper screenshots -->
//             <details style="margin-top: 6px; margin-bottom: 14px;">
//                 <summary style="font-size: 0.75rem; color: #64748B; cursor: pointer;
//                                 user-select: none; padding: 4px 0; list-style: none;">
//                     ▸ View NLI judge reasoning
//                 </summary>
//                 <div style="background: #F8FAFC; border: 1px solid #E2E8F0;
//                             border-radius: 6px; padding: 9px 11px; font-size: 0.75rem;
//                             color: #475569; line-height: 1.5; margin-top: 4px;">
//                     ${agent1.reasoning || 'No reasoning available.'}
//                 </div>
//             </details>`;
//     }


//     // ─────────────────────────────────────────────────────────────────────
//     // AGENT 2 — TRANSPARENCY & EXPLAINABILITY CARD
//     // RAG route only — transparency only measurable with course context.
//     // Severity: Soft WARN — FAIL annotates response, does not block.
//     // Metrics: citation coverage, uncertainty score, explainability score,
//     // audit completeness.
//     // ─────────────────────────────────────────────────────────────────────
//     if (!agent2 || typeof agent2 === 'string') {
//         panelHTML += `
//             <!-- Agent 2 — skipped -->
//             <div style="background:#F8FAFC; border:1px solid #E2E8F0;
//                         border-left:4px solid #94A3B8; border-radius:8px;
//                         padding:10px 13px; font-size:0.82rem; color:#64748B;
//                         margin-bottom:10px;">
//                 <span style="font-size:0.75rem; font-weight:600; text-transform:uppercase;
//                              letter-spacing:0.05em; color:#94A3B8; display:block;
//                              margin-bottom:4px;">Agent 2 — Transparency</span>
//                 ⊘ ${skipReason || 'Not applicable — general knowledge or YouTube route.'}
//             </div>`;
//     } else {
//         const s2 = getScheme(agent2.verdict);
//         panelHTML += `
//             <!-- Agent 2 Verdict Card -->
//             <div style="background:${s2.bg}; border:1px solid ${s2.border};
//                         border-left:4px solid ${s2.border}; border-radius:8px;
//                         padding:12px 13px; font-size:0.82rem; margin-bottom:6px;">
//                 <div style="display:flex; align-items:center;
//                             justify-content:space-between; margin-bottom:10px;">
//                     <span style="font-size:0.75rem; font-weight:600;
//                                  text-transform:uppercase; letter-spacing:0.05em;
//                                  color:#64748B;">Agent 2 — Transparency</span>
//                     <span style="background:${s2.badgeBg}; color:#fff; font-size:0.72rem;
//                                  font-weight:700; padding:3px 9px; border-radius:12px;
//                                  letter-spacing:0.06em;">${s2.icon} ${s2.label}</span>
//                 </div>
//                 ${renderBar('Transparency score',    agent2.score                 || 0, false)}
//                 ${renderBar('Citation coverage',     agent2.citation_coverage     || 0, false)}
//                 // ${renderBar('Uncertainty language',  agent2.uncertainty_score     || 0, false)}
//                 ${renderBar('Explainability score',  agent2.explainability_score  || 0, false)}
//                 ${renderBar('Audit completeness',    agent2.audit_completeness    || 0, false)}
//                 <div style="margin-bottom:8px;">
//                     <div style="font-size:0.73rem; font-weight:600; color:#64748B;
//                                 text-transform:uppercase; letter-spacing:0.04em;
//                                 margin-bottom:4px;">Flags</div>
//                     <div>${renderFlags(agent2.flags)}</div>
//                 </div>
//                 <div style="font-size:0.72rem; color:#94A3B8; text-align:right;
//                             border-top:1px solid rgba(0,0,0,0.06); padding-top:6px; margin-top:4px;">
//                     Verified in ${Math.round(agent2.latency_ms || 0)} ms
//                     &nbsp;·&nbsp; ${agent2.source || 'Agent2_Transparency'}
//                 </div>
//             </div>
//             <!-- Collapsible transparency reasoning -->
//             <details style="margin-top:6px; margin-bottom:14px;">
//                 <summary style="font-size:0.75rem; color:#64748B; cursor:pointer;
//                                 user-select:none; padding:4px 0; list-style:none;">
//                     ▸ View transparency audit reasoning
//                 </summary>
//                 <div style="background:#F8FAFC; border:1px solid #E2E8F0;
//                             border-radius:6px; padding:9px 11px; font-size:0.75rem;
//                             color:#475569; line-height:1.5; margin-top:4px;">
//                     ${agent2.reasoning || 'No reasoning available.'}
//                 </div>
//             </details>`;
//     }





//     // ─────────────────────────────────────────────────────────────────────
//     // AGENT 3 — PEDAGOGICAL ALIGNMENT CARD
//     // Runs on ALL routes. Severity: Advisory LOG only.
//     // Response always delivered untouched — FAIL/WARN logged for
//     // longitudinal pedagogical drift analysis in EduTrust-Eval.
//     // Reference: Liu et al. (2025) LPITutor PeerJ CS.
//     // ─────────────────────────────────────────────────────────────────────
//     if (!agent3 || typeof agent3 === 'string') {
//         panelHTML += `
//             <div style="background:#F8FAFC; border:1px solid #E2E8F0;
//                         border-left:4px solid #94A3B8; border-radius:8px;
//                         padding:10px 13px; font-size:0.82rem; color:#64748B;
//                         margin-bottom:10px;">
//                 <span style="font-size:0.75rem; font-weight:600; text-transform:uppercase;
//                              letter-spacing:0.05em; color:#94A3B8; display:block;
//                              margin-bottom:4px;">Agent 3 — Pedagogical Alignment</span>
//                 ⊘ ${skipReason || 'Skipped — no governance profile available.'}
//             </div>`;
//     } else {
//         const s3 = getScheme(agent3.verdict);
//         panelHTML += `
//             <div style="background:${s3.bg}; border:1px solid ${s3.border};
//                         border-left:4px solid ${s3.border}; border-radius:8px;
//                         padding:12px 13px; font-size:0.82rem; margin-bottom:6px;">
//                 <div style="display:flex; align-items:center;
//                             justify-content:space-between; margin-bottom:10px;">
//                     <span style="font-size:0.75rem; font-weight:600;
//                                  text-transform:uppercase; letter-spacing:0.05em;
//                                  color:#64748B;">Agent 3 — Pedagogical Alignment</span>
//                     <span style="background:${s3.badgeBg}; color:#fff; font-size:0.72rem;
//                                  font-weight:700; padding:3px 9px; border-radius:12px;
//                                  letter-spacing:0.06em;">${s3.icon} ${s3.label}
//                         <span style="font-size:0.65rem; opacity:0.85;"> · Advisory</span>
//                     </span>
//                 </div>
//                 ${renderBar('Pedagogical score',    agent3.score                 || 0, false)}
//                 ${renderBar('Difficulty alignment', agent3.difficulty_alignment  || 0, false)}
//                 ${renderBar('Pedagogical quality',  agent3.pedagogical_quality   || 0, false)}
//                 ${renderBar('Syllabus alignment',   agent3.syllabus_alignment    || 0, false)}
//                 ${renderBar('Persona match score',  agent3.persona_match_score   || 0, false)}
//                 <div style="margin-bottom:8px;">
//                     <div style="font-size:0.73rem; font-weight:600; color:#64748B;
//                                 text-transform:uppercase; letter-spacing:0.04em;
//                                 margin-bottom:4px;">Flags</div>
//                     <div>${renderFlags(agent3.flags)}</div>
//                 </div>
//                 <!-- Advisory note — makes severity tier explicit for paper screenshots -->
//                 <div style="font-size:0.72rem; color:#64748B; font-style:italic;
//                             border-top:1px solid rgba(0,0,0,0.06); padding-top:6px; margin-top:4px;">
//                     📋 Advisory log only — response delivered untouched regardless of verdict.
//                     Logged for longitudinal pedagogical drift analysis.
//                 </div>
//                 <div style="font-size:0.72rem; color:#94A3B8; text-align:right; margin-top:4px;">
//                     Verified in ${Math.round(agent3.latency_ms || 0)} ms
//                     &nbsp;·&nbsp; ${agent3.source || 'Agent3_PedagogicalAlignment'}
//                 </div>
//             </div>
//             <details style="margin-top:6px; margin-bottom:14px;">
//                 <summary style="font-size:0.75rem; color:#64748B; cursor:pointer;
//                                 user-select:none; padding:4px 0; list-style:none;">
//                     ▸ View pedagogical audit reasoning
//                 </summary>
//                 <div style="background:#F8FAFC; border:1px solid #E2E8F0;
//                             border-radius:6px; padding:9px 11px; font-size:0.75rem;
//                             color:#475569; line-height:1.5; margin-top:4px;">
//                     ${agent3.reasoning || 'No reasoning available.'}
//                 </div>
//             </details>`;
//     }




//     // ─────────────────────────────────────────────────────────────────────
//     // AGENT 4 — BIAS & FAIRNESS CARD
//     // Runs on ALL routes (RAG + GENERAL_ASSISTANCE + YouTube).
//     // Only agent with cross-layer data dependency (reads governance_profile
//     // from Layer I to verify Layer II response compliance).
//     // Paper note: WARN/FAIL are audit-only — bias is a measurement criterion.
//     // ─────────────────────────────────────────────────────────────────────
//     if (!agent4 || typeof agent4 === 'string') {
//         panelHTML += `
//             <!-- Agent 4 — skipped (no governance profile) -->
//             <div style="background: #F8FAFC; border: 1px solid #E2E8F0;
//                         border-left: 4px solid #94A3B8; border-radius: 8px;
//                         padding: 10px 13px; font-size: 0.82rem; color: #64748B;
//                         margin-bottom: 10px;">
//                 <span style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
//                              letter-spacing: 0.05em; color: #94A3B8; display: block;
//                              margin-bottom: 4px;">
//                     Agent 4 — Bias & Fairness
//                 </span>
//                 ⊘ ${skipReason || 'Skipped — no governance profile available.'}
//             </div>`;
//     } else {
//         const s4 = getScheme(agent4.verdict);
//         panelHTML += `
//             <!-- Agent 4 Verdict Card -->
//             <div style="background: ${s4.bg};
//                         border: 1px solid ${s4.border};
//                         border-left: 4px solid ${s4.border};
//                         border-radius: 8px; padding: 12px 13px;
//                         font-size: 0.82rem; margin-bottom: 6px;">
//                 <div style="display: flex; align-items: center;
//                             justify-content: space-between; margin-bottom: 10px;">
//                     <span style="font-size: 0.75rem; font-weight: 600;
//                                  text-transform: uppercase; letter-spacing: 0.05em;
//                                  color: #64748B;">Agent 4 — Bias & Fairness</span>
//                     <span style="background: ${s4.badgeBg}; color: #fff; font-size: 0.72rem;
//                                  font-weight: 700; padding: 3px 9px; border-radius: 12px;
//                                  letter-spacing: 0.06em;">${s4.icon} ${s4.label}</span>
//                 </div>
//                 ${renderBar('Bias & fairness score',  agent4.score                   || 0, false)}
//                 ${renderBar('Policy compliance',       agent4.policy_compliance_score || 0, false)}
//                 ${renderBar('Demographic neutrality',  agent4.demographic_neutrality  || 0, false)}
//                 ${renderBar('Difficulty alignment',    agent4.difficulty_alignment    || 0, false)}
//                 ${renderBar('Policy violation rate',   agent4.policy_violation_rate   || 0, true)}
//                 <div style="margin-bottom: 8px;">
//                     <div style="font-size: 0.73rem; font-weight: 600; color: #64748B;
//                                 text-transform: uppercase; letter-spacing: 0.04em;
//                                 margin-bottom: 4px;">Flags</div>
//                     <div>${renderFlags(agent4.flags)}</div>
//                 </div>
//                 <div style="font-size: 0.72rem; color: #94A3B8; text-align: right;
//                             border-top: 1px solid rgba(0,0,0,0.06); padding-top: 6px; margin-top: 4px;">
//                     Verified in ${Math.round(agent4.latency_ms || 0)} ms
//                     &nbsp;·&nbsp; ${agent4.source || 'Agent4_BiasFairness'}
//                 </div>
//             </div>
//             <!-- Collapsible bias reasoning — expand for paper screenshots -->
//             <details style="margin-top: 6px; margin-bottom: 14px;">
//                 <summary style="font-size: 0.75rem; color: #64748B; cursor: pointer;
//                                 user-select: none; padding: 4px 0; list-style: none;">
//                     ▸ View bias audit reasoning
//                 </summary>
//                 <div style="background: #F8FAFC; border: 1px solid #E2E8F0;
//                             border-radius: 6px; padding: 9px 11px; font-size: 0.75rem;
//                             color: #475569; line-height: 1.5; margin-top: 4px;">
//                     ${agent4.reasoning || 'No reasoning available.'}
//                 </div>
//             </details>`;
//     }

//     // ─────────────────────────────────────────────────────────────────────
//     // AGENT 5 — SAFETY & ETHICS CARD
//     // Runs FIRST on ALL routes — hardest block in the system.
//     // FAIL unconditionally blocks the response before any other agent.
//     // Checks: jailbreak pre-screen, LLM safety judge, crisis escalation.
//     // Paper note: always present — never skipped.
//     // Research: Jiao et al. (2025) arXiv:2502.11242; Inan et al. (2023)
//     // ─────────────────────────────────────────────────────────────────────
//     if (!agent5 || typeof agent5 === 'string') {
//         panelHTML += `
//             <!-- Agent 5 — skipped -->
//             <div style="background: #F8FAFC; border: 1px solid #E2E8F0;
//                         border-left: 4px solid #94A3B8; border-radius: 8px;
//                         padding: 10px 13px; font-size: 0.82rem; color: #64748B;
//                         margin-bottom: 10px;">
//                 <span style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
//                              letter-spacing: 0.05em; color: #94A3B8; display: block;
//                              margin-bottom: 4px;">
//                     Agent 5 — Safety & Ethics
//                 </span>
//                 ⊘ Skipped.
//             </div>`;
//     } else {
//         const s5 = getScheme(agent5.verdict);
//         panelHTML += `
//             <!-- Agent 5 Verdict Card -->
//             <div style="background: ${s5.bg};
//                         border: 1px solid ${s5.border};
//                         border-left: 4px solid ${s5.border};
//                         border-radius: 8px; padding: 12px 13px;
//                         font-size: 0.82rem; margin-bottom: 6px;">
//                 <div style="display: flex; align-items: center;
//                             justify-content: space-between; margin-bottom: 10px;">
//                     <span style="font-size: 0.75rem; font-weight: 600;
//                                  text-transform: uppercase; letter-spacing: 0.05em;
//                                  color: #64748B;">Agent 5 — Safety & Ethics</span>
//                     <span style="background: ${s5.badgeBg}; color: #fff; font-size: 0.72rem;
//                                  font-weight: 700; padding: 3px 9px; border-radius: 12px;
//                                  letter-spacing: 0.06em;">${s5.icon} ${s5.label}</span>
//                 </div>
//                 ${renderBar('Safety score',          agent5.safety_score         || 0, false)}
//                 ${renderBar('Unsafe response rate',  agent5.unsafe_response_rate || 0, true)}
//                 <!-- Boolean indicators -->
//                 <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px;">
//                     <span style="font-size: 0.72rem; padding: 3px 8px; border-radius: 10px;
//                                  background: ${agent5.jailbreak_detected ? '#FCEBEB' : '#EAF3DE'};
//                                  color: ${agent5.jailbreak_detected ? '#791F1F' : '#27500A'};
//                                  border: 1px solid ${agent5.jailbreak_detected ? '#F09595' : '#C0DD97'};">
//                         ${agent5.jailbreak_detected ? '🔴 Jailbreak detected' : '🟢 No jailbreak'}
//                     </span>
//                     <span style="font-size: 0.72rem; padding: 3px 8px; border-radius: 10px;
//                                  background: ${agent5.crisis_detected ? '#FAEEDA' : '#EAF3DE'};
//                                  color: ${agent5.crisis_detected ? '#633806' : '#27500A'};
//                                  border: 1px solid ${agent5.crisis_detected ? '#FAC775' : '#C0DD97'};">
//                         ${agent5.crisis_detected
//                             ? (agent5.crisis_escalated ? '⚠️ Crisis — escalated ✓' : '🔴 Crisis — NOT escalated')
//                             : '🟢 No crisis signals'}
//                     </span>
//                 </div>
//                 <div style="margin-bottom: 8px;">
//                     <div style="font-size: 0.73rem; font-weight: 600; color: #64748B;
//                                 text-transform: uppercase; letter-spacing: 0.04em;
//                                 margin-bottom: 4px;">Flags</div>
//                     <div>${renderFlags(agent5.flags)}</div>
//                 </div>
//                 <div style="font-size: 0.72rem; color: #94A3B8; text-align: right;
//                             border-top: 1px solid rgba(0,0,0,0.06); padding-top: 6px; margin-top: 4px;">
//                     Verified in ${Math.round(agent5.latency_ms || 0)} ms
//                     &nbsp;·&nbsp; ${agent5.source || 'Agent5_SafetyEthics'}
//                 </div>
//             </div>
//             <!-- Collapsible safety reasoning — expand for paper screenshots -->
//             <details style="margin-top: 6px; margin-bottom: 10px;">
//                 <summary style="font-size: 0.75rem; color: #64748B; cursor: pointer;
//                                 user-select: none; padding: 4px 0; list-style: none;">
//                     ▸ View safety audit reasoning
//                 </summary>
//                 <div style="background: #F8FAFC; border: 1px solid #E2E8F0;
//                             border-radius: 6px; padding: 9px 11px; font-size: 0.75rem;
//                             color: #475569; line-height: 1.5; margin-top: 4px;">
//                     ${agent5.reasoning || 'No reasoning available.'}
//                 </div>
//             </details>`;
//     }



//     // ─────────────────────────────────────────────────────────────────────
//     // AGENT 6 — AGE-APPROPRIATENESS CARD
//     // ─────────────────────────────────────────────────────────────────────
//     if (!agent6 || typeof agent6 === 'string') {
//         panelHTML += `
//             <div style="background:#F8FAFC; border:1px solid #E2E8F0;
//                         border-left:4px solid #94A3B8; border-radius:8px;
//                         padding:10px 13px; font-size:0.82rem; color:#64748B;
//                         margin-bottom:10px;">
//                 <span style="font-size:0.75rem; font-weight:600; text-transform:uppercase;
//                              letter-spacing:0.05em; color:#94A3B8; display:block;
//                              margin-bottom:4px;">Agent 6 — Age-Appropriateness</span>
//                 ⊘ ${skipReason || 'Skipped — no governance profile available.'}
//             </div>`;
//     } else {
//         const s6 = getScheme(agent6.verdict);
//         panelHTML += `
//             <div style="background:${s6.bg}; border:1px solid ${s6.border};
//                         border-left:4px solid ${s6.border}; border-radius:8px;
//                         padding:12px 13px; font-size:0.82rem; margin-bottom:6px;">
//                 <div style="display:flex; align-items:center;
//                             justify-content:space-between; margin-bottom:10px;">
//                     <span style="font-size:0.75rem; font-weight:600;
//                                  text-transform:uppercase; letter-spacing:0.05em;
//                                  color:#64748B;">Agent 6 — Age-Appropriateness</span>
//                     <span style="background:${s6.badgeBg}; color:#fff; font-size:0.72rem;
//                                  font-weight:700; padding:3px 9px; border-radius:12px;
//                                  letter-spacing:0.06em;">${s6.icon} ${s6.label}</span>
//                 </div>
//                 ${renderBar('Age-appropriateness score',  agent6.score                   || 0, false)}
//                 ${renderBar('Readability score',          agent6.readability_score       || 0, false)}
//                 ${renderBar('Cognitive load score',       agent6.cognitive_load_score    || 0, false)}
//                 ${renderBar('Content rating',             agent6.content_rating_score    || 0, false)}
//                 ${renderBar('Developmental alignment',    agent6.developmental_alignment || 0, false)}
//                 <div style="margin-bottom:8px;">
//                     <div style="font-size:0.73rem; font-weight:600; color:#64748B;
//                                 text-transform:uppercase; letter-spacing:0.04em;
//                                 margin-bottom:4px;">Flags</div>
//                     <div>${renderFlags(agent6.flags)}</div>
//                 </div>
//                 <div style="font-size:0.72rem; color:#94A3B8; text-align:right;
//                             border-top:1px solid rgba(0,0,0,0.06); padding-top:6px; margin-top:4px;">
//                     Verified in ${Math.round(agent6.latency_ms || 0)} ms
//                     &nbsp;·&nbsp; ${agent6.source || 'Agent6_AgeAppropriateness'}
//                 </div>
//             </div>
//             <details style="margin-top:6px; margin-bottom:10px;">
//                 <summary style="font-size:0.75rem; color:#64748B; cursor:pointer;
//                                 user-select:none; padding:4px 0; list-style:none;">
//                     ▸ View age-appropriateness reasoning
//                 </summary>
//                 <div style="background:#F8FAFC; border:1px solid #E2E8F0;
//                             border-radius:6px; padding:9px 11px; font-size:0.75rem;
//                             color:#475569; line-height:1.5; margin-top:4px;">
//                     ${agent6.reasoning || 'No reasoning available.'}
//                 </div>
//             </details>`;
//     }



//     // ── Close the Trust Enforcement section wrapper ───────────────────────
//     panelHTML += `</div>`;
//     sidePanel.innerHTML += panelHTML;
// }   

// // ─────────────────────────────────────────────────────────────────────────────
// // END OF NEW CODE — everything below is unchanged from the original chat.js
// // ─────────────────────────────────────────────────────────────────────────────


// async function sendMessage() {
//     const input = document.getElementById('user-input');
//     const chatPanel = document.getElementById('chat-panel');
//     const sidePanel = document.getElementById('side-panel');
//     const message = input.value.trim();

//     if (!message) return;

//     // --- Hide the welcome screen when a user types their own message ---
//     const welcomeScreen = document.getElementById('welcome-screen');
//     if (welcomeScreen) {
//         welcomeScreen.style.display = 'none';
//     }

//     // 1. Add User Message
//     chatPanel.innerHTML += `<div class="msg user"><b>You:</b> ${message}</div>`;
//     input.value = '';
    
//     // Auto-scroll to bottom
//     chatPanel.scrollTop = chatPanel.scrollHeight;

//     // 2. Add Loading Indicator
//     const botMsgId = 'bot-' + Date.now();
//     chatPanel.innerHTML += `<div class="msg bot" id="${botMsgId}"><i>Thinking...</i></div>`;
//     chatPanel.scrollTop = chatPanel.scrollHeight;

//     try {
//         // 3. Call the Flask Backend
//         const response = await fetch('/api/chat', {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify({ message: message, mode: 'rag' })
//         });

//         const data = await response.json();
//         console.log("RAW RESPONSE:", JSON.stringify(data, null, 2));
//         console.log("STATUS:", data.status);
//         console.log("ANSWER LENGTH:", (data.answer || "").length);
//         console.log("TRUST KEYS:", Object.keys(data.trust_verdicts || {}));
//         const botDiv = document.getElementById(botMsgId);

//         if (data.error) {
//             botDiv.innerHTML = `<b>Tutor:</b> ⚠️ ${data.error}`;
//             return;
//         }
        
//         // --- 4. Render the Answer & Extract Links (WITH ERROR HANDLING) ---
//         let formattedAnswer = data.answer || "";
//         const extractedLLMLinks = []; 

//         // 1. Broad Regex: Catches ANY attempt at [Text](url)
//         const attemptedMarkdownRegex = /\[([^\]]+)\]\s*\(([^)]+)\)/g;
        
//         formattedAnswer = formattedAnswer.replace(attemptedMarkdownRegex, function(match, text, url) {
//             const cleanText = text ? text.trim() : "";
//             const cleanUrl = url ? url.trim() : "";
//             const isValidUrl = /^https?:\/\/[^\s]+$/.test(cleanUrl);
//             const hasTitle = cleanText.length > 0;

//             if (!isValidUrl || !hasTitle) {
//                 console.error("🚨 MALFORMED AI LINK DETECTED 🚨\nOutput:", match);
//                 return `<span style="color: #dc3545; font-size: 0.9em; border-bottom: 1px dotted #dc3545; cursor: help;" title="Broken URL: ${cleanUrl}">⚠️ [Broken Link: ${cleanText}]</span>`;
//             }

//             extractedLLMLinks.push({ isLLMLink: true, title: cleanText, url: cleanUrl }); 
//             return `<a href="${cleanUrl}" target="_blank" style="color: #007bff; text-decoration: underline;">${cleanText}</a>`;
//         });

//         // B. Convert any remaining naked URLs
//         const nakedUrlRegex = /(?<!href=")(https?:\/\/[^\s<]+)/g;
//         formattedAnswer = formattedAnswer.replace(nakedUrlRegex, function(url) {
//             const cleanUrl = url.trim();
//             extractedLLMLinks.push({ isLLMLink: true, title: cleanUrl, url: cleanUrl });
//             return `<a href="${cleanUrl}" target="_blank" style="color: #007bff; text-decoration: underline;">${cleanUrl}</a>`;
//         });

//         // C. Replace newlines with <br> and bold with <b> tags
//         formattedAnswer = formattedAnswer.replace(/\n/g, '<br>');
//         formattedAnswer = formattedAnswer.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');

//         botDiv.innerHTML = `<b>Tutor:</b> ${formattedAnswer}`;

//         // --- 5. Update the Sources Sidebar ---
//         sidePanel.innerHTML = '<h3>📚 Sources</h3>';
        
//         const rawSources = data.sources || [];
//         const cleanSources = rawSources.filter(src => src && src !== "");

//         // Dump extracted links into sources array
//         extractedLLMLinks.forEach(linkObj => cleanSources.push(linkObj));

//         // ROUTE A: General LLM Route
//         if (cleanSources.length === 0) {
//             sidePanel.innerHTML += `
//                 <div class="source-card" style="border-left: 4px solid #6c757d; background: #f8f9fa;">
//                     <div style="font-size: 1.2rem; margin-bottom: 5px;">🧠</div>
//                     <strong>General Knowledge</strong><br>
//                     <small class="text-muted">This response is based on the AI's baseline training. No specific course documents were matched.</small>
//                 </div>`;
//         } 
//         // ROUTE B, C, & D: RAG, YouTube, or Extracted Links
//         else {
//             cleanSources.forEach(src => {
//                 let cardHTML = "";

//                 if (src.isLLMLink) {
//                     cardHTML = `
//                         <div class="source-card" style="border-left: 4px solid #17a2b8;">
//                             <strong>🌐 Web Resource</strong><br>
//                             <a href="${src.url}" target="_blank" style="color: #007bff; text-decoration: underline; font-size: 0.85rem;">${src.title}</a>
//                         </div>`;
//                 } else if (typeof src === 'string') {
//                     if (src.includes("youtube.com") || src.includes("youtu.be")) {
//                         cardHTML = `
//                             <div class="source-card" style="border-left: 4px solid #ff0000;">
//                                 <strong>▶️ YouTube Video</strong><br>
//                                 <a href="${src}" target="_blank" style="color: #007bff; text-decoration: underline; font-size: 0.85rem;">Watch Reference Video</a>
//                             </div>`;
//                     } else {
//                         cardHTML = `
//                             <div class="source-card" style="border-left: 4px solid #007bff;">
//                                 <strong>📄 ${src}</strong><br>
//                                 <small class="text-muted">Reference Document</small>
//                             </div>`;
//                     }
//                 } else if (typeof src === 'object' && !src.isLLMLink) {
//                     const fileName = src.file || src.source || "Course Material";
//                     const pageInfo = src.page ? `Page(s): ${src.page}` : "Reference Text";
                    
//                     cardHTML = `
//                         <div class="source-card" style="border-left: 4px solid #28a745;">
//                             <strong>📄 ${fileName}</strong><br>
//                             <small class="text-muted">${pageInfo}</small>
//                         </div>`;
//                 }

//                 sidePanel.innerHTML += cardHTML;
//             });
//         }

//         // --- 6. 🛡️ Render Trust Verdict Panel (Layer III — Agent 1 + 4 + 5) ---
//         // Single call — renderTrustPanel renders all three agent cards below Sources.
//         // Agent 5 (Safety) always shown. Agent 1 skipped on non-RAG routes.
//         // Agent 4 (Bias) always shown when governance profile available.
//         renderTrustPanel(sidePanel, data.trust_verdicts, data.status);

//         // 7. Tell MathJax to render formulas
//         if (window.MathJax) {
//             MathJax.typesetPromise([chatPanel]).catch(function (err) {
//                 console.error('MathJax error:', err.message);
//             });
//         }

//         chatPanel.scrollTop = chatPanel.scrollHeight;

//     } catch (error) {
//         document.getElementById(botMsgId).innerHTML = "<b>Tutor:</b> ⚠️ Network error. Please check your backend terminal.";
//         console.error("Fetch error:", error);
//     }
// }








// ==========================================
// ETHOS AI - FRONTEND CHAT LOGIC
// ==========================================

// --- Function triggered when a Prompt Pill is clicked ---
function usePrompt(text) {
    const inputField = document.getElementById('user-input');
    inputField.value = text;
    
    // Hide the welcome screen immediately
    const welcomeScreen = document.getElementById('welcome-screen');
    if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
    }
    
    sendMessage(); // Auto-send!
}

document.addEventListener('DOMContentLoaded', () => {
    const sendBtn = document.getElementById('send-btn');
    const inputField = document.getElementById('user-input');

    // Allow pressing "Enter" to send
    inputField.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);
});


// ─────────────────────────────────────────────────────────────────────────────
// 🛡️ TRUST VERDICT PANEL — Layer III Trust Enforcement (Agent 1 + 4 + 5)
//
// NEW FUNCTION — added below existing DOMContentLoaded block.
// Everything above this line is unchanged from the original chat.js.
//
// Renders one card per active trust agent in the sidebar, appended below
// the Sources section after every response.
//
// Paper purpose: provides screenshot-ready trust transparency evidence —
//   • PASS/WARN/FAIL badge with colour coding per agent
//   • Per-agent score bars and flags
//   • Collapsible reasoning for paper figure captions
//   • Verification latency in ms (cost-aware orchestration evidence)
//
// Data source: data.trust_verdicts returned by app.py
//   — agent1_factual : Agent 1 (Factual Accuracy)  verdict dict | "skipped"
//   — agent2_transparency : Agent 2 (Transparency)        verdict dict | always runs
//   — agent4_bias    : Agent 4 (Bias & Fairness)    verdict dict | "skipped"
//   — agent5_safety  : Agent 5 (Safety & Ethics)    verdict dict | always runs
// ─────────────────────────────────────────────────────────────────────────────
function renderTrustPanel(sidePanel, trustVerdicts, status) {
    if (!trustVerdicts) return;

    const agent1 = trustVerdicts.agent1_factual;
    const agent2 = trustVerdicts.agent2_transparency;  
    const agent3 = trustVerdicts.agent3_pedagogical;
    const agent4 = trustVerdicts.agent4_bias;
    const agent6 = trustVerdicts.agent6_age;

    // If Agent 5 hard-blocked, override Agent 1 and 4 skip messages
    // so the panel clearly communicates the pipeline was short-circuited.
    const safetyBlocked = (status === "safety_block" || status === "age_block"
                           || (trustVerdicts.agent5_safety &&
                               trustVerdicts.agent5_safety.verdict === "FAIL" &&
                               !trustVerdicts.agent1_factual &&
                               !trustVerdicts.agent2_transparency));
    const skipReason    = safetyBlocked
        ? "Not invoked — query hard-blocked by Agent 5 Safety firewall before generation."
        : null;
    const agent5 = trustVerdicts.agent5_safety;

    // ── Shared helper: map verdict string → colour scheme ────────────────
    function getScheme(verdict) {
        return {
            PASS: { bg: '#EAF3DE', border: '#639922', badgeBg: '#3B6D11', icon: '✅', label: 'PASS' },
            WARN: { bg: '#FAEEDA', border: '#BA7517', badgeBg: '#633806', icon: '⚠️', label: 'WARN' },
            FAIL: { bg: '#FCEBEB', border: '#E24B4A', badgeBg: '#791F1F', icon: '❌', label: 'FAIL' },
        }[verdict] || { bg: '#F1F5F9', border: '#94A3B8', badgeBg: '#475569', icon: '?', label: verdict };
    }

    // ── Shared helper: render a single metric progress bar ───────────────
    // isInverse: true if higher = worse (hallucination rate, violation rate)
    function renderBar(label, rawValue, isInverse) {
        const pct      = Math.round((rawValue || 0) * 100);
        const barColor = isInverse ? (pct > 25 ? '#E24B4A' : '#639922') : (pct < 50 ? '#E24B4A' : '#639922');
        const txtColor = isInverse ? (pct > 25 ? '#A32D2D' : '#3B6D11') : (pct < 50 ? '#A32D2D' : '#3B6D11');
        return `<div style="margin-bottom: 8px;">
            <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#475569; margin-bottom:3px;">
                <span>${label}</span><span style="font-weight:600; color:${txtColor};">${pct}%</span>
            </div>
            <div style="background:#E2E8F0; border-radius:4px; height:5px; overflow:hidden;">
                <div style="width:${pct}%; height:100%; background:${barColor}; border-radius:4px;"></div>
            </div></div>`;
    }

    // ── Shared helper: render flag pills ─────────────────────────────────
    function renderFlags(flags) {
        return (flags || []).length > 0
            ? flags.map(f => `<span style="display:inline-block; background:#F1F5F9; border:1px solid #CBD5E1;
                color:#475569; font-size:0.72rem; padding:2px 7px; border-radius:12px; margin:2px 2px 0 0;">${f}</span>`
              ).join('')
            : `<span style="color:#94A3B8; font-size:0.78rem;">None</span>`;
    }

    // ── Open the Trust Enforcement section wrapper ────────────────────────
    let panelHTML = `
        <div style="margin-top: 20px; border-top: 2px solid #E2E8F0; padding-top: 14px;">
            <h3 style="margin: 0 0 10px 0; font-size: 1rem; color: #1E293B; font-weight: 600;">
                🛡️ Trust Enforcement
            </h3>`;

    // ── SAFETY HARD-BLOCK BANNER ────────────────────────
    // Shown prominently when Agent 5 fires and hard-blocks the pipeline.
    // All remaining agents show as 'Not invoked' below this banner.
    if (safetyBlocked) {
        const a5 = trustVerdicts.agent5_safety || {};
        const blockedBy = (status === 'age_block') ? 'Agent 6 — Age-Appropriateness' : 'Agent 5 — Safety & Ethics';
        panelHTML += `
        <!-- 🚫 SAFETY HARD-BLOCK BANNER -->
        <div style="background:#7F1D1D; border-radius:10px; padding:14px 16px;
                    margin-bottom:16px; border:2px solid #991B1B;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                <span style="font-size:1.4rem;">🚫</span>
                <div>
                    <div style="font-size:0.85rem; font-weight:800; color:#fff;
                                letter-spacing:0.06em; text-transform:uppercase;">
                        HARD BLOCK — RESPONSE SUPPRESSED
                    </div>
                    <div style="font-size:0.75rem; color:#FCA5A5; margin-top:2px;">
                        Blocked by ${blockedBy} before LLM was called
                    </div>
                </div>
            </div>
            <div style="background:rgba(255,255,255,0.08); border-radius:6px;
                        padding:8px 10px; font-size:0.75rem; color:#FECACA;
                        line-height:1.5; margin-bottom:8px;">
                ${a5.reasoning
                    ? a5.reasoning.substring(0, 300) + (a5.reasoning.length > 300 ? '...' : '')
                    : 'No reasoning captured.'}
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:6px;">
                ${(a5.jailbreak_detected
                    ? '<span style="background:#991B1B; color:#fff; font-size:0.7rem; padding:2px 8px; border-radius:10px; font-weight:700;">&#128308; Jailbreak Detected</span>'
                    : '')}
                ${(a5.crisis_detected
                    ? '<span style="background:#92400E; color:#fff; font-size:0.7rem; padding:2px 8px; border-radius:10px; font-weight:700;">&#9888;&#65039; Crisis Signal</span>'
                    : '')}
                <span style="background:#374151; color:#D1D5DB; font-size:0.7rem;
                             padding:2px 8px; border-radius:10px;">
                    Agents 1 – 4 &amp; 6: Not invoked
                </span>
                <span style="background:#374151; color:#D1D5DB; font-size:0.7rem;
                             padding:2px 8px; border-radius:10px;">
                    Latency saved: ~35s
                </span>
            </div>
        </div>`;
    }

    // ─────────────────────────────────────────────────────────────────────
    // AGENT 1 — FACTUAL ACCURACY CARD
    // RAG route only. Skipped for GENERAL_ASSISTANCE / YouTube routes.
    // ─────────────────────────────────────────────────────────────────────
    if (!agent1 || typeof agent1 === 'string') {
        panelHTML += `
            <!-- Agent 1 — skipped (non-RAG route) -->
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-left:4px solid #94A3B8;
                        border-radius:8px; padding:10px 13px; font-size:0.82rem; color:#64748B;
                        margin-bottom:10px;">
                <span style="font-size:0.75rem; font-weight:600; text-transform:uppercase;
                             letter-spacing:0.05em; color:#94A3B8; display:block; margin-bottom:4px;">
                    Agent 1 — Factual Accuracy
                </span>
                ⊘ ${skipReason || 'Not applicable — general knowledge or YouTube route. No course context to verify against.'}
            </div>`;
    } else {
        const s1 = getScheme(agent1.verdict);
        panelHTML += `
            <!-- Agent 1 Verdict Card -->
            <div style="background:${s1.bg}; border:1px solid ${s1.border};
                        border-left:4px solid ${s1.border}; border-radius:8px;
                        padding:12px 13px; font-size:0.82rem; margin-bottom:6px;">
                <!-- Header: agent label + verdict badge -->
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">
                    <span style="font-size:0.75rem; font-weight:600; text-transform:uppercase;
                                 letter-spacing:0.05em; color:#64748B;">Agent 1 — Factual Accuracy</span>
                    <span style="background:${s1.badgeBg}; color:#fff; font-size:0.72rem;
                                 font-weight:700; padding:3px 9px; border-radius:12px;
                                 letter-spacing:0.06em;">${s1.icon} ${s1.label}</span>
                </div>
                ${renderBar('Trust score',        agent1.score              || 0, false)}
                ${renderBar('Hallucination rate', agent1.hallucination_rate || 0, true)}
                ${renderBar('Citation coverage',  agent1.citation_coverage  || 0, false)}
                <div style="margin-bottom:8px;">
                    <div style="font-size:0.73rem; font-weight:600; color:#64748B;
                                text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px;">Flags</div>
                    <div>${renderFlags(agent1.flags)}</div>
                </div>
                <div style="font-size:0.72rem; color:#94A3B8; text-align:right;
                            border-top:1px solid rgba(0,0,0,0.06); padding-top:6px; margin-top:4px;">
                    Verified in ${Math.round(agent1.latency_ms || 0)} ms
                    &nbsp;·&nbsp; ${agent1.source || 'Agent1_FactualAccuracy'}
                </div>
            </div>

            <!-- Collapsible NLI reasoning — expand for paper screenshots -->
            <!-- Collapsible NLI reasoning — expand for paper screenshots -->
            <details style="margin-top: 6px; margin-bottom: 14px;">
                <summary style="font-size: 0.75rem; color: #64748B; cursor: pointer;
                                user-select: none; padding: 4px 0; list-style: none;">
                    ▸ View NLI judge reasoning
                </summary>
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0;
                            border-radius: 6px; padding: 9px 11px; font-size: 0.75rem;
                            color: #475569; line-height: 1.5; margin-top: 4px;">
                    ${agent1.reasoning || 'No reasoning available.'}
                </div>
            </details>`;
    }


    // ─────────────────────────────────────────────────────────────────────
    // AGENT 2 — TRANSPARENCY & EXPLAINABILITY CARD
    // RAG route only — transparency only measurable with course context.
    // Severity: Soft WARN — FAIL annotates response, does not block.
    // Metrics: citation coverage, uncertainty score, explainability score,
    // audit completeness.
    // ─────────────────────────────────────────────────────────────────────
    if (!agent2 || typeof agent2 === 'string') {
        panelHTML += `
            <!-- Agent 2 — skipped -->
            <div style="background:#F8FAFC; border:1px solid #E2E8F0;
                        border-left:4px solid #94A3B8; border-radius:8px;
                        padding:10px 13px; font-size:0.82rem; color:#64748B;
                        margin-bottom:10px;">
                <span style="font-size:0.75rem; font-weight:600; text-transform:uppercase;
                             letter-spacing:0.05em; color:#94A3B8; display:block;
                             margin-bottom:4px;">Agent 2 — Transparency</span>
                ⊘ ${skipReason || 'Not applicable — general knowledge or YouTube route.'}
            </div>`;
    } else {
        const s2 = getScheme(agent2.verdict);
        panelHTML += `
            <!-- Agent 2 Verdict Card -->
            <div style="background:${s2.bg}; border:1px solid ${s2.border};
                        border-left:4px solid ${s2.border}; border-radius:8px;
                        padding:12px 13px; font-size:0.82rem; margin-bottom:6px;">
                <div style="display:flex; align-items:center;
                            justify-content:space-between; margin-bottom:10px;">
                    <span style="font-size:0.75rem; font-weight:600;
                                 text-transform:uppercase; letter-spacing:0.05em;
                                 color:#64748B;">Agent 2 — Transparency</span>
                    <span style="background:${s2.badgeBg}; color:#fff; font-size:0.72rem;
                                 font-weight:700; padding:3px 9px; border-radius:12px;
                                 letter-spacing:0.06em;">${s2.icon} ${s2.label}</span>
                </div>
                ${renderBar('Transparency score',    agent2.score                 || 0, false)}
                ${renderBar('Citation coverage',     agent2.citation_coverage     || 0, false)}
                ${renderBar('Uncertainty language',  agent2.uncertainty_score     || 0, false)}
                ${renderBar('Explainability score',  agent2.explainability_score  || 0, false)}
                ${renderBar('Audit completeness',    agent2.audit_completeness    || 0, false)}
                <div style="margin-bottom:8px;">
                    <div style="font-size:0.73rem; font-weight:600; color:#64748B;
                                text-transform:uppercase; letter-spacing:0.04em;
                                margin-bottom:4px;">Flags</div>
                    <div>${renderFlags(agent2.flags)}</div>
                </div>
                <div style="font-size:0.72rem; color:#94A3B8; text-align:right;
                            border-top:1px solid rgba(0,0,0,0.06); padding-top:6px; margin-top:4px;">
                    Verified in ${Math.round(agent2.latency_ms || 0)} ms
                    &nbsp;·&nbsp; ${agent2.source || 'Agent2_Transparency'}
                </div>
            </div>
            <!-- Collapsible transparency reasoning -->
            <details style="margin-top:6px; margin-bottom:14px;">
                <summary style="font-size:0.75rem; color:#64748B; cursor:pointer;
                                user-select:none; padding:4px 0; list-style:none;">
                    ▸ View transparency audit reasoning
                </summary>
                <div style="background:#F8FAFC; border:1px solid #E2E8F0;
                            border-radius:6px; padding:9px 11px; font-size:0.75rem;
                            color:#475569; line-height:1.5; margin-top:4px;">
                    ${agent2.reasoning || 'No reasoning available.'}
                </div>
            </details>`;
    }





    // ─────────────────────────────────────────────────────────────────────
    // AGENT 3 — PEDAGOGICAL ALIGNMENT CARD
    // Runs on ALL routes. Severity: Advisory LOG only.
    // Response always delivered untouched — FAIL/WARN logged for
    // longitudinal pedagogical drift analysis in EduTrust-Eval.
    // Reference: Liu et al. (2025) LPITutor PeerJ CS.
    // ─────────────────────────────────────────────────────────────────────
    if (!agent3 || typeof agent3 === 'string') {
        panelHTML += `
            <div style="background:#F8FAFC; border:1px solid #E2E8F0;
                        border-left:4px solid #94A3B8; border-radius:8px;
                        padding:10px 13px; font-size:0.82rem; color:#64748B;
                        margin-bottom:10px;">
                <span style="font-size:0.75rem; font-weight:600; text-transform:uppercase;
                             letter-spacing:0.05em; color:#94A3B8; display:block;
                             margin-bottom:4px;">Agent 3 — Pedagogical Alignment</span>
                ⊘ ${skipReason || 'Skipped — no governance profile available.'}
            </div>`;
    } else {
        const s3 = getScheme(agent3.verdict);
        panelHTML += `
            <div style="background:${s3.bg}; border:1px solid ${s3.border};
                        border-left:4px solid ${s3.border}; border-radius:8px;
                        padding:12px 13px; font-size:0.82rem; margin-bottom:6px;">
                <div style="display:flex; align-items:center;
                            justify-content:space-between; margin-bottom:10px;">
                    <span style="font-size:0.75rem; font-weight:600;
                                 text-transform:uppercase; letter-spacing:0.05em;
                                 color:#64748B;">Agent 3 — Pedagogical Alignment</span>
                    <span style="background:${s3.badgeBg}; color:#fff; font-size:0.72rem;
                                 font-weight:700; padding:3px 9px; border-radius:12px;
                                 letter-spacing:0.06em;">${s3.icon} ${s3.label}
                        <span style="font-size:0.65rem; opacity:0.85;"> · Advisory</span>
                    </span>
                </div>
                ${renderBar('Pedagogical score',    agent3.score                 || 0, false)}
                ${renderBar('Difficulty alignment', agent3.difficulty_alignment  || 0, false)}
                ${renderBar('Pedagogical quality',  agent3.pedagogical_quality   || 0, false)}
                ${renderBar('Syllabus alignment',   agent3.syllabus_alignment    || 0, false)}
                ${renderBar('Persona match score',  agent3.persona_match_score   || 0, false)}
                <div style="margin-bottom:8px;">
                    <div style="font-size:0.73rem; font-weight:600; color:#64748B;
                                text-transform:uppercase; letter-spacing:0.04em;
                                margin-bottom:4px;">Flags</div>
                    <div>${renderFlags(agent3.flags)}</div>
                </div>
                <!-- Advisory note — makes severity tier explicit for paper screenshots -->
                <div style="font-size:0.72rem; color:#64748B; font-style:italic;
                            border-top:1px solid rgba(0,0,0,0.06); padding-top:6px; margin-top:4px;">
                    📋 Advisory log only — response delivered untouched regardless of verdict.
                    Logged for longitudinal pedagogical drift analysis.
                </div>
                <div style="font-size:0.72rem; color:#94A3B8; text-align:right; margin-top:4px;">
                    Verified in ${Math.round(agent3.latency_ms || 0)} ms
                    &nbsp;·&nbsp; ${agent3.source || 'Agent3_PedagogicalAlignment'}
                </div>
            </div>
            <details style="margin-top:6px; margin-bottom:14px;">
                <summary style="font-size:0.75rem; color:#64748B; cursor:pointer;
                                user-select:none; padding:4px 0; list-style:none;">
                    ▸ View pedagogical audit reasoning
                </summary>
                <div style="background:#F8FAFC; border:1px solid #E2E8F0;
                            border-radius:6px; padding:9px 11px; font-size:0.75rem;
                            color:#475569; line-height:1.5; margin-top:4px;">
                    ${agent3.reasoning || 'No reasoning available.'}
                </div>
            </details>`;
    }




    // ─────────────────────────────────────────────────────────────────────
    // AGENT 4 — BIAS & FAIRNESS CARD
    // Runs on ALL routes (RAG + GENERAL_ASSISTANCE + YouTube).
    // Only agent with cross-layer data dependency (reads governance_profile
    // from Layer I to verify Layer II response compliance).
    // Paper note: WARN/FAIL are audit-only — bias is a measurement criterion.
    // ─────────────────────────────────────────────────────────────────────
    if (!agent4 || typeof agent4 === 'string') {
        panelHTML += `
            <!-- Agent 4 — skipped (no governance profile) -->
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0;
                        border-left: 4px solid #94A3B8; border-radius: 8px;
                        padding: 10px 13px; font-size: 0.82rem; color: #64748B;
                        margin-bottom: 10px;">
                <span style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
                             letter-spacing: 0.05em; color: #94A3B8; display: block;
                             margin-bottom: 4px;">
                    Agent 4 — Bias & Fairness
                </span>
                ⊘ ${skipReason || 'Skipped — no governance profile available.'}
            </div>`;
    } else {
        const s4 = getScheme(agent4.verdict);
        panelHTML += `
            <!-- Agent 4 Verdict Card -->
            <div style="background: ${s4.bg};
                        border: 1px solid ${s4.border};
                        border-left: 4px solid ${s4.border};
                        border-radius: 8px; padding: 12px 13px;
                        font-size: 0.82rem; margin-bottom: 6px;">
                <div style="display: flex; align-items: center;
                            justify-content: space-between; margin-bottom: 10px;">
                    <span style="font-size: 0.75rem; font-weight: 600;
                                 text-transform: uppercase; letter-spacing: 0.05em;
                                 color: #64748B;">Agent 4 — Bias & Fairness</span>
                    <span style="background: ${s4.badgeBg}; color: #fff; font-size: 0.72rem;
                                 font-weight: 700; padding: 3px 9px; border-radius: 12px;
                                 letter-spacing: 0.06em;">${s4.icon} ${s4.label}</span>
                </div>
                ${renderBar('Bias & fairness score',  agent4.score                   || 0, false)}
                ${renderBar('Policy compliance',       agent4.policy_compliance_score || 0, false)}
                ${renderBar('Demographic neutrality',  agent4.demographic_neutrality  || 0, false)}
                ${renderBar('Difficulty alignment',    agent4.difficulty_alignment    || 0, false)}
                ${renderBar('Policy violation rate',   agent4.policy_violation_rate   || 0, true)}
                <div style="margin-bottom: 8px;">
                    <div style="font-size: 0.73rem; font-weight: 600; color: #64748B;
                                text-transform: uppercase; letter-spacing: 0.04em;
                                margin-bottom: 4px;">Flags</div>
                    <div>${renderFlags(agent4.flags)}</div>
                </div>
                <div style="font-size: 0.72rem; color: #94A3B8; text-align: right;
                            border-top: 1px solid rgba(0,0,0,0.06); padding-top: 6px; margin-top: 4px;">
                    Verified in ${Math.round(agent4.latency_ms || 0)} ms
                    &nbsp;·&nbsp; ${agent4.source || 'Agent4_BiasFairness'}
                </div>
            </div>
            <!-- Collapsible bias reasoning — expand for paper screenshots -->
            <details style="margin-top: 6px; margin-bottom: 14px;">
                <summary style="font-size: 0.75rem; color: #64748B; cursor: pointer;
                                user-select: none; padding: 4px 0; list-style: none;">
                    ▸ View bias audit reasoning
                </summary>
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0;
                            border-radius: 6px; padding: 9px 11px; font-size: 0.75rem;
                            color: #475569; line-height: 1.5; margin-top: 4px;">
                    ${agent4.reasoning || 'No reasoning available.'}
                </div>
            </details>`;
    }

    // ─────────────────────────────────────────────────────────────────────
    // AGENT 5 — SAFETY & ETHICS CARD
    // Runs FIRST on ALL routes — hardest block in the system.
    // FAIL unconditionally blocks the response before any other agent.
    // Checks: jailbreak pre-screen, LLM safety judge, crisis escalation.
    // Paper note: always present — never skipped.
    // Research: Jiao et al. (2025) arXiv:2502.11242; Inan et al. (2023)
    // ─────────────────────────────────────────────────────────────────────
    if (!agent5 || typeof agent5 === 'string') {
        panelHTML += `
            <!-- Agent 5 — skipped -->
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0;
                        border-left: 4px solid #94A3B8; border-radius: 8px;
                        padding: 10px 13px; font-size: 0.82rem; color: #64748B;
                        margin-bottom: 10px;">
                <span style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
                             letter-spacing: 0.05em; color: #94A3B8; display: block;
                             margin-bottom: 4px;">
                    Agent 5 — Safety & Ethics
                </span>
                ⊘ Skipped.
            </div>`;
    } else {
        const s5 = getScheme(agent5.verdict);
        panelHTML += `
            <!-- Agent 5 Verdict Card -->
            <div style="background: ${s5.bg};
                        border: 1px solid ${s5.border};
                        border-left: 4px solid ${s5.border};
                        border-radius: 8px; padding: 12px 13px;
                        font-size: 0.82rem; margin-bottom: 6px;">
                <div style="display: flex; align-items: center;
                            justify-content: space-between; margin-bottom: 10px;">
                    <span style="font-size: 0.75rem; font-weight: 600;
                                 text-transform: uppercase; letter-spacing: 0.05em;
                                 color: #64748B;">Agent 5 — Safety & Ethics</span>
                    <span style="background: ${s5.badgeBg}; color: #fff; font-size: 0.72rem;
                                 font-weight: 700; padding: 3px 9px; border-radius: 12px;
                                 letter-spacing: 0.06em;">${s5.icon} ${s5.label}</span>
                </div>
                ${renderBar('Safety score',          agent5.safety_score         || 0, false)}
                ${renderBar('Unsafe response rate',  agent5.unsafe_response_rate || 0, true)}
                <!-- Boolean indicators -->
                <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px;">
                    <span style="font-size: 0.72rem; padding: 3px 8px; border-radius: 10px;
                                 background: ${agent5.jailbreak_detected ? '#FCEBEB' : '#EAF3DE'};
                                 color: ${agent5.jailbreak_detected ? '#791F1F' : '#27500A'};
                                 border: 1px solid ${agent5.jailbreak_detected ? '#F09595' : '#C0DD97'};">
                        ${agent5.jailbreak_detected ? '🔴 Jailbreak detected' : '🟢 No jailbreak'}
                    </span>
                    <span style="font-size: 0.72rem; padding: 3px 8px; border-radius: 10px;
                                 background: ${agent5.crisis_detected ? '#FAEEDA' : '#EAF3DE'};
                                 color: ${agent5.crisis_detected ? '#633806' : '#27500A'};
                                 border: 1px solid ${agent5.crisis_detected ? '#FAC775' : '#C0DD97'};">
                        ${agent5.crisis_detected
                            ? (agent5.crisis_escalated ? '⚠️ Crisis — escalated ✓' : '🔴 Crisis — NOT escalated')
                            : '🟢 No crisis signals'}
                    </span>
                </div>
                <div style="margin-bottom: 8px;">
                    <div style="font-size: 0.73rem; font-weight: 600; color: #64748B;
                                text-transform: uppercase; letter-spacing: 0.04em;
                                margin-bottom: 4px;">Flags</div>
                    <div>${renderFlags(agent5.flags)}</div>
                </div>
                <div style="font-size: 0.72rem; color: #94A3B8; text-align: right;
                            border-top: 1px solid rgba(0,0,0,0.06); padding-top: 6px; margin-top: 4px;">
                    Verified in ${Math.round(agent5.latency_ms || 0)} ms
                    &nbsp;·&nbsp; ${agent5.source || 'Agent5_SafetyEthics'}
                </div>
            </div>
            <!-- Collapsible safety reasoning — expand for paper screenshots -->
            <details style="margin-top: 6px; margin-bottom: 10px;">
                <summary style="font-size: 0.75rem; color: #64748B; cursor: pointer;
                                user-select: none; padding: 4px 0; list-style: none;">
                    ▸ View safety audit reasoning
                </summary>
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0;
                            border-radius: 6px; padding: 9px 11px; font-size: 0.75rem;
                            color: #475569; line-height: 1.5; margin-top: 4px;">
                    ${agent5.reasoning || 'No reasoning available.'}
                </div>
            </details>`;
    }



    // ─────────────────────────────────────────────────────────────────────
    // AGENT 6 — AGE-APPROPRIATENESS CARD
    // ─────────────────────────────────────────────────────────────────────
    if (!agent6 || typeof agent6 === 'string') {
        panelHTML += `
            <div style="background:#F8FAFC; border:1px solid #E2E8F0;
                        border-left:4px solid #94A3B8; border-radius:8px;
                        padding:10px 13px; font-size:0.82rem; color:#64748B;
                        margin-bottom:10px;">
                <span style="font-size:0.75rem; font-weight:600; text-transform:uppercase;
                             letter-spacing:0.05em; color:#94A3B8; display:block;
                             margin-bottom:4px;">Agent 6 — Age-Appropriateness</span>
                ⊘ ${skipReason || 'Skipped — no governance profile available.'}
            </div>`;
    } else {
        const s6 = getScheme(agent6.verdict);
        panelHTML += `
            <div style="background:${s6.bg}; border:1px solid ${s6.border};
                        border-left:4px solid ${s6.border}; border-radius:8px;
                        padding:12px 13px; font-size:0.82rem; margin-bottom:6px;">
                <div style="display:flex; align-items:center;
                            justify-content:space-between; margin-bottom:10px;">
                    <span style="font-size:0.75rem; font-weight:600;
                                 text-transform:uppercase; letter-spacing:0.05em;
                                 color:#64748B;">Agent 6 — Age-Appropriateness</span>
                    <span style="background:${s6.badgeBg}; color:#fff; font-size:0.72rem;
                                 font-weight:700; padding:3px 9px; border-radius:12px;
                                 letter-spacing:0.06em;">${s6.icon} ${s6.label}</span>
                </div>
                ${renderBar('Age-appropriateness score',  agent6.score                   || 0, false)}
                ${renderBar('Readability score',          agent6.readability_score       || 0, false)}
                ${renderBar('Cognitive load score',       agent6.cognitive_load_score    || 0, false)}
                ${renderBar('Content rating',             agent6.content_rating_score    || 0, false)}
                ${renderBar('Developmental alignment',    agent6.developmental_alignment || 0, false)}
                <div style="margin-bottom:8px;">
                    <div style="font-size:0.73rem; font-weight:600; color:#64748B;
                                text-transform:uppercase; letter-spacing:0.04em;
                                margin-bottom:4px;">Flags</div>
                    <div>${renderFlags(agent6.flags)}</div>
                </div>
                <div style="font-size:0.72rem; color:#94A3B8; text-align:right;
                            border-top:1px solid rgba(0,0,0,0.06); padding-top:6px; margin-top:4px;">
                    Verified in ${Math.round(agent6.latency_ms || 0)} ms
                    &nbsp;·&nbsp; ${agent6.source || 'Agent6_AgeAppropriateness'}
                </div>
            </div>
            <details style="margin-top:6px; margin-bottom:10px;">
                <summary style="font-size:0.75rem; color:#64748B; cursor:pointer;
                                user-select:none; padding:4px 0; list-style:none;">
                    ▸ View age-appropriateness reasoning
                </summary>
                <div style="background:#F8FAFC; border:1px solid #E2E8F0;
                            border-radius:6px; padding:9px 11px; font-size:0.75rem;
                            color:#475569; line-height:1.5; margin-top:4px;">
                    ${agent6.reasoning || 'No reasoning available.'}
                </div>
            </details>`;
    }



    // ── Close the Trust Enforcement section wrapper ───────────────────────
    panelHTML += `</div>`;
    sidePanel.innerHTML += panelHTML;
}   

// ─────────────────────────────────────────────────────────────────────────────
// END OF NEW CODE — everything below is unchanged from the original chat.js
// ─────────────────────────────────────────────────────────────────────────────


async function sendMessage() {
    const input = document.getElementById('user-input');
    const chatPanel = document.getElementById('chat-panel');
    const sidePanel = document.getElementById('side-panel');
    const message = input.value.trim();

    if (!message) return;

    // --- Hide the welcome screen when a user types their own message ---
    const welcomeScreen = document.getElementById('welcome-screen');
    if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
    }

    // 1. Add User Message
    chatPanel.innerHTML += `<div class="msg user"><b>You:</b> ${message}</div>`;
    input.value = '';
    
    // Auto-scroll to bottom
    chatPanel.scrollTop = chatPanel.scrollHeight;

    // 2. Add Loading Indicator
    const botMsgId = 'bot-' + Date.now();
    chatPanel.innerHTML += `<div class="msg bot" id="${botMsgId}"><i>Thinking...</i></div>`;
    chatPanel.scrollTop = chatPanel.scrollHeight;

    try {
        // 3. Call the Flask Backend
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, mode: 'rag' })
        });

        const data = await response.json();
        console.log("RAW RESPONSE:", JSON.stringify(data, null, 2));
        console.log("STATUS:", data.status);
        console.log("ANSWER LENGTH:", (data.answer || "").length);
        console.log("TRUST KEYS:", Object.keys(data.trust_verdicts || {}));
        const botDiv = document.getElementById(botMsgId);

        if (data.error) {
            botDiv.innerHTML = `<b>Tutor:</b> ⚠️ ${data.error}`;
            return;
        }
        
        // --- 4. Render the Answer & Extract Links (WITH ERROR HANDLING) ---
        let formattedAnswer = data.answer || "";
        const extractedLLMLinks = []; 

        // 1. Broad Regex: Catches ANY attempt at [Text](url)
        const attemptedMarkdownRegex = /\[([^\]]+)\]\s*\(([^)]+)\)/g;
        
        formattedAnswer = formattedAnswer.replace(attemptedMarkdownRegex, function(match, text, url) {
            const cleanText = text ? text.trim() : "";
            const cleanUrl = url ? url.trim() : "";
            const isValidUrl = /^https?:\/\/[^\s]+$/.test(cleanUrl);
            const hasTitle = cleanText.length > 0;

            if (!isValidUrl || !hasTitle) {
                console.error("🚨 MALFORMED AI LINK DETECTED 🚨\nOutput:", match);
                return `<span style="color: #dc3545; font-size: 0.9em; border-bottom: 1px dotted #dc3545; cursor: help;" title="Broken URL: ${cleanUrl}">⚠️ [Broken Link: ${cleanText}]</span>`;
            }

            extractedLLMLinks.push({ isLLMLink: true, title: cleanText, url: cleanUrl }); 
            return `<a href="${cleanUrl}" target="_blank" style="color: #007bff; text-decoration: underline;">${cleanText}</a>`;
        });

        // B. Convert any remaining naked URLs
        const nakedUrlRegex = /(?<!href=")(https?:\/\/[^\s<]+)/g;
        formattedAnswer = formattedAnswer.replace(nakedUrlRegex, function(url) {
            const cleanUrl = url.trim();
            extractedLLMLinks.push({ isLLMLink: true, title: cleanUrl, url: cleanUrl });
            return `<a href="${cleanUrl}" target="_blank" style="color: #007bff; text-decoration: underline;">${cleanUrl}</a>`;
        });

        // C. Replace newlines with <br> and bold with <b> tags
        formattedAnswer = formattedAnswer.replace(/\n/g, '<br>');
        formattedAnswer = formattedAnswer.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');

        botDiv.innerHTML = `<b>Tutor:</b> ${formattedAnswer}`;

        // --- 5. Update the Sources Sidebar ---
        sidePanel.innerHTML = '<h3>📚 Sources</h3>';
        
        const rawSources = data.sources || [];
        const cleanSources = rawSources.filter(src => src && src !== "");

        // Dump extracted links into sources array
        extractedLLMLinks.forEach(linkObj => cleanSources.push(linkObj));

        // ROUTE A: General LLM Route
        if (cleanSources.length === 0) {
            sidePanel.innerHTML += `
                <div class="source-card" style="border-left: 4px solid #6c757d; background: #f8f9fa;">
                    <div style="font-size: 1.2rem; margin-bottom: 5px;">🧠</div>
                    <strong>General Knowledge</strong><br>
                    <small class="text-muted">This response is based on the AI's baseline training. No specific course documents were matched.</small>
                </div>`;
        } 
        // ROUTE B, C, & D: RAG, YouTube, or Extracted Links
        else {
            cleanSources.forEach(src => {
                let cardHTML = "";

                if (src.isLLMLink) {
                    cardHTML = `
                        <div class="source-card" style="border-left: 4px solid #17a2b8;">
                            <strong>🌐 Web Resource</strong><br>
                            <a href="${src.url}" target="_blank" style="color: #007bff; text-decoration: underline; font-size: 0.85rem;">${src.title}</a>
                        </div>`;
                } else if (typeof src === 'string') {
                    if (src.includes("youtube.com") || src.includes("youtu.be")) {
                        cardHTML = `
                            <div class="source-card" style="border-left: 4px solid #ff0000;">
                                <strong>▶️ YouTube Video</strong><br>
                                <a href="${src}" target="_blank" style="color: #007bff; text-decoration: underline; font-size: 0.85rem;">Watch Reference Video</a>
                            </div>`;
                    } else {
                        cardHTML = `
                            <div class="source-card" style="border-left: 4px solid #007bff;">
                                <strong>📄 ${src}</strong><br>
                                <small class="text-muted">Reference Document</small>
                            </div>`;
                    }
                } else if (typeof src === 'object' && !src.isLLMLink) {
                    const fileName = src.file || src.source || "Course Material";
                    const pageInfo = src.page ? `Page(s): ${src.page}` : "Reference Text";
                    
                    cardHTML = `
                        <div class="source-card" style="border-left: 4px solid #28a745;">
                            <strong>📄 ${fileName}</strong><br>
                            <small class="text-muted">${pageInfo}</small>
                        </div>`;
                }

                sidePanel.innerHTML += cardHTML;
            });
        }

        // --- 6. 🛡️ Render Trust Verdict Panel (Layer III — Agent 1 + 4 + 5) ---
        // Single call — renderTrustPanel renders all three agent cards below Sources.
        // Agent 5 (Safety) always shown. Agent 1 skipped on non-RAG routes.
        // Agent 4 (Bias) always shown when governance profile available.
        renderTrustPanel(sidePanel, data.trust_verdicts, data.status);

        // 7. Tell MathJax to render formulas
        if (window.MathJax) {
            MathJax.typesetPromise([chatPanel]).catch(function (err) {
                console.error('MathJax error:', err.message);
            });
        }

        chatPanel.scrollTop = chatPanel.scrollHeight;

    } catch (error) {
        document.getElementById(botMsgId).innerHTML = "<b>Tutor:</b> ⚠️ Network error. Please check your backend terminal.";
        console.error("Fetch error:", error);
    }
}