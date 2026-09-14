# Discovery Playbook: Finding 500–1,000 Implementation Partners

This playbook guides an AI agent on how to discover high-intent systems integrators (SIs), boutique consultancies, and digital agencies with proven client delivery experience.

---

## 1. ATS Search Operators (Consultancies & Agencies Hire on ATS)

Applicant Tracking Systems (Ashby, Greenhouse, Lever, Workable) are exceptional sources for partner discovery. When a professional services firm or consultancy hires, they explicitly describe their client projects, technology partnerships, and delivery engagements in the job post.

### What to Look For:
- Job Titles: `Solutions Architect`, `Implementation Consultant`, `Partner Engineer`, `Technical Delivery Lead`, `Cloud Migration Specialist`, `Practice Lead`.
- Key Verbs: `client delivery`, `working with our enterprise clients`, `certified partner`, `client engagements`, `lead migrations for customers`.

### Ashby (`jobs.ashbyhq.com`)
Prominent among modern cloud, AI, and data consultancies.

```text
site:jobs.ashbyhq.com ("[TechStack]" OR "[PartnerEcosystem]") ("client" OR "consulting" OR "partner" OR "implementation") ("Architect" OR "Consultant" OR "Lead")
```

*Examples:*
- `site:jobs.ashbyhq.com "Snowflake" ("clients" OR "consulting" OR "partner") "Solutions Architect"`
- `site:jobs.ashbyhq.com "Kafka" ("implementation" OR "client engagement") "Delivery"`
- `site:jobs.ashbyhq.com "Supabase" ("consultancy" OR "agency" OR "client")`

### Greenhouse (`boards.greenhouse.io`)
Used by established systems integrators and regional consultancies.

```text
site:boards.greenhouse.io ("[TechStack]") ("Solutions Architect" OR "Implementation Consultant") ("clients" OR "customers")
```

*Examples:*
- `site:boards.greenhouse.io "Datadog" ("Implementation" OR "Solutions Architect") "client"`
- `site:boards.greenhouse.io "Kubernetes" ("consulting" OR "client delivery") "Staff Architect"`

### Lever (`jobs.lever.co`)
Used by high-growth specialized agencies and distributed technical service providers.

```text
site:jobs.lever.co ("[TechStack]") ("systems integrator" OR "professional services" OR "client delivery")
```

---

## 2. Public Partner Directories & Ecosystem Marketplaces

Major platforms publish verified directories of certified consulting and systems integration partners.

### Cloud Provider Partner Registries:
- **AWS Partner Network (APN)**: `partners.amazonaws.com`
  - Search operators: `site:partners.amazonaws.com "[TechStack]" "Consulting Partner"`
  - Filter by tier: Premier, Advanced, Select tier partners.
- **Microsoft AppSource / Azure Marketplace**: `appsource.microsoft.com`
  - Search operators: `site:appsource.microsoft.com/marketplace/consulting-services "[TechStack]"`
- **Google Cloud Partner Directory**: `cloud.google.com/find-a-partner`
  - Search operators: `site:cloud.google.com/find-a-partner "[TechStack]"`

### SaaS & Infrastructure Vendor Directories:
- **Snowflake Partner Network**: `site:snowflake.com/partners "Services"`
- **Datadog Partner Network**: `site:datadog.com/partners/service-providers`
- **Shopify Plus Partners**: `site:shopify.com/plus/partners`
- **HubSpot Solutions Directory**: `site:ecosystem.hubspot.com/marketplace/solutions`
- **Stripe Partner Directory**: `site:stripe.com/partners/directory`

---

## 3. Agency Review Directories & Registries

### Clutch.co
Clutch is the largest index of verified B2B service providers, IT consultancies, and software development agencies.

```text
site:clutch.co/it-services "[TechStack]" "clients"
site:clutch.co/developers "[TechStack]" "case study"
```

*Examples:*
- `site:clutch.co/it-services "Apache Kafka"`
- `site:clutch.co/it-services "Snowflake" "cloud migration"`

### G2 Service Providers
```text
site:g2.com/categories/systems-integrators "[TechStack]"
site:g2.com/categories/cloud-consulting-providers "[TechStack]"
```

---

## 4. Case Studies & Service Practice Pages

High-intent evidence comes directly from the agency's own domain where they showcase customer case studies and specialized service offerings.

```text
site:*.com/case-studies ("deployed" OR "implemented" OR "migrated") "[TechStack]"
site:*.com/services ("implementation" OR "systems integration" OR "migration practice") "[TechStack]"
```

---

## 5. Compiling Discovered Records into `partners.csv`

Format discovered hits into `partners.csv` with these exact columns:

```csv
item_id,text,source_uri
slalom.com,"As a premier cloud consulting partner, Slalom works with Fortune 500 enterprises to architect and deliver large-scale Snowflake and Databricks data modernization initiatives. Our certified Solutions Architects lead turnkey migrations...","https://jobs.ashbyhq.com/slalom/sr-snowflake-architect"
trace3.com,"Trace3 is an advanced systems integrator delivering cloud architecture, security, and data streaming services. Case Study: Leading the Apache Kafka cluster migration for a top-10 fintech client...","https://trace3.com/case-studies/kafka-migration"
dev_boutique.io,"We are a specialized engineering consultancy helping scaleups deploy Kubernetes and Supabase. Our team provides custom systems integration, performance tuning, and managed infrastructure...","https://boards.greenhouse.io/devboutique/lead-consultant"
```

### Ingestion Requirements:
1. `item_id`: Use the clean canonical agency domain (e.g. `slalom.com`, `trace3.com`).
2. `text`: Preserve the raw paragraph or sentence describing the consulting practice, client case study, or client-facing role. Do not summarize or alter text.
3. `source_uri`: Include the live URL so partner managers can inspect the posting or case study directly.
