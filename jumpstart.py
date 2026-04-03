import os
import anthropic
from dotenv import load_dotenv

load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__), ".env"),
    override=True,
)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CONTEXT_DIR = os.path.join(os.path.dirname(__file__), "persona_context")


def load_context(filename):
    path = os.path.join(CONTEXT_DIR, filename)
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


roles = {
    "Research Methodologist": (
        "You are an experienced research methodologist reviewing a "
        "student intern's project proposal. Evaluate whether the "
        "research design is rigorous, ethical, and feasible within a "
        "10-12 week ORCA internship. Flag IRB requirements, scope "
        "problems, data access issues, and design weaknesses. Be "
        "direct — a student finding a fatal flaw now is far better "
        "than discovering it mid-project.\n\n"
        "Reference:\n\n"
        + load_context("research_methodologist_context.md")
    ),
    "VT Dept of Environmental Conservation": (
        "You are a staff member at the Vermont Department of "
        "Environmental Conservation (DEC). Evaluate the proposal "
        "through the lens of permitting, water quality regulation, "
        "stormwater, wetlands, wastewater, groundwater, air quality, "
        "and hazardous waste. Flag any Act 250, stormwater, wetland, "
        "stream alteration, or wastewater permit triggers. Identify "
        "the permit type, likely timeline, and required next steps.\n\n"
        "Reference:\n\n"
        + load_context("vt_dec_context.md")
    ),
    "VT Agency of Natural Resources": (
        "You are a staff member at the Vermont Agency of Natural "
        "Resources (ANR), focused on Fish & Wildlife and Forests, "
        "Parks and Recreation. Evaluate the proposal through the lens "
        "of wildlife habitat, biodiversity, rare and endangered "
        "species, forest ecology, outdoor recreation, environmental "
        "justice, and climate resilience. Flag habitat fragmentation, "
        "species impact, and long-term ecological risks.\n\n"
        "Reference:\n\n"
        + load_context("vt_anr_context.md")
    ),
    "VT Dept of Health": (
        "You are a staff member at the Vermont Department of Health "
        "(VDH). Evaluate the proposal through the lens of public health, "
        "human subjects protection, HIPAA compliance, health data access, "
        "and health equity. Flag IRB requirements, data use agreement "
        "needs, and confidentiality risks.\n\n"
        "Reference:\n\n"
        + load_context("vt_health_context.md")
    ),
    "VT Agency of Agriculture": (
        "You are a staff member at the Vermont Agency of Agriculture, "
        "Food & Markets (AAFM). Evaluate the proposal through the lens "
        "of Vermont's agricultural systems, Required Agricultural "
        "Practices, water quality regulations, farm economics, and food "
        "safety. Flag compliance issues, data restrictions, or practical "
        "problems with engaging Vermont farms.\n\n"
        "Reference:\n\n"
        + load_context("vt_agriculture_context.md")
    ),
}

problem = (
    "We want to study phosphorus runoff from dairy farms in the "
    "Lake Champlain basin. We plan to collect water samples at "
    "10 sites over 8 weeks and survey farm operators about their "
    "current practices. Deliverable is a report with recommendations."
)

print(f"\nPROBLEM\n{'='*60}\n{problem}\n")

responses = {}
for role, system_prompt in roles.items():
    print(f"Consulting {role}...")
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=700,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": (
                "Review this ORCA student research proposal from your "
                f"expert perspective:\n\n{problem}"
            ),
        }],
    )
    responses[role] = response.content[0].text

for role, text in responses.items():
    print(f"\n{role.upper()}\n{'='*60}\n{text}")

synthesis_prompt = (
    "You are a research coordinator helping a student intern understand "
    "feedback on their ORCA project proposal. Synthesize the reviewer "
    "feedback below into a structured summary with these sections:\n\n"
    "## Critical Issues to Resolve Before Starting\n"
    "## Compliance Steps Required\n"
    "## Key Risks to Manage\n"
    "## Domain Knowledge Gaps\n"
    "## Questions to Bring to Your Faculty Advisor\n\n"
    "Reviewer feedback:\n\n"
    + "\n\n".join(
        f"{role.upper()}:\n{text}" for role, text in responses.items()
    )
)

print(f"\nSYNTHESIS\n{'='*60}")
print("Synthesizing perspectives...")

final = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2000,
    messages=[{"role": "user", "content": synthesis_prompt}],
)

print(final.content[0].text)
