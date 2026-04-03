from __future__ import annotations

from typing import NamedTuple

# Format: (company_slug, ats_type)
# Organized by: 🇲🇽 CDMX/Mexico presence → 🌎 Remote-friendly LATAM → 🌐 Relocation/visa-sponsored
# Adjacent roles covered: ML Engineer, AI Platform, LLM Engineer, Data Scientist, Backend AI, MLOps

CompanyTuple = tuple[str, str]

CDMX = "cdmx_presence"
LATAM = "latam_remote"
AI_NATIVE = "ai_native_startups"
GLOBAL_REMOTE = "global_remote_friendly"
RELOCATION = "relocation_visa"
ENTERPRISE = "enterprise_platforms"

GROUP_ORDER: tuple[str, ...] = (
    CDMX,
    LATAM,
    AI_NATIVE,
    GLOBAL_REMOTE,
    RELOCATION,
    ENTERPRISE,
)


class CompanySpec(NamedTuple):
    slug: str
    ats: str
    groups: tuple[str, ...] = ()
    company_name: str | None = None
    fetch_slug: str | None = None


def company(
    slug: str,
    ats: str,
    *groups: str,
    company_name: str | None = None,
    fetch_slug: str | None = None,
) -> CompanySpec:
    return CompanySpec(
        slug=slug,
        ats=ats,
        groups=tuple(groups),
        company_name=company_name,
        fetch_slug=fetch_slug,
    )


