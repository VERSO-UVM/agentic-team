import os
import anthropic
import requests
import streamlit as st
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(
    dotenv_path=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".env"
    ),
    override=True,
)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CONTEXT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "persona_context"
)

MODEL_OPTIONS = {
    "Haiku (fast, low cost)": "claude-haiku-4-5-20251001",
    "Sonnet (balanced)": "claude-sonnet-4-6",
    "Opus (most capable)": "claude-opus-4-6",
}

# Default models per mode
MODE_DEFAULTS = {
    "Student": {"reviewer": 0, "synthesis": 1},   # Haiku / Sonnet
    "Advisor": {"reviewer": 1, "synthesis": 1},   # Sonnet / Sonnet
}


def load_context(filename):
    path = os.path.join(CONTEXT_DIR, filename)
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def fetch_url(url):
    try:
        r = requests.get(
            url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:8000]
    except Exception as e:
        return f"[Could not fetch {url}: {e}]"


# --- Role definitions ---
# Each role has two system prompt variants: student-facing and advisor-facing.
# Student: scaffolded, explains what things mean, flags things student may not know
# Advisor: direct, critical, assumes domain fluency, focuses on strategic gaps

ROLES = {
    "Research Methodologist": {
        "context": load_context("research_methodologist_context.md"),
        "student": (
            "You are an experienced research methodologist reviewing a "
            "student intern's project proposal. Evaluate whether the "
            "research design is rigorous, ethical, and feasible within "
            "a 10-12 week ORCA internship. Be direct and specific. "
            "Flag IRB requirements, scope problems, data access issues, "
            "and design weaknesses. Explain what IRB means and why it "
            "matters if it's relevant — the student may not know.\n\n"
            "Reference:\n\n"
            + load_context("research_methodologist_context.md")
        ),
        "advisor": (
            "You are a senior research methodologist conducting a "
            "critical peer review of a proposal. Assume the reader has "
            "domain expertise. Focus on: internal and external validity "
            "threats, sampling adequacy, IRB classification risk, "
            "measurement validity, and whether the scope matches the "
            "resources. Be blunt about fatal flaws. Skip basics.\n\n"
            "Reference:\n\n"
            + load_context("research_methodologist_context.md")
        ),
    },
    "VT Dept of Environmental Conservation": {
        "context": load_context("vt_dec_context.md"),
        "student": (
            "You are a staff member at the Vermont Department of "
            "Environmental Conservation (DEC). Evaluate the proposal "
            "through the lens of permitting, water quality, stormwater, "
            "wetlands, wastewater, groundwater, and air quality. Flag "
            "permit triggers and explain what each permit involves and "
            "how long it typically takes — the student may not know "
            "what Act 250 or a wetland permit means in practice.\n\n"
            "Reference:\n\n"
            + load_context("vt_dec_context.md")
        ),
        "advisor": (
            "You are a senior DEC staff member reviewing a proposal for "
            "regulatory and compliance risk. Identify specific permit "
            "triggers (Act 250, stormwater, wetland, stream alteration, "
            "wastewater), cite the relevant statute or rule, estimate "
            "realistic timelines, and flag any PFAS or groundwater "
            "contamination context that could confound the work. "
            "Assume the reader knows Vermont environmental law.\n\n"
            "Reference:\n\n"
            + load_context("vt_dec_context.md")
        ),
    },
    "VT Agency of Natural Resources": {
        "context": load_context("vt_anr_context.md"),
        "student": (
            "You are a staff member at the Vermont Agency of Natural "
            "Resources (ANR), focused on Fish & Wildlife and Forests, "
            "Parks and Recreation. Evaluate the proposal through the "
            "lens of wildlife habitat, biodiversity, rare and endangered "
            "species, forest ecology, and environmental justice. Explain "
            "any ecological concepts the student should understand — "
            "e.g., what a Wildlife Management Area is, or why habitat "
            "fragmentation matters.\n\n"
            "Reference:\n\n"
            + load_context("vt_anr_context.md")
        ),
        "advisor": (
            "You are a senior ANR ecologist reviewing a proposal. "
            "Focus on habitat and biodiversity risks, Vermont Natural "
            "Heritage Inventory implications, Wildlife Action Plan "
            "alignment, cumulative landscape impacts, and stewardship "
            "obligations. Flag anything that intersects with the Vermont "
            "Conservation Design framework or old forest priorities. "
            "Be specific and cite relevant ANR programs.\n\n"
            "Reference:\n\n"
            + load_context("vt_anr_context.md")
        ),
    },
    "VT Dept of Health": {
        "context": load_context("vt_health_context.md"),
        "student": (
            "You are a staff member at the Vermont Department of Health "
            "(VDH). Evaluate the proposal through the lens of public "
            "health, human subjects protection, HIPAA, health data "
            "access, and health equity. If IRB or HIPAA applies, "
            "explain what that means practically for a student — "
            "what they need to do, in what order, and how long it "
            "takes.\n\n"
            "Reference:\n\n"
            + load_context("vt_health_context.md")
        ),
        "advisor": (
            "You are a senior VDH epidemiologist and compliance officer "
            "reviewing a proposal. Focus on: IRB classification and "
            "risk level, HIPAA applicability, data use agreement "
            "requirements for VDH/VHDO datasets, de-identification "
            "adequacy given Vermont's small population, and health "
            "equity implications. Flag any 42 CFR Part 2 issues for "
            "substance use data. Assume reader knows research ethics.\n\n"
            "Reference:\n\n"
            + load_context("vt_health_context.md")
        ),
    },
    "VT Agency of Agriculture": {
        "context": load_context("vt_agriculture_context.md"),
        "student": (
            "You are a staff member at the Vermont Agency of Agriculture, "
            "Food & Markets (AAFM). Evaluate the proposal through the "
            "lens of Vermont's agricultural systems, Required "
            "Agricultural Practices, water quality, farm economics, and "
            "food safety. Explain Vermont-specific context the student "
            "may not have — e.g., what RAPs are, why dairy farm "
            "engagement is difficult, what USDA cost-share programs "
            "exist.\n\n"
            "Reference:\n\n"
            + load_context("vt_agriculture_context.md")
        ),
        "advisor": (
            "You are a senior AAFM agronomist reviewing a proposal. "
            "Focus on: RAP compliance implications, data confidentiality "
            "under Vermont agricultural statutes, USDA program alignment "
            "(EQIP, CSP, FSA), phosphorus loading methodology, and "
            "practical constraints of working with Vermont dairy "
            "operations. Flag economic feasibility assumptions. "
            "Assume reader understands Vermont ag policy.\n\n"
            "Reference:\n\n"
            + load_context("vt_agriculture_context.md")
        ),
    },
}

