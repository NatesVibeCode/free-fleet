---
name: partner-fleet
description: Turn target ecosystem requirements into a scored deliverable of qualified implementation partners, systems integrators, and consultancies using free models, public job posts, partner directories, and character-exact quote verification.
---

# Partner Fleet: Implementation Partner Research & Scoring Skill

Turn an ecosystem strategy or partner profile into a ranked pipeline of qualified implementation partners, systems integrators (SIs), and digital consultancies, where every single qualification is backed by a verbatim quote from an active job post, case study, or partner directory listing.

The partner-side profile is a typed `IdealPartnerProfile`. Keep its editable JSON in `ideal_partner_profile.json`. Task revisions remain the execution rubric; each run records the selected profile revision when one is available.

---

## The Partner Execution Pipeline

```
0. Context Inference & Gap Interview ──> 1. IPP Deconstruction ──> 2. Discovery Queries ──> 3. Task Spec & Rubric
                                                                                                  │
                                                                                                  ▼
5. Ranked CSV Export                 <── 4. Python Substring Gate <── Free Model Fleet
```

---

## Phase 0: Autonomous Context Inference & Targeted Partner Calibration

Never jump into blind web searches with vague descriptions, and **never interrogate the user with questions about facts you can discover autonomously**.

The agent harness must follow a two-step context protocol:

### Step 1: Autonomous Discovery (History, Memory, & Repo First)
Before asking the operator anything, inspect:
1. **Provided Context**: Use relevant prior context available in the current conversation or explicitly provided by the user.
2. **Workspace Codebase**: Read `README.md`, package descriptors (`pyproject.toml`, `package.json`), integration code (`connectors/`, `providers/`), and git commits (`git log -n 15`).
3. **Resolve the 6 Target Partner Signals**:
   - *Target Ecosystem / Platform*: What product or stack must the partner implement or integrate? (e.g. Snowflake, Apache Kafka, Datadog, Supabase, Kubernetes).
   - *Required Adjacent Competencies*: What underlying technologies must the partner's engineers master? (e.g. AWS, Terraform, Python, dbt).
   - *Target Service Models*: What delivery models are needed? (e.g. Turnkey Systems Integration, Migration/Modernization, Managed Services, Architecture Advisory).
   - *Client Segment & Scale*: What client tier does the partner serve? (e.g. Enterprise, Mid-Market, Startups, Regulated/Healthcare).
   - *Key Delivery Roles*: What job titles indicate client-facing delivery? (e.g. Solutions Architect, Implementation Consultant, Delivery Lead).
   - *Negative Exclusions*: Incompatible business models (e.g. Pure SaaS software vendors, staffing agencies/recruiters without delivery ownership, exclusive competitor alliances).

### Step 2: Gap Analysis & Targeted Interview
- **The Invariant**: NEVER ask the operator about signals already confirmed from repo or session context.
- Summarize the inferred partner profile to the user with clear evidence.
- Ask **only** for signals that are genuinely missing or ambiguous (typically target client tier or 2–3 anchor partner exemplars).

See [references/ipp-interview.md](references/ipp-interview.md) for detailed thought processes, signal definitions, and interview templates.

---

## Phase 1: Deconstruct the Partner ICP (IPP) into 3 Core Signals

Never evaluate a partner on vague directory marketing alone. Deconstruct the partner profile into three mandatory signals:

1. **Ecosystem & Stack Specialization**:
   - What core platform or technology must the partner specialize in? (e.g. `Snowflake`, `Kafka`, `Datadog`, `Supabase`, `Kubernetes`).
   - What certified partner tiers or badges do they hold? (e.g. `AWS Premier Partner`, `Snowflake Elite Partner`).
2. **Service Delivery Model & Client Proof**:
   - What proves they are a fee-for-service consultancy/SI with delivery ownership rather than a software vendor or staffing shop?
   - *Case Studies*: Named client deployments, migrations, or architecture overhauls.
   - *Service Offerings*: Dedicated practices for implementation, migration, or integration.
3. **Delivery Staffing & Hiring Urgency**:
   - What roles indicate they are actively staffing client engagements in this space *right now*? (e.g. `Solutions Architect`, `Implementation Consultant`, `Partner Engineer`, `Cloud Delivery Lead`).

See [references/ipp-decomposition.md](references/ipp-decomposition.md) for full breakdown templates.

---

## Phase 2: Formulate Partner Discovery Queries

The highest-intent public signals come from Applicant Tracking Systems (ATS) where consultancies recruit client-facing architects, alongside public partner directories and case studies.

Search these channels directly:

| Source | Target Domain / Method | Example Query |
|---|---|---|
| **Ashby** (Modern Tech Agencies) | `jobs.ashbyhq.com` | `site:jobs.ashbyhq.com ("consulting" OR "partner" OR "client") "Snowflake" "Architect"` |
| **Greenhouse** (Established SIs) | `boards.greenhouse.io` | `site:boards.greenhouse.io ("solutions architect" OR "implementation consultant") "clients"` |
| **Lever** (Scaleup Consultancies) | `jobs.lever.co` | `site:jobs.lever.co ("delivery" OR "professional services" OR "systems integrator")` |
| **Cloud Directories** | AWS / Azure / GCP Partner Directories | `site:partners.amazonaws.com "migration" "competency"` |
| **Vendor Directories** | Snowflake / Datadog / Supabase Partners | `site:snowflake.com/partners "services" OR "system integrator"` |
| **Agency Directories** | Clutch.co / G2 Service Providers | `site:clutch.co/it-services "Kafka" OR "Snowflake"` |
| **Services & Case Studies** | `*.com/services`, `*.com/case-studies` | `site:example.com/case-studies "implemented" OR "migrated"` |