_COMPANY_SPECS: tuple[CompanySpec, ...] = (
    # ── 🇲🇽 COMPANIES WITH CDMX OFFICES / MEXICO ENGINEERING TEAMS ────────────────
    company("etsy", "greenhouse", CDMX),
    company("kavak", "greenhouse", CDMX),
    company("clip-mx", "lever", CDMX, company_name="Clip", fetch_slug="clip"),
    company("konfio", "greenhouse", CDMX),
    company("bitso", "greenhouse", CDMX),
    company("klar", "lever", CDMX),
    company(
        "incode-technologies",
        "lever",
        CDMX,
        company_name="Incode Technologies",
        fetch_slug="incode",
    ),
    company("latam", "greenhouse", CDMX),
    company("qualcomm", "greenhouse", CDMX),
    company("google", "greenhouse", CDMX),
    company("salesforce", "greenhouse", CDMX),
    company("wizeline", "greenhouse", CDMX),
    company("softtek", "greenhouse", CDMX),
    company("encora", "greenhouse", CDMX),
    company("scribd", "greenhouse", CDMX),
    company("simplepractice", "greenhouse", CDMX),
    company("sezzle", "greenhouse", CDMX),
    company("totalplay", "greenhouse", CDMX),
    company("mercadolibre", "greenhouse", CDMX),
    company("oracle", "greenhouse", CDMX),
    company("bbva", "greenhouse", CDMX),
    company("rappi", "greenhouse", CDMX),

    # ── 🌎 REMOTE-FRIENDLY / LATAM-OPEN (STRONG SIGNAL) ──────────────────────────
    company("factored", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("arionkoder", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("xebia", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("quora", "ashby", LATAM, GLOBAL_REMOTE),
    company("cohere", "ashby", LATAM, GLOBAL_REMOTE),
    company("handshake", "ashby", LATAM, GLOBAL_REMOTE),
    company(
        "scaleai",
        "lever",
        LATAM,
        GLOBAL_REMOTE,
        company_name="Scale AI",
        fetch_slug="scale-ai",
    ),
    company(
        "wandb",
        "lever",
        LATAM,
        GLOBAL_REMOTE,
        company_name="Weights & Biases",
        fetch_slug="weightsbiases",
    ),
    company("labelbox", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("huggingface", "lever", LATAM, GLOBAL_REMOTE),
    company("replit", "ashby", LATAM, GLOBAL_REMOTE),
    company("runwayml", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("elevenlabs", "ashby", LATAM, GLOBAL_REMOTE),
    company("stabilityai", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("mistral", "lever", LATAM, GLOBAL_REMOTE),
    company("anthropic", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("openai", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("perplexityai", "ashby", LATAM, GLOBAL_REMOTE),
    company("characterai", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("togetherai", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("anyscale", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("modal-labs", "ashby", LATAM, GLOBAL_REMOTE),
    company("replicate", "ashby", LATAM, GLOBAL_REMOTE),
    company("luma-ai", "ashby", LATAM, GLOBAL_REMOTE),
    company("glean", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("ema", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("sierra", "greenhouse", LATAM, GLOBAL_REMOTE),
    company("dust", "ashby", LATAM, GLOBAL_REMOTE),
    company("vapi", "ashby", LATAM, GLOBAL_REMOTE),

    # ── 🌐 RELOCATION / VISA-SPONSORED OPPORTUNITIES ─────────────────────────────
    company("deepmind", "greenhouse", RELOCATION),
    company("palantir", "lever", RELOCATION),
    company("stripe", "greenhouse", RELOCATION),
    company("databricks", "greenhouse", RELOCATION),
    company("snowflake", "greenhouse", RELOCATION),
    company("datadog", "greenhouse", RELOCATION),
    company("mongodb", "greenhouse", RELOCATION),
    company("elastic", "greenhouse", RELOCATION),
    company("cloudflare", "greenhouse", RELOCATION),
    company("vercel", "ashby", RELOCATION),
    company("linear", "ashby", RELOCATION),
    company("notion", "greenhouse", RELOCATION),
    company("intercom", "greenhouse", GLOBAL_REMOTE, RELOCATION),
    company("typeform", "ashby", GLOBAL_REMOTE, RELOCATION),
    company("figma", "greenhouse", RELOCATION),
    company("airtable", "greenhouse", RELOCATION),
    company("zapier", "greenhouse", GLOBAL_REMOTE, RELOCATION),
    company("hubspot", "greenhouse", RELOCATION),
    company("zendesk", "greenhouse", GLOBAL_REMOTE, RELOCATION),
    company("twilio", "greenhouse", RELOCATION),
    company("brex", "greenhouse", GLOBAL_REMOTE, RELOCATION),
    company("ramp", "greenhouse", GLOBAL_REMOTE, RELOCATION),
    company("mercury", "ashby", GLOBAL_REMOTE, RELOCATION),
    company("rippling", "greenhouse", RELOCATION),
    company("lattice", "greenhouse", RELOCATION),
    company("leapsome", "greenhouse", GLOBAL_REMOTE, RELOCATION),

    # ── 🤖 AI-NATIVE STARTUPS (HIGH SIGNAL FOR AI ENG ROLES) ─────────────────────
    company("harvey", "ashby", AI_NATIVE),
    company("casetext", "greenhouse", AI_NATIVE),
    company("hippocratic-ai", "greenhouse", AI_NATIVE),
    company("abridge", "greenhouse", AI_NATIVE),
    company("nabla", "lever", AI_NATIVE),
    company("rad-ai", "greenhouse", AI_NATIVE),
    company("adept", "greenhouse", AI_NATIVE),
    company("cognition", "ashby", AI_NATIVE),
    company("magic-dev", "greenhouse", AI_NATIVE),
    company("anysphere", "ashby", AI_NATIVE),
    company("codeium", "greenhouse", AI_NATIVE),
    company("poolside", "lever", AI_NATIVE),
    company("imbue", "greenhouse", AI_NATIVE),
    company("contextual-ai", "greenhouse", AI_NATIVE),
    company("covariant", "greenhouse", AI_NATIVE),
    company("physical-intelligence", "greenhouse", AI_NATIVE),
    company("waymo", "greenhouse", AI_NATIVE),
    company("samsara", "greenhouse", AI_NATIVE),

    # ── 📊 DATA/MLOPS PLATFORMS (ADJACENT ROLES) ─────────────────────────────────
    company("dbt-labs", "greenhouse", ENTERPRISE),
    company("fivetran", "greenhouse", ENTERPRISE),
    company("airbyte", "greenhouse", ENTERPRISE),
    company("astronomer", "greenhouse", ENTERPRISE),
    company("prefect", "greenhouse", ENTERPRISE),
    company("tecton", "greenhouse", ENTERPRISE),
    company("arize-ai", "greenhouse", ENTERPRISE),
    company("fiddler-ai", "greenhouse", ENTERPRISE),
    company("arthur-ai", "greenhouse", ENTERPRISE),

    # ── 🏦 LATAM FINTECH (STRONG AI INVESTMENT, CDMX ADJACENT) ──────────────────
    company("nubank", "greenhouse", LATAM),
    company("belvo", "greenhouse", LATAM),
    company("kueski", "greenhouse", LATAM),
    company("stori", "greenhouse", LATAM),
    company("arcus", "lever", LATAM),
    company("merama", "greenhouse", LATAM),
    company("nowports", "greenhouse", LATAM),

    # ── 🧠 ENTERPRISE AI / B2B (STRONG HIRING PIPELINE) ─────────────────────────
    company("writer", "greenhouse", ENTERPRISE),
    company("jasper", "greenhouse", ENTERPRISE),
    company("moveworks", "greenhouse", ENTERPRISE),
    company("observe-ai", "greenhouse", ENTERPRISE),
    company("cresta", "greenhouse", ENTERPRISE),
    company("kore-ai", "greenhouse", ENTERPRISE),
    company("unstructured", "ashby", ENTERPRISE),
    company("llamaindex", "ashby", ENTERPRISE),
    company("langchain", "greenhouse", ENTERPRISE),
    company("vectara", "greenhouse", ENTERPRISE),
    company("weaviate", "greenhouse", ENTERPRISE),
    company("pinecone", "greenhouse", ENTERPRISE),
    company("qdrant", "greenhouse", ENTERPRISE),
    company("chroma", "ashby", ENTERPRISE),
)


def _build_slug_overrides(specs: tuple[CompanySpec, ...]) -> dict[str, dict[str, str]]:
    overrides: dict[str, dict[str, str]] = {}
    for spec in specs:
        if spec.fetch_slug and spec.fetch_slug != spec.slug:
            overrides.setdefault(spec.ats, {})[spec.slug] = spec.fetch_slug
    return overrides


def _build_group_slugs(specs: tuple[CompanySpec, ...]) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {group_name: set() for group_name in GROUP_ORDER}
    for spec in specs:
        for group_name in spec.groups:
            grouped.setdefault(group_name, set()).add(spec.slug)
    return grouped


def _build_company_groups(specs: tuple[CompanySpec, ...]) -> dict[str, list[CompanyTuple]]:
    grouped: dict[str, list[CompanyTuple]] = {group_name: [] for group_name in GROUP_ORDER}
    for spec in specs:
        company_tuple = (spec.slug, spec.ats)
        for group_name in spec.groups:
            grouped.setdefault(group_name, []).append(company_tuple)
    return grouped


SLUG_OVERRIDES: dict[str, dict[str, str]] = _build_slug_overrides(_COMPANY_SPECS)

COMPANY_NAME_OVERRIDES: dict[str, str] = {
    spec.slug: spec.company_name
    for spec in _COMPANY_SPECS
    if spec.company_name is not None
}

COMPANIES: list[CompanyTuple] = [
    (spec.slug, spec.ats)
    for spec in _COMPANY_SPECS
]

GROUP_SLUGS: dict[str, set[str]] = _build_group_slugs(_COMPANY_SPECS)

COMPANY_GROUPS: dict[str, list[CompanyTuple]] = _build_company_groups(_COMPANY_SPECS)


def build_company_list(
    group_names: list[str],
    limit: int | None = None,
) -> list[CompanyTuple]:
    selected: list[CompanyTuple] = []
    seen_slugs: set[str] = set()

    for group_name in group_names:
        for slug, ats in COMPANY_GROUPS.get(group_name, []):
            if slug in seen_slugs:
                continue
            selected.append((slug, ats))
            seen_slugs.add(slug)
            if limit is not None and len(selected) >= limit:
                return selected

    return selected