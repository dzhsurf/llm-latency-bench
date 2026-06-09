from __future__ import annotations

from tools.seeds.types import Seed

DOC_NORMAL_TASKS = [
    (
        "For EACH section below, write a detailed analysis with: "
        "(1) Section Summary — 3-5 sentences; "
        "(2) Key Facts — bullet list of 5+ facts with verbatim quotes from the source as evidence; "
        "(3) Reasoning — how you derived each conclusion from the quoted text; "
        "(4) Implications — what these facts mean for stakeholders. "
        "Process every section. Cite source lines throughout."
    ),
    (
        "For EACH section below, extract and catalog: "
        "(1) Named Entities — people, orgs, products with quoted mentions; "
        "(2) Dates and Timelines — every date with context quote; "
        "(3) Numeric Metrics — every number with unit and source quote; "
        "(4) Cross-References — connections between entities across sections with reasoning. "
        "Be exhaustive. Quote the original text for every extraction."
    ),
    (
        "For EACH section below, perform risk analysis: "
        "(1) Quote passages that indicate risk or contradiction; "
        "(2) Explain the risk with step-by-step reasoning; "
        "(3) Identify missing information and why it matters; "
        "(4) Rate severity (low/medium/high) with justification citing evidence. "
        "Cover all sections. Do not skip ambiguous passages."
    ),
    (
        "For EACH section below, produce a structured outline: "
        "(1) Heading hierarchy with one-line summaries; "
        "(2) For each heading, quote the most important sentence from source; "
        "(3) Reasoning chain linking sections together; "
        "(4) Open questions raised by the material. "
        "Map the entire document. Include direct quotes."
    ),
    (
        "For EACH section below, identify decisions: "
        "(1) What decision was made — quote the passage; "
        "(2) Who made it — quote attribution; "
        "(3) Evidence supporting the decision — quote with reasoning; "
        "(4) Dissenting views or alternatives mentioned — quote if present. "
        "Extract every decision. Cite all evidence verbatim."
    ),
]

DOC_STRUCTURED_TASKS = [
    (
        "Return ONLY valid JSON with this schema: "
        "{summary (string, 3+ sentences), "
        "sections (array of {heading, summary, key_facts (array of {fact, evidence_quote}), "
        "reasoning, implications}), "
        "entities (array of {name, type, mentions (array of quotes)}), "
        "dates (array of {date, context, evidence_quote}), "
        "metrics (array of {name, value, unit, evidence_quote})}. "
        "Process all sections. No markdown fences."
    ),
    (
        "Return ONLY valid JSON with this schema: "
        "{risks (array of {description, severity, evidence_quote, reasoning, mitigation}), "
        "contradictions (array of {passage_a_quote, passage_b_quote, explanation}), "
        "missing_info (array of {topic, why_it_matters, suggested_followup})}. "
        "Cover every section. No markdown fences."
    ),
    (
        "Return ONLY valid JSON with this schema: "
        "{outline (array of {level, heading, summary, key_quote, reasoning}), "
        "timeline (array of {date, event, evidence_quote, significance}), "
        "cross_references (array of {from_section, to_section, connection, evidence})}. "
        "Map the full document. No markdown fences."
    ),
    (
        "Return ONLY valid JSON with this schema: "
        "{decisions (array of {decision, decision_maker, evidence_quotes (array), "
        "reasoning, alternatives_mentioned, outcome}), "
        "action_items (array of {description, owner, deadline, evidence_quote, status})}. "
        "Extract all decisions and action items. No markdown fences."
    ),
    (
        "Return ONLY valid JSON with this schema: "
        "{executive_summary (string, 5+ sentences for non-technical audience), "
        "goals (array of {goal, evidence_quote}), "
        "outcomes (array of {outcome, evidence_quote}), "
        "gaps (array of {stated_goal, actual_outcome, gap_description, evidence_quotes}), "
        "recommendations (array of {recommendation, reasoning, priority})}. "
        "Compare goals vs outcomes with quoted evidence. No markdown fences."
    ),
]

# Backward-compatible alias: normal cases 1-5, structured cases 6-10
DOC_TASKS = DOC_NORMAL_TASKS + DOC_STRUCTURED_TASKS

