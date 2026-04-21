# Master Prompt: OpenMetadata Hackathon Strategy Session

> Copy and paste this entire prompt into any AI (Claude, GPT-4, Gemini) to reproduce this context and continue strategic planning.

---

## WHO I AM

I am **Mehboob**, a Software Engineer II with ~2.5 years of experience based in Bangalore/Chennai, India.

**Core technical stack:**
- Backend: Django / Django REST Framework, FastAPI
- Infrastructure: Docker, Kubernetes (basics), AWS, Nginx
- Data: PostgreSQL, Redis, RabbitMQ, Celery
- Observability: OpenTelemetry, Prometheus, Grafana
- Media: FFmpeg, HLS, DASH (video streaming)
- Realtime: WebSocket, WebRTC
- AI/ML: LLM integrations, multi-agent systems, computer vision pipelines

**Recent project (last hackathon):**
I built **Drishti AI** — a real-time AI eye screening system for rural India. It uses Vision Agents SDK (WebRTC), Gemini Live (speech-to-speech Hindi), MediaPipe, OpenCV, Roboflow (3 CV models), and Moondream VQA in a 5-layer ML pipeline. Backend: Django (234 tests) + FastAPI (275 tests) + React Native ASHA worker app + React web PHC admin dashboard. 500+ total tests. Deployed on 9 Docker containers. Built solo in 7 days.

**Portfolio:** https://mahboob.engineer  
**Hackathon writeup:** https://imehboob.medium.com/drishti-ai-building-an-ai-eye-screening-agent-for-rural-india-in-7-days-2fc3d4ccc1fe

I operate as a **solo founder** exploring SaaS for the Indian market. I use AI-assisted development heavily (Codebuff, Cursor, Claude). I care deeply about building from first principles and solving real problems.

---

## THE HACKATHON

**Event:** WeMakeDevs × OpenMetadata Hackathon  
**URL:** https://www.wemakedevs.org/hackathons/openmetadata  
**Dates:** April 17 – April 26, 2026 (10 days)  
**Format:** Solo participation, AI-assisted development explicitly allowed  
**Prizes:** MacBook (1st), iPad (2nd), Keychron keyboard (3rd) + job interviews at Collate

**Six competition tracks (called "Temporal Paradoxes"):**

| # | Track | Focus |
|---|-------|-------|
| T-01 | MCP Ecosystem & AI Agents | MCP servers, AI agents, natural language metadata queries, auto-classification |
| T-02 | Data Observability | Monitoring dashboards, anomaly detection, pipeline health, data quality alerts |
| T-03 | Connectors & Ingestion | New connectors, ETL integrations, metadata ingestion to new platforms |
| T-04 | Developer Tooling & CI/CD | CLI tools, GitHub Actions, IDE plugins, developer utilities |
| T-05 | Community & Comms Apps | Slack bots, notification systems, collaboration tools |
| T-06 | Governance & Classification | Auto-tagging, PII detection, compliance tools, policy enforcement |

**Judging criteria (in order of weight):**
1. Potential Impact
2. Creativity & Innovation
3. Technical Excellence
4. Best Use of OpenMetadata
5. User Experience
6. Presentation Quality

**Project ideas board (official):** https://github.com/orgs/open-metadata/projects/107/views/1

---

## WHAT IS OPENMETADATA (Brief Context)

OpenMetadata is an **open-source unified metadata platform** for:
- **Data Discovery** — find what data exists, what it means, who owns it
- **Data Lineage** — column-level lineage: how data flows from source → transformation → dashboard
- **Data Observability** — automated data quality tests, anomaly detection, pipeline health monitoring
- **Data Governance** — tagging, PII detection, classification, ownership, compliance policies

**Key technical facts:**
- Architecture: 4 core components (API Server, Metadata Store, Search Index via Elasticsearch, Ingestion Framework)
- 90+ connectors for databases, warehouses, pipelines, dashboards, ML platforms
- Schema-first approach: everything is typed JSON Schema
- API-first: every feature is exposed via REST API
- MCP Server built-in: connects LLMs/AI agents to the entire metadata graph
- Unified Knowledge Graph: tables, dashboards, pipelines, ML models, users, teams, glossaries all linked
- Self-hostable via Docker or Kubernetes

**MCP integration:**
OpenMetadata ships an enterprise-grade MCP server. AI agents (Claude, GPT, custom) can:
- Search and discover data assets via natural language
- Read/write lineage
- Create/update glossary terms
- Trigger data quality tests
- Enforce governance policies programmatically
- All with the same RBAC/auth as the REST API

---

## THE TASK I NEED HELP WITH

I want you to act as my **strategic hackathon advisor + technical co-pilot**. You know my background, my stack, the hackathon constraints, and OpenMetadata deeply.

**I need you to help me with the following (respond to each section separately):**

### Section 1: Strategic Project Selection
Given my background (Django/FastAPI, Docker, AI agents, observability, solo, 10 days), which of the 10 project ideas in the companion document (`c_hackathon_ideas.md`) do you think I should build? Rank the top 3 with reasoning covering: feasibility in 10 days solo, judging score potential, differentiation, and alignment to my stack.

### Section 2: Deep Technical Architecture
For the top recommended idea, give me:
- Full system architecture (components, data flow, API contracts)
- What OpenMetadata APIs/features I must use
- What external technologies I need
- What I can skip to hit MVP in 10 days
- Folder structure
- Day-by-day 10-day build plan

### Section 3: Demo Script & Judging Preparation
Help me design a 5-minute demo that maximizes the judging score. What story do I tell? What does the judge see first? What screenshots/videos do I capture?

### Section 4: README & Submission
Help me write a competition-grade README.md and submission description that scores high on Presentation Quality.

---

## COMPANION DOCUMENTS

This prompt is part of a set of 3 documents I generated before starting:
- `a_master_prompt.md` — this file (context + task)
- `b_openmetadata_deep_dive.md` — complete OpenMetadata understanding
- `c_hackathon_ideas.md` — 10 unique project ideas

Read all three before responding. They are in the same folder.

---

## MY WORKING CONSTRAINTS

- **Time:** 10 days, solo, working ~6–8 hours/day (evenings + weekend)
- **Tools allowed:** AI coding assistants (Claude, Codebuff, Cursor), any framework
- **Stack preference:** Python (Django/FastAPI), Docker, can add Node.js/React for frontend if needed
- **Deployment:** Local demo is acceptable (per hackathon rules), but I prefer a live URL if time allows
- **OpenMetadata setup:** I will run it locally via Docker Compose
- **Quality bar I set for myself:** Production-grade code, tests where it matters, Prometheus metrics, clean README

---

*End of master prompt. If you are an AI reading this, you now have full context. Begin with Section 1 first.*
