# Implementation Partner Research & Scoring Example

This example demonstrates how to discover, evaluate, qualify, and score potential **Implementation Partners, Systems Integrators (SIs), and Specialized Consultancies** with **character-exact source evidence**:

1. **Implementation Partner Research & Qualification**: Scores partner candidates 0–100 and clips verbatim evidence of active practices, certified alliances, and client delivery case studies.
2. **The Partner Compounding Filter**: Filter broad candidate pools down to qualified, specialized service partners without wasting model compute.
3. **Verifiable Ranked Deliverable**: Export a clean, sorted CSV (`ranked_implementation_partners.csv`) with rank, partner score, identified practice, and verbatim proof quotes ready for alliance managers.

---

## Files in this Directory

- `sample_partners.csv`: Sample candidates including premier cloud consultancies (Slalom), advanced systems integrators (Trace3), specialized boutique data consultancies (DataBridge), regional IT SIs (Apex), creative web agencies (PixelCraft), and pure SaaS software vendors (Stripe).
- `task.json`: Pre-configured closed task specification requiring a checklist-derived `score` (0–100), `fit_tier`, `identified_practice`, and `reasoning`.

---

## Quickstart (CLI)

### 1. Initialize Task from Preset
You can initialize directly from the built-in `partner-research` preset:

```bash
harness-fleet init partner-qualification --preset partner-research
```

Or run directly from the bundled `task.json`:
```bash
harness-fleet run examples/partner_research/task.json \
  --input examples/partner_research/sample_partners.csv \
  --id-column domain \
  --text-column research \
  --run-id partners-01
```

### 2. Export Ranked Implementation Partners CSV

Generate the ranked deliverable (sorted by score descending, with a 1-indexed rank column):

```bash
harness-fleet export partners-01 \
  --format csv \
  --sort-by score \
  --desc \
  --top 10 \
  --rank \
  --output ranked_implementation_partners.csv
```

Output format (`ranked_implementation_partners.csv`):
```csv
rank,item_id,score,fit_tier,identified_practice,reasoning,primary_quote_text,quote_count,source_uri,source_digest
1,slalom.com,100,tier_1,"Premier Consulting Partner & Cloud Data Platform Modernization","Solutions architects work directly with Fortune 500 clients delivering Snowflake, Kafka, and Kubernetes solutions","work directly with Fortune 500 enterprise clients to architect, deploy, and modernize cloud data platforms",1,"",...
2,trace3.com,100,tier_1,"Enterprise Apache Kafka Streaming & Multi-Region Kubernetes Migration","Turnkey client solutions with case study for top-10 financial services customer","Leading the enterprise Apache Kafka streaming infrastructure deployment and multi-region Kubernetes migration",1,"",...
```

---

## The 3-Tier Partner Compounding Filter

To filter large candidate sets down to top-tier partners efficiently:

```bash
# Layer 1: Professional services / consultancy screening (1,000 -> 300)
harness-fleet init l1-partner-filter --preset filter
harness-fleet run l1-partner-filter --input directory_hits.csv --run-id l1-partners
harness-fleet export l1-partners --format csv --filter '{"all": [{"field": "passed", "value": true}]}' --output l1_services_survivors.csv

# Layer 2: Ecosystem & tech stack verification (300 -> 80)
harness-fleet init l2-stack-filter --preset filter
harness-fleet run l2-stack-filter --input practice_pages.csv --only-ids l1_services_survivors.csv --run-id l2-partners
harness-fleet export l2-partners --format csv --filter '{"all": [{"field": "passed", "value": true}]}' --output l2_stack_survivors.csv

# Layer 3: Deep qualification & evidence clipping (80 -> 25)
harness-fleet init l3-partner-scoring --preset partner-research
harness-fleet run l3-partner-scoring --input qualified_postings.csv --only-ids l2_stack_survivors.csv --run-id l3-partners
harness-fleet export l3-partners --format csv --sort-by score --desc --top 25 --rank --output ranked_implementation_partners.csv
```
