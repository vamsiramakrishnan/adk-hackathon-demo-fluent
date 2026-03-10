# NOC Command — Proactive Network Outage Communication Agent

A multi-agent system built with [Google ADK](https://google.github.io/adk-docs/) and [adk-fluent](https://github.com/vamsiramakrishnan/adk-fluent) that transforms telco network outage response from reactive chaos into proactive, high-touch customer communication.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-Apache%202.0-green)

## The Problem

When a network outage hits, telcos are immediately on the back foot — flooded support lines, angry enterprise clients watching SLA clocks tick, and no coordinated communication strategy. Response is slow, manual, and fails to prioritize the customers who matter most.

## The Solution

NOC Command activates the instant a critical network fault is detected. It analyzes the technical problem, identifies business impact, and orchestrates a targeted communication strategy in minutes — not hours.

### Agent Pipeline

```
Alert ─→ Network Analyst ─→ Customer Impact Analyst ─→ ┬─ Enterprise Comms  ─→ Approval Dashboard
                                                        ├─ VIP Residential
                                                        └─ Mass Notifications
```

| Agent | Model | Role |
|-------|-------|------|
| **Network Analyst** | Gemini Pro | Parses alerts, identifies root cause, blast radius, ETR |
| **Customer Impact Analyst** | Gemini Flash | Cross-references outage zones with customer DB, stratifies by SLA tier |
| **Enterprise Comm Drafter** | Gemini Pro | Formal technical notifications for enterprise/government accounts |
| **VIP Residential Drafter** | Gemini Flash | Warm, empathetic SMS + email for VIP residential customers |
| **Mass Notification Drafter** | Gemini Flash Lite | SMS blasts, push notifications, status page updates |
| **Approval Summarizer** | Gemini Flash | Executive approval dashboard for one-click send |

### Built with adk-fluent

The entire pipeline is composed using adk-fluent's expression operators:

```python
outage_response_pipeline = (
    S.capture("alert_text")
    >> network_analyst
    >> customer_impact_analyst
    >> (enterprise_drafter | vip_drafter | mass_drafter)  # parallel fan-out
    >> approval_summarizer
)
```

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- A [Google AI API key](https://aistudio.google.com/apikey)

### Setup

```bash
# Clone the repo
git clone https://github.com/vamsiramakrishnan/adk-hackathon-demo-fluent.git
cd adk-hackathon-demo-fluent

# Install dependencies (adk-fluent is fetched automatically via git)
uv sync

# Configure your environment
cp .env.example .env
# Edit .env with your GCP project ID (Vertex AI) or Google API key
```

### Run the Dashboard

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8080
```

Open [http://localhost:8080](http://localhost:8080) to access the NOC Command dashboard. Select an alert and watch the multi-agent pipeline analyze the outage, identify affected customers, draft communications, and produce an approval summary — all in real time via SSE streaming.

## Project Structure

```
├── network_outage_agent/
│   ├── agent.py              # Multi-agent pipeline definition
│   ├── tools.py              # Tool functions (alert queries, customer DB)
│   └── data/
│       ├── network_alerts.json    # Simulated network alerts
│       ├── customer_accounts.json # Simulated customer database
│       └── seed_generator.py      # Data generation utility
├── server.py                 # FastAPI server with SSE streaming
├── static/
│   └── index.html            # NOC Command dashboard frontend
├── pyproject.toml
└── .env.example
```

## How It Works

1. **Alert Ingestion** — Raw network alerts (fiber cuts, routing failures, power outages) are loaded from the monitoring system
2. **Network Analysis** — The Network Analyst agent queries all related alerts, identifies root cause, blast radius, and ETR
3. **Customer Impact** — The Impact Analyst cross-references affected zones with the customer database, stratifying by tier (life-safety, enterprise, VIP, residential)
4. **Parallel Drafting** — Three drafting agents run simultaneously, each tailored to their audience: formal SLA-aware enterprise notifications, warm VIP messages, and concise mass alerts
5. **Approval Dashboard** — Everything is consolidated into a single executive summary for human one-click approval before dissemination

## License

[Apache 2.0](LICENSE)
