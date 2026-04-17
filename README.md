# Vermont Research Reviewer

A dual-mode multi-agent review tool built on the Anthropic Claude API. Submit a research proposal or project outline and receive structured feedback from expert reviewers simultaneously, synthesized into an actionable summary.

Two audiences, one tool:
- **Student mode** — scaffolded feedback for ORCA student interns at UVM
- **Advisor mode** — direct critical analysis for faculty, program managers, and grant reviewers

---

## What It Does

Each analysis runs one parallel Claude API call per selected reviewer role, each grounded in an agency or program reference document. A final synthesis call consolidates the feedback into a structured summary tuned to the selected mode.

### Reviewer Roles

| Reviewer | Focus |
|---|---|
| **Research Methodologist** | Study design, IRB requirements, scope feasibility, data collection validity |
| **VT Dept of Environmental Conservation (DEC)** | Act 250, stormwater/wetland/wastewater permits, water quality, groundwater, PFAS |
| **VT Agency of Natural Resources (ANR)** | Wildlife habitat, biodiversity, rare species, forest ecology, environmental justice |
| **VT Dept of Health (VDH)** | Human subjects, HIPAA, health data access, health equity |
| **VT Agency of Agriculture, Food & Markets (AAFM)** | Required Agricultural Practices, farm engagement, water/ag nexus, food safety |
| **NSF Program Officer** | Intellectual Merit, Broader Impacts, data management, EPSCoR, budget compliance |
| **NIH Program Officer** | Review criteria, human subjects, rigor/reproducibility, Vermont health data risks |
| **UVM IRB Specialist** | IRB classification, CITI training, consent, HIPAA/FERPA, data security |
| **UVM Sponsored Research Officer** | OSP sign-off, F&A rates, Uniform Guidance, export control, subawards |

Each role has two system prompt variants — same context document, different tone and framing depending on mode.

Reviewers are individually selectable via checkboxes — none are selected by default. Select at least one to run an analysis.

### Synthesis Output

**Student mode** produces:
1. Critical Issues to Resolve Before Starting
2. Compliance Steps Required
3. Key Risks to Manage
4. Domain Knowledge Gaps
5. Questions to Bring to Your Faculty Advisor

**Advisor mode** produces:
1. Where Reviewers Agree
2. Key Conflicts and Tensions
3. Regulatory and Compliance Exposure
4. Strategic Gaps and Blind Spots
5. Recommended Next Steps

---

## Project Structure

```
agentic-team/
├── app.py                        # Streamlit web UI (main entry point)
├── requirements.txt
├── .env                          # Your API key (never commit this)
├── .env.example                  # Safe committed placeholder
├── CHANGELOG.md                  # Design evolution log
├── persona_context/
│   ├── research_methodologist_context.md
│   ├── vt_dec_context.md
│   ├── vt_anr_context.md
│   ├── vt_health_context.md
│   ├── vt_agriculture_context.md
│   ├── nsf_program_officer_context.md
│   ├── nih_program_officer_context.md
│   ├── uvm_irb_context.md
│   └── uvm_sponsored_research_context.md
```

---

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd agentic-team
pip install -r requirements.txt
```

### 2. Get your Anthropic API key

- Go to [console.anthropic.com](https://console.anthropic.com)
- Navigate to **Settings → API Keys → Create Key**
- Add at least $5 in credits under **Settings → Billing**

### 3. Configure your key

Copy `.env.example` to `.env` and add your key:

```bash
cp .env.example .env
```

Edit `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Never commit `.env` — it is listed in `.gitignore`.

### 4. Run the web UI

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Mode Selection

The sidebar toggle switches between two modes:

| Mode | Audience | Reviewer tone | Synthesis structure |
|---|---|---|---|
| **Student** | ORCA interns | Explains concepts, flags unknowns | Blockers → compliance → risks → gaps → advisor questions |
| **Advisor** | Faculty, program managers, grant reviewers | Direct, assumes domain fluency | Agreement → conflicts → compliance exposure → blind spots → next steps |

Model defaults change automatically with mode but can be overridden.

---

## Model Selection

| Option | Model | Best for |
|---|---|---|
| Haiku (fast, low cost) | `claude-haiku-4-5-20251001` | Development, student mode |
| Sonnet (balanced) | `claude-sonnet-4-6` | Default production use |
| Opus (most capable) | `claude-opus-4-7` | High-stakes proposals |

**Student mode defaults:** Haiku for reviewers, Sonnet for synthesis.
**Advisor mode defaults:** Sonnet for reviewers, Sonnet for synthesis.

**Estimated cost per analysis:** ~$0.02–0.10 depending on mode, model, and input length.

---

## Adding or Updating Context Documents

Each reviewer role loads a markdown reference file from `persona_context/`. To improve reviewer quality:

1. Edit the relevant `.md` file in `persona_context/`
2. Add specific local knowledge: permit numbers, agency contacts, program names, known constraints
3. Keep files under ~8,000 tokens for best cost/performance ratio

To add a new reviewer role:
1. Create a new context file in `persona_context/`
2. Add an entry to the `ROLES` dict in `app.py` — include both `student` and `advisor` prompt variants
3. The UI will automatically render a checkbox for the new reviewer

---

## Web Fetching

The UI accepts optional reference URLs (one per line). Each URL is fetched at run time, stripped of navigation/scripts, and appended to every reviewer's user message. Capped at 8,000 characters per URL. Sites that block automated access return a graceful error rather than crashing.

---

## Security

- API key is stored in `.env` and loaded with `override=True` to prevent Windows system environment variables from shadowing it
- `.env` is gitignored — never commit it
- No user data is stored or logged by this application
- All API calls go directly to Anthropic — no third-party services
