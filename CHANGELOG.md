# Project Evolution Log

## 2026-04-03 — Session 1: Initial Build

### Starting Point
`jumpstart.py` was a minimal proof-of-concept: three hardcoded roles (Software Engineer, UX Designer, Project Manager) making parallel Claude API calls, with a synthesis pass at the end. No UI, no context files, no key management.

### What We Built

**API & Key Management**
- Created `.env` for storing `ANTHROPIC_API_KEY` securely
- Created `.env.example` as a safe committed placeholder
- Added `override=True` to `load_dotenv()` calls to prevent stale system environment variables from overriding the `.env` file
- Diagnosed and resolved a 401 authentication error caused by a Windows system-level environment variable shadowing the correct key

**Context Document System**
- Established `persona_context/` directory to hold per-role reference documents
- Built context documents for Vermont state agencies, loaded at startup and injected into each role's system prompt
- Principle: *you bring the web to the model — it can't go get it itself*

**Web Fetching (Approach 3)**
- Added `requests` + `beautifulsoup4` to strip live web pages to readable text
- Implemented `fetch_url()` to remove script/style/nav/footer tags and cap output at ~8,000 characters to control token costs
- Added optional URL input field to the UI — one URL per line, all fetched and appended to each agent's user message

**Streamlit UI (`app.py`)**
- Built interactive web interface replacing the terminal-only `jumpstart.py`
- Problem statement entered via text area
- Optional reference URL input
- Per-role response columns
- Synthesis section below

---

## 2026-04-03 — Session 1 (continued): ORCA Pivot

### Decision
Reoriented the tool from a generic multi-role analyzer to a purpose-built reviewer for **ORCA (Open Research Community Accelerator) student internship projects** at UVM.

### Problem with Original Roles
The original three agencies (Digital Services, ACCD, ANR) were chosen for general Vermont government coverage. For student research projects:
- **ADS** was rarely relevant at the student project scope
- **ACCD** was hit-or-miss — useful for community projects, weak for research
- Neither role addressed the most common student failure modes: IRB compliance, study design flaws, and scope problems

### New Role Set

| Role | What It Replaced | Why |
|---|---|---|
| **Research Methodologist** | Software Engineer | The most important reviewer for student work — flags IRB, design flaws, feasibility, scope creep before they become fatal |
| **VT Dept of Health (VDH)** | ADS | Human subjects protection, HIPAA, health data access agreements, health equity |
| **VT Agency of Agriculture, Food & Markets (AAFM)** | ACCD | Vermont's dominant industry — water quality/ag nexus, Required Agricultural Practices, farm engagement realities |
| **VT ANR / DEC** | (kept) | Environmental permitting, Act 250, water quality, climate resilience — remained highly relevant |

### Context Documents Created
- `research_methodologist_context.md` — IRB categories, study design framework, ORCA-specific pitfalls, 8 questions every student should answer
- `vt_health_context.md` — VDH divisions, HIPAA, data use agreements, human subjects common mistakes
- `vt_agriculture_context.md` — AAFM structure, Required Agricultural Practices, Vermont farm landscape, water quality nexus
- `vt_anr_context.md` — already existed, retained as-is

### Synthesis Restructure
Replaced the generic "where do they agree/conflict" synthesis with a structured five-section output designed for student action:
1. **Critical Issues to Resolve Before Starting** — blockers
2. **Compliance Steps Required** — specific regulatory/IRB/institutional steps
3. **Key Risks to Manage** — non-blocking but project-threatening issues
4. **Domain Knowledge Gaps** — what the student needs to learn
5. **Questions to Bring to Your Faculty Advisor** — 5–8 specific questions

### UX Changes
- Individual reviewer panels collapsed by default — synthesis leads the page
- Prompt language rewritten for a student audience
- Placeholder text in the problem input guides students to include: what they want to study, how they'll collect data, who their subjects/partners are, and what their deliverable is

---

## Design Principles Established

- **Context documents are the quality lever.** The model's output is only as good as the reference material in the system prompt. Invest in these files.
- **Synthesis is the product.** Individual reviewer panels are useful for debugging but the structured summary is what students need.
- **Scope roles to the audience.** Generic roles produce generic output. The more specifically the role is tuned to the actual use case (student intern, ORCA program, Vermont context), the more actionable the feedback.
- **Keep context documents under ~8,000 tokens each.** Beyond that, cost and latency increase without proportional quality gain. Use retrieval approaches for larger reference corpora.
- **One URL per fetch, capped at 8,000 chars.** Sites that block bots return a graceful error rather than crashing.

---

## 2026-04-03 — Session 1 (continued): DEC Split and Token Optimization

### DEC Split from ANR
ANR was carrying two distinct functions: (1) regulatory permitting, water quality, and environmental compliance (DEC), and (2) wildlife, habitat, forests, and recreation (Fish & Wildlife / FPR). These were split into separate roles because:
- DEC triggers are permit-specific and highly actionable — Act 250, stormwater, wetland, wastewater
- ANR's Fish & Wildlife / FPR lens is ecological and stewardship-focused, not regulatory
- Combining them produced unfocused output; splitting sharpens both

**Added:** `vt_dec_context.md` — permit types and timelines, Act 250, Clean Water Act, PFAS tracker, key data resources (ANR Atlas, Environmental Data Explorer)

