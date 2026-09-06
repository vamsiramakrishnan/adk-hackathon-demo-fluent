# NOC Command

**Turn a simulated network alert into customer-impact analysis and three audience-specific communication drafts.**

A Google ADK demo that turns a simulated network outage into customer-impact analysis and drafted communications.

The pipeline is authored with `adk-fluent`. Two analysis agents run first, three audience-specific drafting agents fan out in parallel, and a final agent assembles the drafts for approval.

This repository uses simulated network and customer data. It does not connect to a production NOC, CRM, notification system, or SLA database by default.

## Run one outage all the way through

1. Follow [setup](#setup) and choose the configured model backend.
2. Start the [dashboard](#run-the-dashboard) and select an alert.
3. Inspect the affected infrastructure, customer impact, and three drafts.
4. Review the final approval view before connecting any real delivery system.

The data is simulated, but running the agents uses the configured model
service. Draft production and message delivery are separate: this demo does
not send customer notifications by default. The [demo-data section](#demo-data)
explains how to vary the scenario.


## Pipeline

```text
network alert
     │
     ▼
Network Analyst
     │
     ▼
Customer Impact Analyst
     │
     ├──────────────┬──────────────────┐
     ▼              ▼                  ▼
Enterprise       VIP Residential    Mass Notification
Drafter          Drafter            Drafter
     └──────────────┴──────────────────┘
                    │
                    ▼
             Approval Summarizer
```

The corresponding `adk-fluent` composition is:

```python
outage_response_pipeline = (
    S.capture("alert_text")
    >> network_analyst
    >> customer_impact_analyst
    >> (enterprise_drafter | vip_drafter | mass_drafter)
    >> approval_summarizer
)
```

Each stage writes to named session state. Downstream agents read the state they need rather than parsing prior console output.

## Agents

| Agent | Responsibility |
| --- | --- |
| Network Analyst | Read the selected alert and related network records; produce the affected infrastructure and zone set |
| Customer Impact Analyst | Map affected zones to simulated accounts and SLA records |
| Enterprise Drafter | Draft enterprise/government communication |
| VIP Residential Drafter | Draft VIP residential communication |
| Mass Notification Drafter | Draft broad subscriber/status communication |
| Approval Summarizer | Collect the three drafts into one approval view |

Model IDs are configured in `network_outage_agent/agent.py`. Preview model names change over time, so treat the source file as the current configuration rather than copying model IDs from this README into automation.

## Tools

The agents call functions in `network_outage_agent/tools.py`:

| Tool | Purpose |
| --- | --- |
| `get_all_active_alerts()` | List the simulated active alerts |
| `query_network_alerts(...)` | Read details for an alert |
| `get_affected_customers(zones)` | Find simulated accounts in affected zones |
| `get_customer_sla_details(account_id)` | Read the simulated SLA record |
| `log_communication_action(...)` | Record a drafted communication action |

These functions operate on demo data in the repository. A production integration would need its own authentication, authorization, error handling, audit, idempotency, and data-classification controls.

## Setup

Requirements:

- Python 3.11+
- `uv`
- either Vertex AI credentials or a Google AI Studio key

Clone and install:

```bash
git clone https://github.com/vamsiramakrishnan/adk-hackathon-demo-fluent.git
cd adk-hackathon-demo-fluent
uv sync
cp .env.example .env
```

Vertex AI configuration:

```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
```

Then authenticate Application Default Credentials:

```bash
gcloud auth application-default login
```

Google AI Studio configuration:

```env
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your-gemini-api-key
```

Verify the agent package loads:

```bash
uv run python -c "from network_outage_agent.agent import root_agent; print(root_agent.name)"
```

## Run the dashboard

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8080
```

Open `http://localhost:8080`.

The dashboard loads the checked-in alert data. Selecting an alert starts the agent pipeline and streams stage events to the browser with Server-Sent Events.

Development reload:

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8080 --reload
```

## HTTP surface

| Method and path | Purpose |
| --- | --- |
| `GET /` | Dashboard |
| `GET /api/alerts` | List simulated alerts |
| `GET /api/alerts/{alert_id}` | Read one simulated alert |
| `GET /api/run/{alert_id}` | Start the pipeline and stream SSE events |

Example:

```bash
curl -N http://localhost:8080/api/run/ALT-2026-03-10-4150
```

The stream includes pipeline/stage lifecycle events, model text, tool calls, tool completion, errors, and the final completion signal.

`GET /api/run/{alert_id}` causes model calls and tool execution. Do not expose that route as an unauthenticated production control surface without adding the controls appropriate to the deployment.

## Demo data

The deterministic seed generator creates network alerts and customer records for repeatable demos.

```bash
uv run python -m network_outage_agent.data.seed_generator --preset demo
```

Built-in presets include small, demo, medium, stress-test, and large data sizes. For a custom corpus:

```bash
uv run python -m network_outage_agent.data.seed_generator \
  --seed 123 \
  --alerts 5 \
  --customers 50
```

A seed is intended to reproduce the same generator output for the same code revision and inputs. It does not make model-generated agent responses deterministic.

## Deployment

Build a local image:

```bash
docker build -t noc-command .
docker run -p 8080:8080 --env-file .env noc-command
```

The current Dockerfile should be reviewed before production use. In particular, do not copy a credential-bearing `.env` into an image. Inject runtime configuration through the deployment platform or a secret manager.

A basic Cloud Run deployment can be built with Google Cloud Build and deployed with `gcloud run deploy`, but the demo's unauthenticated examples are not a production access-control recommendation.

## Repository layout

```text
network_outage_agent/
  agent.py              agent definitions and pipeline
  tools.py              simulated backend tools
  data/
    network_alerts.json
    customer_accounts.json
    seed_generator.py
server.py               FastAPI + SSE server
static/index.html       dashboard
pyproject.toml          dependencies
.env.example            configuration template
Dockerfile              container build
use-case.md             original hackathon brief
```

## Boundaries

- The repository demonstrates orchestration and UI flow with simulated data.
- Drafted communication is not automatically sent by the default demo.
- Agent output should be reviewed before it becomes customer communication.
- A deterministic input-data generator does not make model output deterministic.
- The demo tool functions do not represent the authentication and transaction semantics required for production NOC/CRM systems.
- Model IDs in preview channels can change; read the checked source configuration before deployment.

## License

Apache-2.0. See `LICENSE`.
