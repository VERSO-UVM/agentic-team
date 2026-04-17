import os
import datetime
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
    "Opus (most capable)": "claude-opus-4-7",
}

# Default models per mode
MODE_DEFAULTS = {
    "Student": {"reviewer": 0, "synthesis": 1},   # Haiku / Sonnet
    "Advisor": {"reviewer": 1, "synthesis": 1},   # Sonnet / Sonnet
}


def build_download_text(mode, problem, url_input, responses, synthesis_text,
                        reviewer_model, synthesis_model):
    divider = "=" * 70
    thin = "-" * 70
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        divider,
        f"  VERMONT RESEARCH REVIEWER — {mode.upper()} MODE",
        f"  Generated: {now}",
        f"  Reviewer model: {reviewer_model}  |  Synthesis model: {synthesis_model}",
        divider,
        "",
        "PROPOSAL / PROJECT DESCRIPTION",
        thin,
        problem.strip(),
    ]
    if url_input and url_input.strip():
        lines += ["", "REFERENCE URLS", thin, url_input.strip()]
    lines += ["", "", divider, "INDIVIDUAL REVIEWER FEEDBACK", divider]
    for role, text in responses.items():
        lines += ["", role.upper(), thin, text.strip(), ""]
    lines += [divider, "SYNTHESIS", divider, "", synthesis_text.strip(), ""]
    return "\n".join(lines)