**ANR role narrowed** to: Fish & Wildlife, forests, biodiversity, Vermont Conservation Design, Natural Heritage Inventory, environmental justice.

Result: 5 reviewer roles total.

### Token and Cost Optimization
- Trimmed `vt_digital_services_context.md` from ~1,300 lines to ~70 — removed the full NIST security policy, DocuSign metadata, and A–Z citizen services directory. Retained mission, leadership, guiding principles, EPMO, key security policy points, evaluation lens, and pain points.
- Reduced reviewer `max_tokens` from 1,000 to 700 — sufficient for focused role feedback
- Switched reviewer default model from Sonnet to Haiku — ~20× cheaper, adequate for flagging issues from structured context documents
- Kept synthesis on Sonnet — reasoning depth matters there
- Estimated cost per run: ~$0.02–0.03 at default settings vs. ~$0.08 previously

### Prompt Refinement
- Synced `jumpstart.py` roles to match `app.py` — was out of date with old ADS/ACCD/ANR set
- Fixed stray `lso` syntax error in `jumpstart.py` that caused crash on run
- Updated test problem in `jumpstart.py` to a realistic ORCA scenario (phosphorus runoff / dairy farm study)
- Added model selection sidebar to `app.py` — Haiku / Sonnet / Opus selectable independently for reviewers and synthesis

---

## 2026-04-03 — Session 1 (continued): Dual-Mode Implementation

### Decision
Two distinct use cases emerged for the same tool:
1. **Student mode** — ORCA interns submitting project outlines for structured feedback
2. **Advisor mode** — Faculty, program managers, and grant reviewers analyzing proposals critically

These audiences need fundamentally different outputs. A student needs to understand what IRB means and what to do next. An advisor already knows — they need conflicts, regulatory exposure, and strategic gaps identified quickly.

### Implementation
Each role now carries **two system prompt variants** — `student` and `advisor` — loading the same context document but with different tone, instruction, and framing:

| Dimension | Student prompts | Advisor prompts |
|---|---|---|
| Tone | Explain concepts, flag what they may not know | Direct, skip basics, assume domain fluency |
| IRB/compliance | Explain what it means and what to do | Cite statute, estimate timeline, flag classification risk |
| Ecological/ag concepts | Define terms (what is a WMA, what are RAPs) | Reference specific programs and frameworks by name |
| Scope | Flag if project is too ambitious for 10–12 weeks | Flag strategic misalignment and resource assumptions |

### Synthesis restructured by mode

**Student synthesis:**
1. Critical Issues to Resolve Before Starting
2. Compliance Steps Required
3. Key Risks to Manage
4. Domain Knowledge Gaps
5. Questions to Bring to Your Faculty Advisor

**Advisor synthesis:**
1. Where Reviewers Agree
2. Key Conflicts and Tensions
3. Regulatory and Compliance Exposure
4. Strategic Gaps and Blind Spots
5. Recommended Next Steps

### Model defaults by mode
- Student: Haiku reviewers / Sonnet synthesis
- Advisor: Sonnet reviewers / Sonnet synthesis
- Both overridable in the sidebar

### UX
- Mode toggle added to sidebar as a radio button — switches title, caption, input labels, button text, user message framing, and synthesis structure
- Page title changes: Student → "ORCA Student Research Project Reviewer" / Advisor → "Vermont Agency Proposal Analyzer"

---

## Design Principles Established

- **Context documents are the quality lever.** The model's output is only as good as the reference material in the system prompt. Invest in these files.
- **Synthesis is the product.** Individual reviewer panels are useful for debugging but the structured summary is what users need.
- **Scope roles to the audience.** Generic roles produce generic output. The more specifically the role is tuned to the actual use case, the more actionable the feedback.
- **Two prompt variants per role, one context file.** Student and advisor tones diverge significantly — maintain them separately but share the same underlying reference document.
- **Keep context documents under ~8,000 tokens each.** Beyond that, cost and latency increase without proportional quality gain.
- **One URL per fetch, capped at 8,000 chars.** Sites that block bots return a graceful error rather than crashing.
- **Default cheap, allow expensive.** Haiku is the right default for reviewer roles. Let users escalate to Sonnet/Opus when the stakes warrant it.

---

## 2026-04-03 — Session 1 (continued): Selectable Reviewers

### Decision
Not every project is relevant to every reviewer. A purely methodological proposal doesn't need ANR or AAFM. A water quality project may not need VDH. Running all five reviewers every time adds cost and noise.

### Implementation
- Added a **reviewer checkbox panel** to the right of the input fields — all five checked by default
- Analysis only runs the selected reviewers — columns in the results panel adjust automatically
- Run button disables if no reviewers are selected
- Synthesis receives only the feedback from active reviewers — no empty columns or placeholder text

### Effect
Users can now tailor each run to the project type, reducing cost and improving signal-to-noise in the synthesis.

---

## Open Questions / Future Directions

- [ ] Should roles be dynamically selected based on project type? (e.g., health project auto-routes to VDH, farm project auto-routes to AAFM)
- [ ] Would a follow-up "ask a question" interface after the review be useful for students?
- [ ] Are there additional Vermont agencies worth adding? (e.g., VT Agency of Transportation, VT Housing & Conservation Board)
- [ ] Should the WWTP Operator role be preserved for infrastructure/water systems projects?
- [ ] Prompt caching — context documents don't change between runs; caching could reduce costs ~90% on repeated use
