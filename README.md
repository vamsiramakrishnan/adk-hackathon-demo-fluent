# NOC Command — Proactive Network Outage Communication Agent

A multi-agent system built with [Google ADK](https://google.github.io/adk-docs/) and [adk-fluent](https://github.com/vamsiramakrishnan/adk-fluent) that transforms telco network outage response from reactive chaos into proactive, high-touch customer communication.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-Apache%202.0-green)

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the Dashboard](#running-the-dashboard)
- [Configuration Reference](#configuration-reference)
- [Data Generation](#data-generation)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [How It Works — Step by Step](#how-it-works--step-by-step)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## The Problem

When a network outage hits, telcos are immediately on the back foot — flooded support lines, angry enterprise clients watching SLA clocks tick, and no coordinated communication strategy. Response is slow, manual, and fails to prioritize the customers who matter most.

## The Solution

NOC Command activates the instant a critical network fault is detected. It analyzes the technical problem, identifies business impact, and orchestrates a targeted communication strategy in minutes — not hours.

---

## Architecture

### Agent Pipeline

```
                                                        ┌─ Enterprise Comm Drafter (Gemini Pro)
Alert ─→ Network Analyst ─→ Customer Impact Analyst ─→ ├─ VIP Residential Drafter  (Gemini Flash)    ─→ Approval Summarizer
         (Gemini Pro)        (Gemini Flash)             └─ Mass Notification Drafter (Gemini Flash Lite)  (Gemini Flash)
                                                          ↑ parallel fan-out (|)
```

| Agent | Model | What it does |
|-------|-------|--------------|
| **Network Analyst** | `gemini-3.1-pro-preview` | Parses raw alerts, identifies root cause, blast radius, affected zones, and ETR |
| **Customer Impact Analyst** | `gemini-3-flash-preview` | Cross-references affected zones with customer DB; stratifies by tier (life-safety, enterprise, VIP, residential) |
| **Enterprise Comm Drafter** | `gemini-3.1-pro-preview` | Formal, SLA-aware notifications for enterprise and government accounts |
| **VIP Residential Drafter** | `gemini-3-flash-preview` | Warm, empathetic SMS + email for VIP residential customers |
| **Mass Notification Drafter** | `gemini-3.1-flash-lite` | SMS blasts, push notifications, status page updates for general subscribers |
| **Approval Summarizer** | `gemini-3-flash-preview` | Consolidates everything into an executive approval dashboard for one-click send |

### Built with adk-fluent

The entire pipeline is composed using adk-fluent's expression operators — `>>` for sequential chaining, `|` for parallel fan-out, and state accessors for inter-agent data flow:

```python
outage_response_pipeline = (
    S.capture("alert_text")
    >> network_analyst
    >> customer_impact_analyst
    >> (enterprise_drafter | vip_drafter | mass_drafter)  # parallel fan-out
    >> approval_summarizer
)
```

### Data Flow Between Agents

Each agent writes its output to a named state key (`.writes("key")`), and downstream agents read from those keys via `.context(C.from_state("key"))`:

```
network_analyst        ──writes──→  "network_analysis"
customer_impact_analyst ──writes──→  "customer_impact_report"
enterprise_drafter     ──writes──→  "enterprise_communications"
vip_drafter            ──writes──→  "vip_communications"
mass_drafter           ──writes──→  "mass_communications"
approval_summarizer    ──reads all of the above──→  final output
```

### Tool Functions

Agents interact with simulated backend systems via five tool functions defined in `network_outage_agent/tools.py`:

| Tool | Used by | Purpose |
|------|---------|---------|
| `get_all_active_alerts()` | Network Analyst | Lists all current alerts from the monitoring system |
| `query_network_alerts(alert_id, severity, alert_type)` | Network Analyst | Gets full technical details for a specific alert |
| `get_affected_customers(zones)` | Customer Impact Analyst | Queries customer DB by affected zone IDs |
| `get_customer_sla_details(account_id)` | Customer Impact Analyst | Gets full SLA/contract details for a specific account |
| `log_communication_action(account_id, channel, message_type, status)` | Comm Drafters | Logs drafted communications for audit trail |

---

## Prerequisites

| Requirement | Version | Install |
|-------------|---------|---------|
| **Python** | 3.11+ | [python.org](https://www.python.org/downloads/) |
| **uv** | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Google Cloud account** | — | [console.cloud.google.com](https://console.cloud.google.com) |

You need **one** of the following for Gemini model access:

- **Vertex AI** (recommended) — a GCP project with the Vertex AI API enabled
- **Google AI Studio** — a Gemini API key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/vamsiramakrishnan/adk-hackathon-demo-fluent.git
cd adk-hackathon-demo-fluent
```

### 2. Install dependencies

```bash
uv sync
```

This installs all Python dependencies including `adk-fluent` (fetched automatically from its git repository), `google-adk`, `FastAPI`, `uvicorn`, and `sse-starlette`.

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials. Choose **one** of the two options:

**Option A — Vertex AI (recommended for production)**

```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
```

Make sure you are authenticated with `gcloud`:

```bash
gcloud auth application-default login
gcloud config set project your-gcp-project-id
```

**Option B — Google AI Studio (simpler for local dev)**

```env
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your-gemini-api-key
```

### 4. Verify the setup

```bash
uv run python -c "from network_outage_agent.agent import root_agent; print('Agent loaded:', root_agent.name)"
```

If this prints the agent name without errors, you're ready to go.

---

## Running the Dashboard

### Start the server

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8080
```

Open [http://localhost:8080](http://localhost:8080) in your browser.

### Using the dashboard

1. The dashboard displays all active network alerts loaded from `network_outage_agent/data/network_alerts.json`
2. Click on any alert card to trigger the multi-agent pipeline
3. Watch each agent stage execute in real time via Server-Sent Events (SSE):
   - **Stage 1** — Network Analyst analyzes the alert, calls tools to fetch technical details
   - **Stage 2** — Customer Impact Analyst queries the customer database for affected accounts
   - **Stage 3a/b/c** — Three communication drafters run in parallel, each tailored to their audience
   - **Stage 4** — Approval Summarizer compiles everything into an executive dashboard
4. The final output is an approval dashboard with all drafted communications, ready for one-click send

### Auto-reload for development

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8080 --reload
```

---

## Configuration Reference

### Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_GENAI_USE_VERTEXAI` | Yes | — | `TRUE` for Vertex AI, `FALSE` for Google AI Studio |
| `GOOGLE_CLOUD_PROJECT` | If Vertex AI | — | Your GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | If Vertex AI | `global` | GCP region (`global`, `us-central1`, etc.) |
| `GOOGLE_API_KEY` | If AI Studio | — | Gemini API key from AI Studio |

### Model configuration

Models are set in `network_outage_agent/agent.py`:

```python
PRO   = "gemini-3.1-pro-preview"      # Network Analyst, Enterprise Drafter
FLASH = "gemini-3-flash-preview"     # Customer Impact, VIP Drafter, Approval
LITE  = "gemini-3.1-flash-lite"        # Mass Notification Drafter
```

Change these to use different Gemini model versions or to swap in cheaper/faster models for development.

---

## Data Generation

The project includes a deterministic data generator that creates realistic network alerts and customer account databases.

### Regenerate demo data

```bash
# Default demo preset (3 alerts, 15 customers, seed 42)
uv run python -m network_outage_agent.data.seed_generator --preset demo
```

### Available presets

| Preset | Seed | Alerts | Customers | Use case |
|--------|------|--------|-----------|----------|
| `demo` | 42 | 3 | 15 | Default demo — quick runs |
| `small` | 1 | 1 | 5 | Minimal testing |
| `medium` | 99 | 10 | 100 | Moderate load testing |
| `stress-test` | 7 | 25 | 500 | High-volume scenarios |
| `large` | 2026 | 50 | 1,000 | Full-scale simulation |

### Custom data generation

```bash
# Custom: 5 alerts, 50 customers, seed 123
uv run python -m network_outage_agent.data.seed_generator --seed 123 --alerts 5 --customers 50

# Output to a different directory
uv run python -m network_outage_agent.data.seed_generator --preset medium --output-dir ./my-data
```

The generator is **deterministic** — the same seed always produces the same dataset, making demos reproducible.

### Generated customer types

The generator creates a realistic distribution of account types:

| Type | % of total | Examples |
|------|-----------|----------|
| Platinum Enterprise | ~10% | Hospitals, financial institutions (life-safety, 99.999% SLA) |
| Gold Enterprise | ~15% | Logistics, manufacturing, insurance (99.99% SLA) |
| Silver Enterprise | ~15% | Schools, hotels, law firms (99.9% SLA) |
| Government | ~10% | Police, fire, emergency management (life-safety) |
| VIP Residential | ~10% | Public figures, executives (high reputational risk) |
| SMB | ~25% | Restaurants, clinics, dealerships (no SLA) |
| Residential Bulk | 1 entry | Aggregated subscriber counts per zone |

---

## Deployment

### Docker (local)

```bash
docker build -t noc-command .
docker run -p 8080:8080 --env-file .env noc-command
```

### Google Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT/noc-command

# Deploy
gcloud run deploy noc-command \
  --image gcr.io/YOUR_PROJECT/noc-command \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT,GOOGLE_CLOUD_LOCATION=global
```

> **Note:** The Dockerfile currently copies `.env` into the image. For production, remove that line and pass environment variables at deploy time (as shown above) or use Secret Manager.

---

## Project Structure

```
adk-hackathon-demo-fluent/
├── network_outage_agent/           # Core agent package
│   ├── __init__.py
│   ├── agent.py                    # Multi-agent pipeline definition
│   │                                 - 6 agents composed with >> and | operators
│   │                                 - State flow via .writes() and C.from_state()
│   │                                 - Prompt engineering with P.role() + P.task() + P.constraint()
│   ├── tools.py                    # Tool functions for agents
│   │                                 - Loads JSON data at import time
│   │                                 - 5 tools: alert queries, customer lookup, SLA details, action logging
│   └── data/
│       ├── network_alerts.json     # Simulated network monitoring alerts (3 by default)
│       ├── customer_accounts.json  # Simulated customer database (15 accounts by default)
│       └── seed_generator.py       # Deterministic data generator with presets
│
├── server.py                       # FastAPI application
│                                     - GET /             → Dashboard UI
│                                     - GET /api/alerts   → List all alerts
│                                     - GET /api/alerts/{id} → Alert detail
│                                     - GET /api/run/{id} → SSE stream of agent pipeline execution
│                                     - InMemoryRunner for agent sessions
│
├── static/
│   └── index.html                  # NOC Command dashboard (single-file frontend)
│                                     - Dark-themed NOC-style interface
│                                     - Real-time SSE streaming with stage indicators
│                                     - Alert cards, pipeline visualization, markdown rendering
│
├── pyproject.toml                  # Project metadata and dependencies
├── .env.example                    # Environment variable template
├── .python-version                 # Python 3.11
├── Dockerfile                      # Container image for Cloud Run
├── .dockerignore
├── .gitignore
├── LICENSE                         # Apache 2.0
└── use-case.md                     # Original hackathon use case brief
```

---

## API Reference

The server exposes the following endpoints:

### `GET /`

Serves the NOC Command dashboard UI.

### `GET /api/alerts`

Returns all active network alerts as JSON.

```bash
curl http://localhost:8080/api/alerts | python -m json.tool
```

### `GET /api/alerts/{alert_id}`

Returns full details for a specific alert.

```bash
curl http://localhost:8080/api/alerts/ALT-2026-03-10-4150
```

### `GET /api/run/{alert_id}`

Triggers the multi-agent pipeline for the given alert and streams results via SSE.

```bash
curl -N http://localhost:8080/api/run/ALT-2026-03-10-4150
```

**SSE event types:**

| Event | Payload | Description |
|-------|---------|-------------|
| `pipeline_start` | `{alert_id, ts}` | Pipeline execution has begun |
| `stage_start` | `{stage, label, icon, order}` | A new agent has started processing |
| `text` | `{stage, text}` | Text output from the current agent |
| `tool_call` | `{stage, tool, args}` | Agent is calling a tool function |
| `tool_result` | `{stage, tool}` | Tool function returned a result |
| `stage_done` | `{stage, label}` | Agent has finished processing |
| `error` | `{error}` | An error occurred during execution |
| `done` | `{ts}` | Pipeline execution is complete |

---

## How It Works — Step by Step

### 1. Alert Ingestion

The server loads simulated network alerts from `network_alerts.json` at startup. Each alert contains structured data: severity, affected infrastructure (nodes, cell towers, distribution hubs), affected zones (`ZONE-XX-XX` format), impacted services, redundancy status, field crew dispatch info, and related cascading alerts.

### 2. Network Analysis (Agent 1)

When an alert is selected, the **Network Analyst** agent (Gemini Pro) receives the alert text and:
- Calls `get_all_active_alerts()` to see the full picture
- Calls `query_network_alerts(alert_id)` to get deep technical details
- Analyzes related alerts for cascading failures
- Produces a structured assessment: root cause, blast radius (zone list), services impacted, redundancy status, ETR, risk factors, and severity rating
- Writes output to session state as `network_analysis`

### 3. Customer Impact Assessment (Agent 2)

The **Customer Impact Analyst** (Gemini Flash) reads the `network_analysis` from state and:
- Extracts affected zone IDs from the analysis
- Calls `get_affected_customers(zones)` to query the customer database
- Calls `get_customer_sla_details(account_id)` for LIFE_SAFETY and PLATINUM accounts
- Produces a prioritized impact report: critical (15-min SLA), high (30-min), medium (1-hr), mass notification (2-hr)
- Calculates total SLA credit exposure in dollars
- Writes output to state as `customer_impact_report`

### 4. Communication Drafting (Agents 3a, 3b, 3c — Parallel)

Three agents run simultaneously via adk-fluent's `|` (fan-out) operator, each reading `network_analysis` and `customer_impact_report` from state:

- **Enterprise Comm Drafter** — Formal, technical notifications for each enterprise/government account. References SLA tiers, provides incident bridge numbers, commits to update cadence.
- **VIP Residential Drafter** — Warm SMS (< 300 chars) + email for each VIP customer. Empathetic tone, no jargon, proactive service credit offer.
- **Mass Notification Drafter** — SMS blast (< 160 chars), app push notification, status page update, and email template for general subscribers.

Each drafter calls `log_communication_action()` to create an audit trail.

### 5. Approval Dashboard (Agent 4)

The **Approval Summarizer** (Gemini Flash) reads all five state keys and produces an executive dashboard:
- Incident overview (ID, root cause, ETR, total affected)
- Communications queue table (every message to be sent, numbered)
- Financial exposure summary (total SLA credit liability)
- Approval action items with priority timeline
- Ends with "Awaiting one-click approval to begin dissemination"

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'adk_fluent'`

Run `uv sync` to install dependencies. If the issue persists, ensure you're running commands with `uv run` (not bare `python`).

### `google.auth.exceptions.DefaultCredentialsError`

For Vertex AI: run `gcloud auth application-default login` and ensure your project has the Vertex AI API enabled.

### `400 Model not found` or model errors

The agents use `gemini-3.1-pro-preview`, `gemini-3-flash-preview`, and `gemini-3.1-flash-lite`. Ensure these models are available in your region. You can change model names in `network_outage_agent/agent.py`.

### Port already in use

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 9090  # use a different port
```

### SSE stream disconnects or hangs

The pipeline runs 6 agents sequentially (with 3 in parallel). A full run can take 30-60 seconds depending on model latency. If it hangs beyond 2 minutes, check your API quota and model availability.

---

## License

[Apache 2.0](LICENSE)