Compile discovered items into `partners.csv` with columns:
- `item_id`: Partner agency domain or identifier (e.g. `slalom.com`, `trace3.com`)
- `text`: Raw unedited job description, case study excerpt, or practice page description
- `source_uri`: Direct URL of the live posting or case study

See [references/discovery-playbook.md](references/discovery-playbook.md) for discovery queries and search operators.

---

## Phase 3: Build the Task Spec & 0–100 Scoring Rubric

Register a typed task with an explicit 0–100 rubric. Every high score must cite an exact quote.

### Standard Claims Schema:
### 6-Question Gatekeeper Claims Schema:
```json
{
  "type": "object",
  "properties": {
    "checklist": {
      "type": "object",
      "properties": {
        "q1_target_stack": {"type": "boolean", "description": "Verified active delivery in target/adjacent tech stack"},
        "q2_service_model": {"type": "boolean", "description": "Verified turnkey SI/migration practice (false for SaaS or staff aug)"},
        "q3_industry_verticals": {"type": "boolean", "description": "Verified client work in specific industry verticals"},
        "q4_geography_delivery": {"type": "boolean", "description": "Verified physical HQ and delivery locations"},
        "q5_vendor_alliances": {"type": "boolean", "description": "Verified certified partner tiers with adjacent vendors"},
        "q6_case_study_proof": {"type": "boolean", "description": "Verified project outcome, transformation metric, or case study"}
      },
      "required": ["q1_target_stack", "q2_service_model", "q3_industry_verticals", "q4_geography_delivery", "q5_vendor_alliances", "q6_case_study_proof"],
      "additionalProperties": false
    },
    "score": {
      "type": "integer",
      "minimum": 0,
      "maximum": 100,
      "description": "Computed by pipeline from checklist: 100 points total"
    },
    "identified_practice": {
      "type": "string",
      "description": "Concise summary of verified partner practice"
    },
    "answers": {
      "type": "object",
      "description": "Structured answers to the 6 questions backed by cited quotes"
    },
    "source_diversity_count": {
      "type": "integer",
      "description": "Number of distinct source categories cited in quotes"
    },
    "fit_tier": {
      "enum": ["tier_1", "tier_2", "tier_3", "unfit"],
      "description": "tier_1 (85-100), tier_2 (70-84), tier_3 (50-69), unfit (<50)"
    },
    "reasoning": {
      "type": "string",
      "description": "Short explanation grounded in multi-source evidence"
    }
  },
  "required": ["checklist", "identified_practice", "reasoning"],
  "additionalProperties": false
}
```

### The Multi-Source Completeness Gate:
- **Tier 1 (85–100)**: All 6 core questions answered `true` with character-exact quotes across $\ge 3$ distinct source types (First-Party, Vendor Registry, Case Study, Review, ATS).
- **Tier 2 (70–84)**: At least 5 core questions answered `true` across $\ge 2$ distinct source types.
- **Tier 3 (50–69)**: Partial fit (3–4 questions answered); general agency lacking domain specialization.
- **Unfit (<50 / Discard)**: Any core question missing with zero evidence, pure SaaS vendor, staff-aug only, or single-source blind spot.

See [references/scoring-rubric-guide.md](references/scoring-rubric-guide.md) for task templates and instructions.

---

## Phase 4: Execute with Free Models & Exact Substring Verification

Initialize the task using the built-in `partner-research` preset and run across `partners.csv`:

```bash
# Initialize task with partner preset
harness-fleet init partner-qualification --preset partner-research

# Run campaign across partners.csv
harness-fleet run partner-qualification \
  --input partners.csv \
  --id-column item_id \
  --text-column text \
  --run-id campaign-partners-01 \
  --free-only \
  --sessions 4
```

### The Invariant: Substring Verification Gate
Every model claim must include an exact quote. Under the hood:
```python
assert quote in raw_text
```
- If a cited quote is fabricated, paraphrased, or changed by one character, the check fails and the attempt rotates.
- If verified, the exact character range `[start, end]` and source URI are committed to SQLite.

---

## Phase 5: Export & Present the Ranked Deliverable

Export the top-scoring partners sorted descending, ready for partner alliance managers or channel leaders:

```bash
harness-fleet export campaign-partners-01 \
  --format csv \
  --sort-by score \
  --desc \
  --top 25 \
  --rank \
  --output ranked_implementation_partners.csv
```

### Format of the Final Deliverable:
| Rank | Partner Agency | Score | Identified Practice | Verbatim Quote Proof | Source URL |
|---|---|---|---|---|---|
| #1 | `data_integrators.com` | 95 | Enterprise Snowflake Migration Practice | “certified Snowflake Premier Partner delivering end-to-end cloud migrations for Fortune 500 clients” | `https://data_integrators.com/case-studies/snowflake` |
| #2 | `cloud_solutions.io` | 90 | Real-Time Kafka Streaming Deployment | “our client delivery team architects mission-critical Apache Kafka clusters for fintech customers” | `https://jobs.ashbyhq.com/cloud_solutions/lead-architect` |

See [references/mcp-recipes.md](references/mcp-recipes.md) for interactive prompt recipes.

## Related skills

- `harness-fleet` — the shared engine underneath every fleet playbook: task contracts, runs, export, MCP, troubleshooting.
- `account-fleet` — turn an ICP into scored target accounts (`--preset account-research`).

Setup installs these next to this skill in `.agents/skills/`.
