# Scoring Rubric & Task Spec Guide for Implementation Partners

This guide explains how to construct a deterministic 0–100 scoring contract so that LLMs evaluate potential implementation partners consistently and extract character-exact evidence.

---

## 1. The 4-Tier Partner Scoring Rubric

To prevent model score inflation or arbitrary grading, enforce this standardized 4-tier rubric across all partner qualification campaigns:

| Tier | Score Range | Definition | Grounding Requirement |
|---|---|---|---|
| **Tier 1 (Direct Implementation Partner)** | **85 – 100** | Dedicated practice, verified certified partner status, or explicit client case study in the target ecosystem cited directly in source text (e.g. "certified Snowflake Premier Partner delivering cloud data migrations for Fortune 500 clients"). | **Mandatory verbatim quote** naming the specialized practice, partnership, or case study. |
| **Tier 2 (High Potential Adjacent Partner)** | **70 – 84** | Confirmed systems integration / consultancy model with active hiring for technical delivery roles in adjacent stack (e.g. Cloud/Data architecture), with demonstrated capacity to deploy solutions for clients. | Quote proving consulting/SI model and client-facing technical role. |
| **Tier 3 (General Dev Shop / Broad Agency)** | **50 – 69** | General IT services, staff augmentation, or web development agency without proven specialization or enterprise track record in the required domain. | General agency services description quote. |
| **Unfit (Discard)** | **0 – 49** | Pure software product company (SaaS vendor), pure recruiting/staffing firm, direct rival alliance, or incompatible domain. | None (auto-filtered out of deliverable). |

---

## 2. Complete TaskSpec Template

When initializing a task via CLI (`harness-fleet init partner-qualification --preset partner-research`), the task is registered with this declarative specification:

```json
{
  "$schema": "https://raw.githubusercontent.com/NatesVibeCode/harness-fleet/master/schemas/task-v1.schema.json",
  "format_version": "harness_fleet_task_v1",
  "name": "partner-qualification",
  "instructions": "Evaluate potential implementation partner fit by answering the evidence checklist, identify the verified partner practice or core capability, and cite verbatim evidence. The pipeline computes the partner fit score and tier.",
  "batch_size": 4,
  "max_slice_chars": 6000,
  "min_quote_chars": 15,
  "checklist": {
    "verified_service_model": 30,
    "ecosystem_specialization": 35,
    "delivery_hiring_or_case_study": 25,
    "target_client_segment": 10
  },
  "claims_schema": {
    "type": "object",
    "properties": {
      "checklist": {
        "type": "object",
        "properties": {
          "verified_service_model": {
            "type": "boolean",
            "description": "True only when the source confirms the company is an implementation partner, systems integrator, consultancy, or agency delivering client services (not a pure software vendor or pure recruiter)."
          },
          "ecosystem_specialization": {
            "type": "boolean",
            "description": "True only when the source confirms an active practice, specialized capability, or deep technical delivery in the target or direct adjacent technology stack."
          },
          "delivery_hiring_or_case_study": {
            "type": "boolean",
            "description": "True only when the source shows active hiring for client-facing technical roles (Solutions Architect, Implementation Consultant, Delivery Lead) or describes an explicit client deployment/migration case study."
          },
          "target_client_segment": {
            "type": "boolean",
            "description": "True only when the source confirms alignment with target client segments, scale, or geographic scope."
          }
        },
        "required": [
          "delivery_hiring_or_case_study",
          "ecosystem_specialization",
          "target_client_segment",
          "verified_service_model"
        ],
        "additionalProperties": false
      },
      "score": {
        "type": "integer",
        "minimum": 0,
        "maximum": 100,
        "description": "Computed by the pipeline from the checklist; omit it."
      },
      "identified_practice": {
        "type": "string",
        "description": "The verified partner practice, capability, or core service offering, named exactly as the source names it."
      },
      "fit_tier": {
        "enum": ["tier_1", "tier_2", "tier_3", "unfit"],
        "description": "Score band, derived by the pipeline: tier_1 85-100, tier_2 70-84, tier_3 50-69, unfit below 50. Omit it."
      },
      "reasoning": {
        "type": "string",
        "description": "Short explanation grounded in the cited quotes, naming the evidence behind the checklist and practice."
      }
    },
    "required": ["checklist", "identified_practice", "reasoning"],
    "additionalProperties": false
  }
}
```

---

## 3. Substring Verification Gate

When candidate model outputs are submitted:
1. Every claim is validated against the raw page text:
   ```python
   assert quote in raw_text
   assert len(quote.strip()) >= 15
   ```
2. The pipeline checks that checklist answers correspond to verified quotes:
   - For every checklist item answered `true`, there must be at least one quote tagged with that item in its `supports` field.
   - Any hallucinated quote or false claim fails validation and causes the attempt to rotate to the next worker.
3. The pipeline computes the final score:
   - `score = sum(points for verified true checklist items)`
   - Fits neatly into `fit_tier`: 85+ → `tier_1`, 70–84 → `tier_2`, 50–69 → `tier_3`, <50 → `unfit`.
