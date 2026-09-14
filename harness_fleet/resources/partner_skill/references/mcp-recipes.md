# Partner Fleet: MCP & Agent Recipes

Ready-to-use prompt recipes for running partner qualification campaigns across Claude Desktop, Cursor, OpenCode, and Antigravity IDE.

---

## 1. Task Initialization Recipe (MCP / CLI)

To initialize a partner qualification task using MCP or CLI:

### CLI:
```bash
harness-fleet init partner-qualification --preset partner-research
```

### MCP Tool Call (`harness_fleet_init`):
```json
{
  "task_name": "partner-qualification",
  "preset": "partner-research"
}
```

---

## 2. Partner Discovery Recipe (Prompt for LLM Agent)

Use this prompt when delegating discovery to an AI assistant:

```markdown
Find 20 potential implementation partners and systems integrators specializing in [Target Technology, e.g. Snowflake / Apache Kafka].

Follow the partner-fleet discovery playbook:
1. Search ATS job boards (Ashby, Greenhouse, Lever) for consulting roles:
   - `site:jobs.ashbyhq.com "[Target Technology]" ("consulting" OR "client delivery" OR "partner") "Architect"`
   - `site:boards.greenhouse.io "[Target Technology]" ("solutions architect" OR "implementation consultant") "clients"`
2. Query Clutch.co and partner directories:
   - `site:clutch.co/it-services "[Target Technology]"`
3. Compile all discovered hits into `partners.csv` with columns:
   - `item_id`: canonical partner domain (e.g. `slalom.com`)
   - `text`: unedited job posting description or case study excerpt
   - `source_uri`: direct URL of the live posting or page

Ensure each record includes the verbatim excerpt proving client delivery or specialized practice.
```

---

## 3. Campaign Execution Recipe

Run the qualification campaign across free routes with SQLite persistence:

```bash
harness-fleet run partner-qualification \
  --input partners.csv \
  --id-column item_id \
  --text-column text \
  --run-id campaign-partners-01 \
  --free-only \
  --sessions 4
```

---

## 4. Export & Presentation Recipe

Export the top-tier partners sorted by fit score with exact quotation evidence:

```bash
harness-fleet export campaign-partners-01 \
  --format csv \
  --sort-by score \
  --desc \
  --top 25 \
  --rank \
  --output ranked_implementation_partners.csv
```