# --- Page layout ---

st.set_page_config(page_title="Vermont Research Reviewer", layout="wide")

with st.sidebar:
    st.header("Mode")
    mode = st.radio(
        "Who is this for?",
        ["Student", "Advisor"],
        index=0,
        help=(
            "Student: scaffolded feedback for ORCA interns. "
            "Advisor: direct critical analysis for proposal review."
        ),
    )

    st.divider()
    st.header("Model Settings")
    model_keys = list(MODEL_OPTIONS.keys())
    reviewer_label = st.selectbox(
        "Reviewer model",
        model_keys,
        index=MODE_DEFAULTS[mode]["reviewer"],
        help="Used for each of the five expert reviewers.",
    )
    synthesis_label = st.selectbox(
        "Synthesis model",
        model_keys,
        index=MODE_DEFAULTS[mode]["synthesis"],
        help="Used for the final summary.",
    )
    REVIEWER_MODEL = MODEL_OPTIONS[reviewer_label]
    SYNTHESIS_MODEL = MODEL_OPTIONS[synthesis_label]
    st.caption(f"Reviewer: `{REVIEWER_MODEL}`")
    st.caption(f"Synthesis: `{SYNTHESIS_MODEL}`")

# --- Mode-specific UI ---

if mode == "Student":
    st.title("ORCA Student Research Project Reviewer")
    st.caption(
        "Paste your project outline below. Five expert reviewers will "
        "analyze it in parallel, then a facilitator synthesizes the key "
        "risks, compliance steps, and questions to bring to your advisor."
    )
    input_label = "Describe your research project or proposal:"
    input_placeholder = (
        "Include: what you want to study, how you plan to collect data, "
        "who your subjects or partners are, and what your deliverable is. "
        "The more detail you provide, the more useful the feedback."
    )
    button_label = "Review My Project"
    prompt_key = "student"

else:
    st.title("Vermont Agency Proposal Analyzer")
    st.caption(
        "Paste a proposal, grant, or document below — or provide URLs. "
        "Five Vermont agency reviewers will assess it in parallel. "
        "The synthesis flags strategic risks, conflicts, and gaps."
    )
    input_label = "Paste proposal text or describe what you want analyzed:"
    input_placeholder = (
        "Paste the full proposal text, an executive summary, or a "
        "description of the initiative. You can also provide URLs below."
    )
    button_label = "Analyze Proposal"
    prompt_key = "advisor"

col_input, col_reviewers = st.columns([2, 1])

with col_input:
    problem = st.text_area(
        input_label, height=180, placeholder=input_placeholder
    )
    url_input = st.text_area(
        "Reference URLs (optional — one per line):",
        height=80,
        placeholder="Paste links to proposals, program pages, datasets, or docs.",
    )