DOC_SEEDS: list[Seed] = [
    Seed(
        "incident_postmortem",
        "Incident Postmortem: Payment API Outage",
        '''On 2026-03-14 between 02:11 and 03:47 UTC, payment authorization success rate dropped from 99.2% to 61.4%.
Root cause: a misconfigured connection pool max size (200) on checkout-api exceeded database max connections (180).
Customer impact: 18,442 failed checkouts, estimated revenue at risk $1.2M.
Detection: PagerDuty alert on error rate at 02:18 UTC; on-call SRE joined bridge at 02:24.
Mitigation: rolled back deploy checkout-api v2.14.3 -> v2.14.2 at 02:39; pool size restored to 120.
Follow-ups: add pre-deploy load test, enforce pool limit via config validation, add synthetic checkout probe.''',
    ),
    Seed(
        "api_spec_users",
        "REST API Spec: Users Service",
        '''GET /v1/users/{id}
Response 200: {"id":"string","email":"string","created_at":"iso8601","status":"active|suspended"}
Response 404: {"error":"user_not_found"}
Rate limit: 1200 requests/min per API key.
Auth: Bearer token with scope users:read.

PATCH /v1/users/{id}
Body: {"status":"active|suspended"}
Response 200: updated user object
Validation: status required; idempotent for same value.''',
    ),
    Seed(
        "db_schema_orders",
        "Database Schema: Orders",
        '''Table orders(id BIGINT PK, user_id BIGINT, total_cents INT, currency CHAR(3), status VARCHAR(32), created_at TIMESTAMP)
Index orders_user_id_created_at(user_id, created_at DESC)
Table order_items(id BIGINT PK, order_id BIGINT FK, sku VARCHAR(64), qty INT, unit_price_cents INT)
Constraint: sum(order_items.qty * unit_price_cents) must equal orders.total_cents at commit.
Status transitions: pending -> paid -> fulfilled; pending -> cancelled; paid -> refunded.''',
    ),
    Seed(
        "quarterly_metrics",
        "Quarterly Business Metrics",
        '''Q1 2026 highlights:
- MAU grew 12% QoQ to 4.8M; DAU/MAU ratio 0.31.
- Net revenue retention 118%; gross margin 72%.
- Support tickets per 1k users decreased from 9.1 to 7.4 after chatbot rollout.
- Churn in enterprise segment rose 0.6pp due to pricing changes in EU.
Leadership asks for deeper cohort analysis on EU enterprise churn before Q2 pricing review on April 22.''',
    ),
    Seed(
        "security_audit",
        "Security Audit Findings",
        '''Finding SEC-014 (High): admin endpoints accept JWT without audience claim validation.
Finding SEC-021 (Medium): S3 bucket logs-archive allows public list due to legacy policy.
Finding SEC-033 (Low): dependency requests==2.28.1 has known CVE; upgrade to 2.32.0 planned.
Remediation owner: platform-security. Deadline: critical in 7 days, medium in 30 days.''',
    ),
    Seed(
        "k8s_runbook",
        "Kubernetes Runbook: Pod CrashLoop",
        '''Symptoms: Deployment replicas unavailable; kubectl shows CrashLoopBackOff.
Steps:
1. kubectl logs deploy/<name> --previous
2. Check recent configmap/secret changes in last 2h.
3. Verify image tag and pull secrets.
4. If OOMKilled, increase memory limit or profile heap.
Escalation: page service owner if error rate >5% for 10 minutes.''',
    ),
    Seed(
        "privacy_policy_excerpt",
        "Privacy Policy Excerpt",
        '''We collect account email, usage telemetry, and payment metadata processed by Stripe.
Telemetry retention: 13 months; deletion requests honored within 30 days.
EU users may exercise GDPR rights via privacy@example.com.
Third-party subprocessors listed at example.com/legal/subprocessors (updated Jan 2026).''',
    ),
    Seed(
        "meeting_notes",
        "Product Planning Meeting Notes",
        '''Attendees: PM(Ava), Eng(Leo), Design(Mina), Data(Sam)
Decision: ship smart compose v1 behind feature flag rollout 5% -> 25% -> 100%.
Open question: latency budget for compose endpoint remains 800ms p95.
Action: Leo prototypes caching by Friday; Sam defines success metrics (accept rate, edit distance).''',
    ),
    Seed(
        "research_abstract",
        "Research Abstract: Retrieval Quality",
        '''We evaluate hybrid retrieval (BM25 + dense) on 2,400 enterprise support tickets.
Hybrid MRR@10 improves from 0.41 (BM25) and 0.46 (dense) to 0.53 combined.
Latency overhead: +38ms median from reranker cross-encoder.
Conclusion: hybrid retrieval is cost-effective for ticket deflection workflows.''',
    ),
    Seed(
        "sla_report",
        "SLA Report: Messaging Platform",
        '''January SLA target 99.95%; achieved 99.91%.
Top contributors to downtime: broker failover (14 min), bad deploy (9 min), vendor DNS (6 min).
Customer-facing credits triggered for 3 enterprise accounts totaling $42k.
February focus: multi-AZ quorum tuning and canary analysis automation.''',
    ),
    Seed(
        "onboarding_guide",
        "Engineer Onboarding Guide",
        '''Week 1: access setup, local dev via docker compose, read architecture RFC-001.
Week 2: ship a small bugfix with mentor review; shadow on-call for one shift.
Coding standards: black + ruff; PR requires 2 approvals and unit test coverage on changed lines.
Services map: gateway, auth, billing, notifications, search indexer.''',
    ),
    Seed(
        "customer_feedback",
        "Customer Feedback Summary",
        '''Top requests: SSO SAML (38 mentions), audit log export (27), finer RBAC (21).
Complaints: slow dashboard load in APAC (p95 3.4s), confusing billing invoices (19 tickets).
NPS moved from 34 to 41 after onboarding wizard release.
Sales notes enterprise deal ACME blocked on SOC2 Type II report due in May.''',
    ),
    Seed(
        "legal_contract_clause",
        "Contract Clause: Data Processing",
        '''Processor shall process personal data only on documented instructions.
Subprocessors require prior written notice with 15-day objection window.
Breach notification within 72 hours of becoming aware.
Data residency: primary EU (Frankfurt), backups EU (Dublin); no transfers outside SCCs.''',
    ),
    Seed(
        "ml_model_card",
        "Model Card: Churn Predictor v3",
        '''Intended use: rank accounts for customer success outreach; not for automated account closure.
Training data: 2023-01 to 2025-06 accounts with 90-day activity windows.
AUC 0.81 on holdout; calibration error 0.04.
Known limitations: underperforms on accounts <30 days old; sensitive to pricing changes.''',
    ),
    Seed(
        "terraform_notes",
        "Terraform Module Notes",
        '''Module vpc creates /16 with 3 public and 3 private subnets across AZs.
Outputs: vpc_id, private_subnet_ids, public_subnet_ids.
Consumers must pass environment tag; module enforces tag compliance via policy.
State backend: S3 + DynamoDB lock table terraform-locks-prod.''',
    ),
    Seed(
        "support_transcript",
        "Support Transcript",
        '''User: exports fail after 10k rows.
Agent: which format CSV or XLSX? any error message?
User: CSV; "timeout after 60s".
Agent: reproducing on export v2; workaround split by date range; engineering ticket ENG-8842 opened.
User requests ETA; agent commits to update within 2 business days.''',
    ),
    Seed(
        "rfc_cache",
        "RFC: Edge Cache Invalidation",
        '''Problem: stale content after CMS publish; current TTL 15 min unacceptable for news.
Proposal: publish events to Kafka topic cache-invalidate with path patterns.
Edge workers subscribe and purge matching keys; fallback TTL 5 min.
Tradeoff: added complexity vs near-real-time updates; estimated 2 engineer-months.''',
    ),
    Seed(
        "hiring_plan",
        "Hiring Plan H2",
        '''Open roles: 2 backend (payments), 1 SRE, 1 data engineer, 1 technical writer.
Priority: payments backend to unblock EU launch.
Interview loop: recruiter screen, coding, system design, values.
Target start dates: July-August; budget approved for levels L4-L5.''',
    ),
    Seed(
        "competitor_scan",
        "Competitor Scan",
        '''Competitor A launched AI assistant with 1.2s median response; pricing +15% for enterprise.
Competitor B open-sourced connector SDK; community traction on GitHub.
Our differentiation: on-prem deployment option and granular audit trails.
Risk: Competitor A bundling assistant at no extra cost in renewals.''',
    ),
    Seed(
        "inventory_snapshot",
        "Warehouse Inventory Snapshot",
        '''SKU-1001 keyboards: on_hand 420, reserved 58, inbound 200 ETA Apr 3.
SKU-2044 monitors: on_hand 90, reserved 110 -> backorder risk high.
SKU-3300 docks: on_hand 300, reserved 40; overstock in EU-West warehouse.
Ops recommends transfer 80 units monitors EU-West -> US-East.''',
    ),
    Seed(
        "clinical_trial_summary",
        "Clinical Trial Summary (Synthetic)",
        '''Phase II randomized, n=240, treatment vs placebo over 12 weeks.
Primary endpoint met: symptom score reduction 28% vs 11% (p<0.01).
Adverse events mild-moderate; 3 serious unrelated per investigator.
Next step: Phase III protocol submission targeted Q3.''',
    ),
    Seed(
        "city_budget",
        "City Budget Excerpt",
        '''FY2026 proposed allocation: education 38%, infrastructure 22%, public safety 18%.
Deficit gap $12M if transit expansion approved; council debate scheduled March 28.
Revenue drivers: property tax +3%, federal grant transit $8M conditional on match.''',
    ),
    Seed(
        "release_notes",
        "Release Notes v5.8",
        '''Added: bulk user import, webhook retries with exponential backoff.
Fixed: timezone bug in scheduled reports; memory leak in PDF renderer.
Deprecated: /v1/reports/async endpoint; removal in v6.0 October 2026.
Upgrade note: run migration script migrate_5_8.py before deploy.''',
    ),
    Seed(
        "architecture_overview",
        "Architecture Overview",
        '''Clients -> CDN -> API Gateway -> services (auth, catalog, orders, search).
Orders writes to Postgres; search indexer consumes outbox events to Elasticsearch.
Async jobs via SQS; idempotency keys stored in Redis 24h TTL.
Observability: OpenTelemetry traces, Prometheus metrics, Loki logs.''',
    ),
    Seed(
        "policy_remote_work",
        "Remote Work Policy",
        '''Employees may work remotely up to 3 days/week with manager approval.
Core collaboration hours 10:00-15:00 local time.
International remote requires HR and legal review; tax implications apply.
Equipment stipend $500 annually; security requires VPN and disk encryption.''',
    ),
    Seed(
        "dataset_dictionary",
        "Data Dictionary: events table",
        '''event_id STRING PK
user_id STRING nullable for anonymous events
event_name STRING e.g. signup, purchase, click
properties JSON serialized; max 8KB
received_at TIMESTAMP server ingest time; client_ts TIMESTAMP device time
PII fields hashed at ingestion per policy PRIV-002''',
    ),
    Seed(
        "marketing_campaign",
        "Marketing Campaign Brief",
        '''Campaign: Spring Launch; channels email + in-app + webinar.
Goal: 2,000 trial signups; budget $120k; duration Apr 1 - Apr 30.
Message pillars: faster onboarding, enterprise security, AI assist.
KPIs: CTR 3.5%, trial-to-paid 18%, CAC <$400.''',
    ),
    Seed(
        "vendor_comparison",
        "Vendor Comparison: Observability",
        '''Vendor X: strong tracing, higher cost at scale, good K8s integration.
Vendor Y: competitive pricing, weaker anomaly detection, fast setup.
Vendor Z: best ML alerts, requires 90-day baseline, SOC2 available.
Committee recommends pilot Vendor X in staging for 6 weeks.''',
    ),
    Seed(
        "training_curriculum",
        "Training Curriculum: ML Ops",
        '''Module 1 data versioning; Module 2 feature stores; Module 3 model registry;
Module 4 deployment patterns (canary, shadow); Module 5 monitoring drift.
Capstone: deploy sklearn model with CI and rollback.
Expected duration 4 weeks part-time.''',
    ),
    Seed(
        "foss_license_review",
        "Open Source License Review",
        '''Dependency libfasthash: Apache-2.0 OK.
Dependency pretty-log: MIT OK.
Dependency chartplus: AGPL-3.0 triggers copyleft review for networked use.
Action: legal to assess AGPL implications by April 10; alternative seek MIT library.''',
    ),
    Seed(
        "weather_alert",
        "Weather Alert Bulletin",
        '''Severe thunderstorm warning counties: River, Pine, Lake until 21:00.
Expected hail up to 2cm, winds 70 km/h, localized flooding low-lying roads.
Residents advised secure outdoor items; emergency services on standby.
School districts River and Pine dismissed early at 14:30.''',
    ),
    Seed(
        "user_research",
        "User Research Findings",
        '''Method: 12 interviews with finance admins; tasks create report, manage roles, export audit.
Pain points: multi-step export (7/12), unclear role permissions (5/12), slow search (4/12).
Delighters: inline validation, recent items panel.
Recommendation: simplify export modal to 2 steps; add role templates.''',
    ),
    Seed(
        "energy_report",
        "Energy Usage Report",
        '''Building A electricity Q1: 1.24 GWh (+6% YoY); peak demand 14:00-16:00 weekdays.
Solar generation 0.18 GWh; net grid draw 1.06 GWh.
Recommendation: shift batch jobs to off-peak; ROI 18 months on battery buffer pilot.''',
    ),
    Seed(
        "translation_glossary",
        "Translation Glossary Excerpt",
        '''EN "workspace" -> DE "Arbeitsbereich" (not Arbeitsplatz in product UI)
EN "billing" -> FR "facturation"
EN "role" -> ES "rol" (masculine in UI strings)
Note: avoid literal translation of "dashboard" in JP; use ダッシュボード accepted loanword.''',
    ),
    Seed(
        "procurement_rfp",
        "RFP Summary: Office Laptops",
        '''Quantity 350 units; delivery by June 15; warranty 3 years on-site.
Minimum specs: 16GB RAM, 512GB SSD, TPM 2.0, 1080p camera.
Evaluation weights: price 40%, performance 30%, support 20%, sustainability 10%.
Vendors invited: 4; questions due March 20; award April 5.''',
    ),
    Seed(
        "ethics_guidelines",
        "AI Ethics Guidelines",
        '''Prohibited uses: covert surveillance, discriminatory profiling, deceptive impersonation.
Required: human review for high-impact decisions; document model version and prompt.
Transparency: user-facing disclosure when content AI-generated.
Escalation path: ethics@example.com and review board monthly.''',
    ),
    Seed(
        "network_topology",
        "Network Topology Notes",
        '''DMZ hosts load balancers; app tier private subnets; DB tier no internet egress.
Inter-service mTLS via internal CA; cert rotation 90 days automated.
Egress allowlist for payment provider and email API only.
DR site mirrors core services; RPO 15 min RTO 2 h per BCP.''',
    ),
    Seed(
        "changelog_mobile",
        "Mobile App Changelog 3.2",
        '''3.2.0: offline mode for drafts; push notification preferences revamp.
3.2.1 hotfix: crash on iOS 17.2 when opening camera attachment.
Known issue: biometric login fails on Pixel 6 Pro workaround use PIN.
Rollout 10% staged; monitor crash-free sessions >99.5%.''',
    ),
    Seed(
        "board_summary",
        "Board Summary",
        '''Revenue beat plan by 4%; operating margin 11% vs 9% guide.
Cash runway 26 months at current burn.
Strategic options: expand APAC sales, acquire analytics startup, or deepen AI features.
Board approved APAC expansion pilot $3M; M&A review ongoing under NDA.''',
    ),
    Seed(
        "lab_protocol",
        "Lab Protocol: Sample Analysis",
        '''Step 1 calibrate spectrometer with standard S-100.
Step 2 prepare 3 replicates; record batch IDs.
Step 3 run scan 400-800nm; export CSV to LIMS.
QC: reference sample must be within 2% of baseline; else recalibrate.''',
    ),
]
