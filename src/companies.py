# Format: (company_slug, ats_type)
# Organized by: 🇲🇽 CDMX/Mexico presence → 🌎 Remote-friendly LATAM → 🌐 Relocation/visa-sponsored
# Adjacent roles covered: ML Engineer, AI Platform, LLM Engineer, Data Scientist, Backend AI, MLOps

COMPANIES: list[tuple[str, str]] = [

    # ── 🇲🇽 COMPANIES WITH CDMX OFFICES / MEXICO ENGINEERING TEAMS ────────────────

    # Etsy — confirmed CDMX engineering office (Polanco)
    ("etsy", "greenhouse"),

    # Kavak — Mexico-founded unicorn, active ML team in CDMX
    ("kavak", "greenhouse"),

    # Clip — Mexican fintech, CDMX HQ, growing ML/data team
    ("clip-mx", "lever"),

    # Konfío — B2B fintech CDMX, ML for credit scoring
    ("konfio", "greenhouse"),

    # Bitso — Crypto exchange, CDMX office, ML/data engineering
    ("bitso", "greenhouse"),

    # Klar — Neobank CDMX, AI/ML for risk and fraud
    ("klar", "lever"),

    # Incode Technologies — Identity AI, CDMX HQ, LLM + vision engineering
    ("incode-technologies", "lever"),

    # LATAM Airlines — Greenhouse presence, MLE roles open in Mexico
    ("latam", "greenhouse"),

    # Qualcomm — CDMX engineering office, ML compiler roles
    ("qualcomm", "greenhouse"),

    # Google — Cloud AI Engineer roles specifically advertised for CDMX
    ("google", "greenhouse"),

    # Salesforce — Confirmed engineering in CDMX, ML/AI roles
    ("salesforce", "greenhouse"),

    # Wizeline — Mexico City + GDL + MTY, applied AI consulting arm
    ("wizeline", "greenhouse"),

    # Softtek — Enterprise AI, Mexico HQ, ISO 42001 certified AI mgmt
    ("softtek", "greenhouse"),

    # Encora — CDMX + Hermosillo, explicit LLM Engineering roles
    ("encora", "greenhouse"),

    # Scribd — Remote-friendly, multiple MLE openings targeting Mexico
    ("scribd", "greenhouse"),

    # SimplePractice — Confirmed ML roles visible in MX job boards
    ("simplepractice", "greenhouse"),

    # Sezzle — Buy-now-pay-later, ML roles open in Mexico City
    ("sezzle", "greenhouse"),

    # Grupo Salinas / Totalplay (tech arm) — Large CDMX conglomerate, AI initiatives
    ("totalplay", "greenhouse"),

    # Mercado Libre — Latam e-commerce giant, CDMX office, large ML platform team
    ("mercadolibre", "greenhouse"),

    # Oracle — OCI Data Science roles, Mexico engineering presence
    ("oracle", "greenhouse"),

    # BBVA Mexico — Banktech + AI, large CDMX AI center
    ("bbva", "greenhouse"),

    # Rappi — Delivery super-app, Mexico City office, ML/Recommendations team
    ("rappi", "greenhouse"),

    # ── 🌎 REMOTE-FRIENDLY / LATAM-OPEN (STRONG SIGNAL) ──────────────────────────

    # Factored — LATAM-focused AI/ML staffing + residency (Greenhouse confirmed)
    ("factored", "greenhouse"),

    # Arionkoder — LLM/AI Greenhouse-listed, explicitly LATAM remote
    ("arionkoder", "greenhouse"),

    # Xebia / LATAM — GCP ML roles open for LATAM (Greenhouse confirmed)
    ("xebia", "greenhouse"),

    # Quora / Poe — Remote-first, Ashby confirmed, MX-eligible countries
    ("quora", "ashby"),

    # Cohere — LLM infra company, Ashby confirmed, LATAM hires
    ("cohere", "ashby"),

    # Handshake — Ashby confirmed, ML intern/eng roles, remote eligible
    ("handshake", "ashby"),

    # Scale AI — Data annotation + LLM training platform, Lever, LATAM remote
    ("scaleai", "lever"),

    # Weights & Biases (wandb) — MLOps tooling, remote-first, Lever
    ("wandb", "lever"),

    # Labelbox — Data-centric AI, Wellfound/Greenhouse, remote eng
    ("labelbox", "greenhouse"),

    # Hugging Face — Open-source AI, remote-first globally, Lever
    ("huggingface", "lever"),

    # Replit — AI coding platform, remote-friendly, Ashby
    ("replit", "ashby"),

    # Runway ML — Generative AI/video, NYC + remote, Greenhouse
    ("runwayml", "greenhouse"),

    # ElevenLabs — Voice AI, remote-friendly, Ashby
    ("elevenlabs", "ashby"),

    # Stability AI — GenAI, remote-distributed, Greenhouse
    ("stabilityai", "greenhouse"),

    # Mistral AI — LLM company, remote roles, Lever (EU primarily but open)
    ("mistral", "lever"),

    # Anthropic — Safety-focused LLM lab, Greenhouse, US-based but growing
    ("anthropic", "greenhouse"),

    # OpenAI — LLM lab, Greenhouse, US-based with some intl roles
    ("openai", "greenhouse"),

    # Perplexity AI — AI search, Ashby, fast-growing remote roles
    ("perplexityai", "ashby"),

    # Character.AI — Conversational AI, Greenhouse, some remote
    ("characterai", "greenhouse"),

    # Together AI — LLM inference platform, Greenhouse, remote
    ("togetherai", "greenhouse"),

    # Anyscale — Ray / distributed ML, Greenhouse, remote-open
    ("anyscale", "greenhouse"),

    # Modal — Cloud GPU/ML infra, Ashby, remote-friendly
    ("modal-labs", "ashby"),

    # Replicate — ML model hosting, Ashby, remote-first
    ("replicate", "ashby"),

    # Luma AI — 3D/Video GenAI, Ashby
    ("luma-ai", "ashby"),

    # Glean — Enterprise AI search, Greenhouse, some remote
    ("glean", "greenhouse"),

    # Ema — Enterprise AI assistant, Greenhouse, remote
    ("ema", "greenhouse"),

    # Sierra AI — Conversational AI agents, Greenhouse
    ("sierra", "greenhouse"),

    # Dust — LLM ops / enterprise agents, Ashby
    ("dust", "ashby"),

    # Vapi — Voice AI infrastructure, Ashby
    ("vapi", "ashby"),

    # ── 🌐 RELOCATION / VISA-SPONSORED OPPORTUNITIES ─────────────────────────────

    # Deepmind — Google DeepMind, London/global, Greenhouse, visa sponsor
    ("deepmind", "greenhouse"),

    # Palantir — US/EU AI/ML, Lever, sponsors visas
    ("palantir", "lever"),

    # Stripe — Fintech AI platform, Greenhouse, strong relocation program
    ("stripe", "greenhouse"),

    # Databricks — Data+AI platform, Greenhouse, hires globally
    ("databricks", "greenhouse"),

    # Snowflake — Data cloud + Cortex AI, Greenhouse
    ("snowflake", "greenhouse"),

    # Datadog — Observability + AI, Greenhouse, EU/US relocation
    ("datadog", "greenhouse"),

    # MongoDB — Atlas Vector Search / AI layer, Greenhouse
    ("mongodb", "greenhouse"),

    # Elastic — ElasticSearch + ELSER AI search, Greenhouse
    ("elastic", "greenhouse"),

    # Cloudflare — AI Workers / inference edge, Greenhouse
    ("cloudflare", "greenhouse"),

    # Vercel — AI SDK/Next.js, Ashby, remote + relocation
    ("vercel", "ashby"),

    # Linear — Dev tooling, Ashby, remote-first EU/US
    ("linear", "ashby"),

    # Notion — Notion AI, Greenhouse, SF + NYC + remote
    ("notion", "greenhouse"),

    # Intercom — Fin AI agent, Greenhouse, Dublin + remote
    ("intercom", "greenhouse"),

    # Typeform — AI forms, Ashby, Barcelona HQ, LATAM-friendly
    ("typeform", "ashby"),

    # Figma — Design AI, Greenhouse, SF + remote
    ("figma", "greenhouse"),

    # Airtable — No-code + AI, Greenhouse, SF
    ("airtable", "greenhouse"),

    # Zapier — Workflow automation + AI, Greenhouse, remote-first
    ("zapier", "greenhouse"),

    # HubSpot — CRM + AI, Greenhouse, global offices
    ("hubspot", "greenhouse"),

    # Zendesk — CX + AI, Greenhouse, LATAM presence
    ("zendesk", "greenhouse"),

    # Twilio — Communications + AI, Greenhouse, remote
    ("twilio", "greenhouse"),

    # Brex — Fintech AI, Greenhouse, LATAM remote-open
    ("brex", "greenhouse"),

    # Ramp — Finance AI, Greenhouse, US-based + remote
    ("ramp", "greenhouse"),

    # Mercury — Banking API + AI, Ashby
    ("mercury", "ashby"),

    # Rippling — HR + AI platform, Greenhouse
    ("rippling", "greenhouse"),

    # Lattice — People mgmt + AI, Greenhouse
    ("lattice", "greenhouse"),

    # Leapsome — HR AI, Greenhouse, Berlin-based, remote-open
    ("leapsome", "greenhouse"),

    # ── 🤖 AI-NATIVE STARTUPS (HIGH SIGNAL FOR AI ENG ROLES) ─────────────────────

    # Harvey AI — Legal AI, Ashby
    ("harvey", "ashby"),

    # Casetext / Thomson Reuters AI — Legal AI, Greenhouse
    ("casetext", "greenhouse"),

    # Hippocratic AI — Healthcare AI agents, Greenhouse
    ("hippocratic-ai", "greenhouse"),

    # Abridge — Medical AI transcription, Greenhouse
    ("abridge", "greenhouse"),

    # Nabla — Clinical AI, CDMX-adjacent (French + US), Lever
    ("nabla", "lever"),

    # Rad AI — Radiology AI, Greenhouse
    ("rad-ai", "greenhouse"),

    # Adept AI — Action models / agents, Greenhouse
    ("adept", "greenhouse"),

    # Cognition (Devin) — AI SWE agent, Ashby
    ("cognition", "ashby"),

    # Magic.dev — AI code completion, Greenhouse
    ("magic-dev", "greenhouse"),

    # Cursor — AI code editor, Ashby (fast-growing)
    ("anysphere", "ashby"),

    # Windsurf / Codeium — AI coding, Greenhouse
    ("codeium", "greenhouse"),

    # Poolside AI — Code LLM, Lever
    ("poolside", "lever"),

    # Imbue — Research + agents, Greenhouse
    ("imbue", "greenhouse"),

    # Contextual AI — RAG/enterprise LLM, Greenhouse
    ("contextual-ai", "greenhouse"),

    # Covariant — Robotics + AI, Greenhouse
    ("covariant", "greenhouse"),

    # Physical Intelligence (pi) — Robotics foundation models, Greenhouse
    ("physical-intelligence", "greenhouse"),

    # Waymo — Autonomous driving AI, Greenhouse
    ("waymo", "greenhouse"),

    # Samsara — IoT + AI, Greenhouse, LATAM offices
    ("samsara", "greenhouse"),

    # ── 📊 DATA/MLOPS PLATFORMS (ADJACENT ROLES) ─────────────────────────────────

    # dbt Labs — Analytics engineering, Greenhouse, remote-first
    ("dbt-labs", "greenhouse"),

    # Fivetran — Data integration + AI, Greenhouse
    ("fivetran", "greenhouse"),

    # Airbyte — Open-source data pipelines, Greenhouse
    ("airbyte", "greenhouse"),

    # Astronomer (Airflow) — ML orchestration, Greenhouse
    ("astronomer", "greenhouse"),

    # Prefect — Workflow orchestration, Greenhouse
    ("prefect", "greenhouse"),

    # Tecton — Feature store, Greenhouse
    ("tecton", "greenhouse"),

    # Arize AI — ML observability, Greenhouse
    ("arize-ai", "greenhouse"),

    # Fiddler AI — ML monitoring, Greenhouse
    ("fiddler-ai", "greenhouse"),

    # Arthur AI — ML governance, Greenhouse
    ("arthur-ai", "greenhouse"),

    # ── 🏦 LATAM FINTECH (STRONG AI INVESTMENT, CDMX ADJACENT) ──────────────────

    # Nu Bank — Brazilian neobank, huge ML team, remote LATAM roles
    ("nubank", "greenhouse"),

    # Belvo — Open banking API (YC-backed, CDMX), Greenhouse
    ("belvo", "greenhouse"),

    # Kueski — BNPL Mexico, AI credit scoring, Greenhouse
    ("kueski", "greenhouse"),

    # Stori — CDMX credit card startup, AI/ML team
    ("stori", "greenhouse"),

    # Arcus — Fintech infra Mexico, Lever
    ("arcus", "lever"),

    # Merama — LatAm e-commerce, AI ops, Greenhouse
    ("merama", "greenhouse"),

    # Nowports — Latam logistics AI, Greenhouse
    ("nowports", "greenhouse"),

    # ── 🧠 ENTERPRISE AI / B2B (STRONG HIRING PIPELINE) ─────────────────────────

    # Writer — Enterprise LLM platform, Greenhouse
    ("writer", "greenhouse"),

    # Cohere for Enterprise — see cohere above
    # Jasper AI — Content AI, Greenhouse
    ("jasper", "greenhouse"),

    # Moveworks — IT support AI agents, Greenhouse
    ("moveworks", "greenhouse"),

    # Observe.AI — Contact center AI, Greenhouse
    ("observe-ai", "greenhouse"),

    # Cresta — Sales AI/coaching, Greenhouse
    ("cresta", "greenhouse"),

    # Kore.ai — Conversational AI platform, Greenhouse
    ("kore-ai", "greenhouse"),

    # Unstructured — Document parsing for LLMs, Ashby
    ("unstructured", "ashby"),

    # LlamaIndex — LLM data framework, Ashby
    ("llamaindex", "ashby"),

    # LangChain — LLM orchestration, Greenhouse
    ("langchain", "greenhouse"),

    # Vectara — RAG-as-a-service, Greenhouse
    ("vectara", "greenhouse"),

    # Weaviate — Vector DB, Greenhouse
    ("weaviate", "greenhouse"),

    # Pinecone — Vector DB, Greenhouse
    ("pinecone", "greenhouse"),

    # Qdrant — Vector DB, Greenhouse
    ("qdrant", "greenhouse"),

    # Chroma — Open-source vector DB, Ashby
    ("chroma", "ashby"),
]