def load_context(*filenames):
    """Load one or more context files and join them."""
    parts = []
    for filename in filenames:
        path = os.path.join(CONTEXT_DIR, filename)
        with open(path, encoding="utf-8", errors="replace") as f:
            parts.append(f.read())
    return "\n\n---\n\n".join(parts)


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
    "NSF Program Officer": {
        "context": load_context("nsf_program_officer_context.md"),
        "student": (
            "You are an NSF Program Officer reviewing a student's "
            "research project proposal. Evaluate whether it has the "
            "potential to meet NSF's two core review criteria: "
            "Intellectual Merit and Broader Impacts. Explain what those "
            "mean in plain language. Flag missing elements — data "
            "management plan, IRB requirements, scope issues. Help the "
            "student understand what makes NSF-worthy research and "
            "where this proposal falls short or shows promise.\n\n"
            "Reference:\n\n"
            + load_context("nsf_program_officer_context.md")
        ),
        "advisor": (
            "You are an NSF Program Officer conducting a critical "
            "pre-submission review of a proposal. Assess Intellectual "
            "Merit and Broader Impacts rigorously. Flag weaknesses a "
            "review panel will penalize: underdeveloped Broader Impacts, "
            "scope mismatch, weak preliminary data, missing data "
            "management plan, budget compliance issues, or F&A concerns. "
            "Note any EPSCoR positioning opportunities. Assume the "
            "reader understands the NSF merit review process.\n\n"
            "Reference:\n\n"
            + load_context("nsf_program_officer_context.md")
        ),
    },
    "NIH Program Officer": {
        "context": load_context("nih_program_officer_context.md"),
        "student": (
            "You are an NIH Program Officer reviewing a student research "
            "proposal. Evaluate it against NIH's five core review "
            "criteria: Significance, Investigators, Innovation, "
            "Approach, and Environment. Explain what each criterion "
            "means in practice. Flag human subjects requirements, data "
            "sharing obligations, and rigor/reproducibility gaps. Help "
            "the student understand what NIH-funded research looks like "
            "and what they would need to address.\n\n"
            "Reference:\n\n"
            + load_context("nih_program_officer_context.md")
        ),
        "advisor": (
            "You are an NIH Program Officer conducting a critical "
            "pre-submission review. Assess all five review criteria and "
            "flag fatal weaknesses: approach lacks rigor or contingency "
            "plans, human subjects section is incomplete, data sharing "
            "plan missing or insufficient, team lacks key expertise, "
            "scope exceeds budget. Note relevant IC alignment and any "
            "Vermont-specific re-identification risks in health data. "
            "Assume the reader understands NIH peer review.\n\n"
            "Reference:\n\n"
            + load_context("nih_program_officer_context.md")
        ),
    },
    "UVM IRB Specialist": {
        "context": load_context("uvm_irb_context.md", "uvm_irb_supplement.md"),
        "student": (
            "You are a UVM IRB compliance specialist. Evaluate this "
            "student research proposal for human subjects requirements. "
            "Determine whether IRB review is required, and if so, what "
            "level (exempt, expedited, or full board). Explain what IRB "
            "is and why it exists. Walk the student through what they "
            "would need to submit through UVMClick — CITI training, "
            "consent forms, protocol — and how long it takes. Flag HIPAA "
            "and FERPA issues if the proposal involves health or student "
            "data. Reference the Top 10 obstacles when relevant.\n\n"
            "Reference:\n\n"
            + load_context("uvm_irb_context.md", "uvm_irb_supplement.md")
        ),
        "advisor": (
            "You are a senior UVM IRB compliance officer reviewing a "
            "proposal. Determine IRB classification under the 7 approval "
            "criteria (45 CFR 46.111) and flag risk factors: sensitive "
            "populations, re-identification risk in Vermont's small "
            "population, HIPAA applicability, FERPA intersections, "
            "secondary data use, and community-based research "
            "complexities. Flag UVMClick submission requirements, "
            "regulatory binder obligations, and any DUA or MTA needs. "
            "Identify if Single IRB reliance agreements are needed. "
            "Assume reader knows research regulations.\n\n"
            "Reference:\n\n"
            + load_context("uvm_irb_context.md", "uvm_irb_supplement.md")
        ),
    },
    "UVM Sponsored Research Officer": {
        "context": load_context("uvm_sponsored_research_context.md"),
        "student": (
            "You are a UVM Office of Sponsored Programs (OSP) officer. "
            "Review this student research proposal from the perspective "
            "of institutional compliance and grant administration. "
            "Explain what OSP does and why institutional sign-off "
            "matters. Flag budget issues, indirect cost requirements, "
            "conflict of interest disclosure needs, and any export "
            "control concerns. Help the student understand the "
            "administrative steps required before a proposal can go out "
            "the door.\n\n"
            "Reference:\n\n"
            + load_context("uvm_sponsored_research_context.md")
        ),
        "advisor": (
            "You are a senior UVM Sponsored Research officer reviewing "
            "a proposal for institutional compliance. Flag: budget "
            "allowability and allocability issues under 2 CFR 200, F&A "
            "rate application, unauthorized cost sharing, export control "
            "triggers, conflict of interest disclosure gaps, subaward "
            "compliance, and any effort commitment concerns. Note if "
            "USDA land-grant or EPSCoR rules apply. Assume the reader "
            "understands sponsored research administration.\n\n"
            "Reference:\n\n"
            + load_context("uvm_sponsored_research_context.md")
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

    st.markdown("---")
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
    st.caption("Select at least one reviewer to run.")
    selected_roles = {}
    for role in ROLES:
        selected_roles[role] = st.checkbox(role, value=False)

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
                        system=[{
                            "type": "text",
                            "text": role_data[prompt_key],
                            "cache_control": {"type": "ephemeral"},
                        }],
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
        synthesis_text = final.content[0].text
        st.markdown(synthesis_text)

    st.markdown("---")
    filename = (
        f"research_review_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    )
    download_text = build_download_text(
        mode=mode,
        problem=problem,
        url_input=url_input,
        responses=responses,
        synthesis_text=synthesis_text,
        reviewer_model=REVIEWER_MODEL,
        synthesis_model=SYNTHESIS_MODEL,
    )
    st.download_button(
        label="Download Review (.txt)",
        data=download_text,
        file_name=filename,
        mime="text/plain",
    )