with col_reviewers:
    st.markdown("**Select Reviewers**")
    selected_roles = {}
    for role in ROLES:
        selected_roles[role] = st.checkbox(role, value=True)

active_roles = {r: v for r, v in ROLES.items() if selected_roles[r]}

if st.button(
    button_label,
    disabled=not problem.strip() or not any(selected_roles.values()),
):

    fetched_content = ""
    urls = [u.strip() for u in url_input.splitlines() if u.strip()]
    if urls:
        with st.spinner(f"Fetching {len(urls)} URL(s)..."):
            for url in urls:
                fetched_content += (
                    f"\n\n--- Content from {url} ---\n{fetch_url(url)}"
                )

    if mode == "Student":
        user_message = (
            "Please review this ORCA student research project proposal "
            "from your expert perspective. Be specific and actionable. "
            "Flag risks the student may not be aware of, and explain "
            "any technical or regulatory concepts they need to "
            "understand.\n\n"
            f"PROJECT PROPOSAL:\n{problem}"
        )
    else:
        user_message = (
            "Please conduct a critical expert review of this proposal "
            "from your agency's perspective. Be direct. Identify "
            "regulatory risks, strategic gaps, conflicting assumptions, "
            "and anything that would trigger your agency's involvement "
            "or approval. Assume the reader is a program manager or "
            "faculty advisor who knows the domain.\n\n"
            f"PROPOSAL:\n{problem}"
        )

    if fetched_content:
        user_message += f"\n\nREFERENCE MATERIAL:\n{fetched_content}"

    responses = {}

    with st.expander("Individual Reviewer Feedback", expanded=False):
        cols = st.columns(len(active_roles))
        for col, (role, role_data) in zip(cols, active_roles.items()):
            with col:
                st.markdown(f"**{role}**")
                with st.spinner(f"Consulting {role}..."):
                    response = client.messages.create(
                        model=REVIEWER_MODEL,
                        max_tokens=700,
                        system=role_data[prompt_key],
                        messages=[
                            {"role": "user", "content": user_message}
                        ],
                    )
                    text = response.content[0].text
                    responses[role] = text
                    st.markdown(text)

    if mode == "Student":
        st.subheader("Project Review Summary")
        synthesis_prompt = (
            "You are a research coordinator helping a student intern "
            "understand feedback on their ORCA project proposal. Five "
            "expert reviewers have assessed the proposal. Synthesize "
            "their feedback into a clear, actionable summary the student "
            "can immediately use.\n\n"
            "Structure your response exactly as follows:\n\n"
            "## Critical Issues to Resolve Before Starting\n"
            "List any blockers — IRB approval, missing permits, data "
            "access agreements, fundamental design flaws.\n\n"
            "## Compliance Steps Required\n"
            "List specific regulatory, ethical, or institutional steps "
            "with enough detail that the student knows what to do next.\n\n"
            "## Key Risks to Manage\n"
            "Risks that won't stop the project but could derail it.\n\n"
            "## Domain Knowledge Gaps\n"
            "Specific concepts, regulations, or systems the student "
            "needs to learn before or during the project.\n\n"
            "## Questions to Bring to Your Faculty Advisor\n"
            "List 5-8 specific questions to ask before finalizing the "
            "project plan.\n\n"
            "---\n\nReviewer feedback:\n\n"
            + "\n\n".join(
                f"{role.upper()}:\n{text}"
                for role, text in responses.items()
            )
        )
    else:
        st.subheader("Analysis Summary")
        synthesis_prompt = (
            "You are a senior policy analyst synthesizing expert agency "
            "feedback on a proposal. Five Vermont agency reviewers have "
            "assessed it. Produce a direct, senior-level summary.\n\n"
            "Structure your response exactly as follows:\n\n"
            "## Where Reviewers Agree\n"
            "Shared concerns or endorsements across multiple agencies.\n\n"
            "## Key Conflicts and Tensions\n"
            "Where agency perspectives diverge or create competing "
            "requirements — be specific about the nature of the tension.\n\n"
            "## Regulatory and Compliance Exposure\n"
            "Specific permits, approvals, or compliance obligations "
            "triggered by this proposal, with owning agency and "
            "estimated timeline.\n\n"
            "## Strategic Gaps and Blind Spots\n"
            "What the proposal is not accounting for that it should be.\n\n"
            "## Recommended Next Steps\n"
            "Ordered list of actions — what needs to happen first, "
            "second, and third to move this proposal forward responsibly.\n\n"
            "---\n\nReviewer feedback:\n\n"
            + "\n\n".join(
                f"{role.upper()}:\n{text}"
                for role, text in responses.items()
            )
        )

    with st.spinner("Synthesizing reviewer feedback..."):
        final = client.messages.create(
            model=SYNTHESIS_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": synthesis_prompt}],
        )
        st.markdown(final.content[0].text)
