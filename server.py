"""
NOC Dashboard Server

Combines ADK's built-in agent serving with custom alert data endpoints
and a bespoke NOC dashboard frontend. Designed for Cloud Run deployment.

Usage:
    uv run uvicorn server:app --host 0.0.0.0 --port 8080
"""

import json
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
from sse_starlette.sse import EventSourceResponse

load_dotenv()

from network_outage_agent.agent import root_agent
from network_outage_agent.tools import _alerts

app = FastAPI(title="NOC Command — Proactive Outage Communication")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"

# Shared runner instance
runner = InMemoryRunner(agent=root_agent, app_name="noc_dashboard")


# ── Static Frontend ──────────────────────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


# ── Alert Data API ───────────────────────────────────────────────────────────
@app.get("/api/alerts")
async def list_alerts():
    return [
        {
            "alert_id": a["alert_id"],
            "severity": a["severity"],
            "alert_type": a["alert_type"],
            "title": a["title"],
            "description": a["description"],
            "affected_zones": a["affected_zones"],
            "affected_infrastructure": a.get("affected_infrastructure", {}),
            "services_impacted": a.get("services_impacted", []),
            "estimated_customers_affected": a["estimated_customers_affected"],
            "preliminary_etr": a["preliminary_etr"],
            "escalation_level": a["escalation_level"],
            "timestamp": a["timestamp"],
            "redundancy_status": a.get("redundancy_status", ""),
            "field_dispatch": a.get("field_dispatch", {}),
            "related_alerts": a.get("related_alerts", []),
        }
        for a in _alerts
    ]


@app.get("/api/alerts/{alert_id}")
async def get_alert(alert_id: str):
    for a in _alerts:
        if a["alert_id"] == alert_id:
            return a
    return {"error": "not found"}


# ── Agent SSE Streaming ──────────────────────────────────────────────────────
@app.get("/api/run/{alert_id}")
async def run_agent_sse(alert_id: str, request: Request):
    """Stream agent pipeline execution for a given alert via SSE."""

    alert_data = next((a for a in _alerts if a["alert_id"] == alert_id), None)
    if not alert_data:
        return {"error": "Alert not found"}

    alert_text = (
        f"CRITICAL NETWORK ALERT: {alert_data['title']}\n"
        f"Alert ID: {alert_data['alert_id']}\n"
        f"Severity: {alert_data['severity']}\n"
        f"Type: {alert_data['alert_type']}\n"
        f"Affected Zones: {', '.join(alert_data['affected_zones'])}\n"
        f"Estimated Customers Affected: {alert_data['estimated_customers_affected']}\n"
        f"ETR: {alert_data['preliminary_etr']}\n"
        f"Description: {alert_data['description']}"
    )

    session = await runner.session_service.create_session(
        app_name="noc_dashboard",
        user_id=f"noc_{uuid.uuid4().hex[:8]}",
    )

    user_content = Content(role="user", parts=[Part(text=alert_text)])

    async def event_generator():
        stage_map = {
            "network_analyst": {"stage": "network_analysis", "label": "Network Analyst", "icon": "1", "order": 1},
            "customer_impact_analyst": {"stage": "customer_impact", "label": "Customer Impact Analyst", "icon": "2", "order": 2},
            "enterprise_comm_drafter": {"stage": "enterprise_comms", "label": "Enterprise Comms", "icon": "3a", "order": 3},
            "vip_residential_drafter": {"stage": "vip_comms", "label": "VIP Comms", "icon": "3b", "order": 3},
            "mass_notification_drafter": {"stage": "mass_comms", "label": "Mass Notifications", "icon": "3c", "order": 3},
            "approval_summarizer": {"stage": "approval", "label": "Approval Dashboard", "icon": "4", "order": 4},
        }

        yield {"event": "pipeline_start", "data": json.dumps({"alert_id": alert_data["alert_id"], "ts": time.time()})}

        current_agent = None

        try:
            async for event in runner.run_async(
                user_id=session.user_id, session_id=session.id, new_message=user_content,
            ):
                if await request.is_disconnected():
                    break

                author = event.author
                if not author or author == "user":
                    continue

                clean_author = author
                for name in stage_map:
                    if name in author:
                        clean_author = name
                        break

                info = stage_map.get(clean_author)
                if not info:
                    continue

                if clean_author != current_agent:
                    if current_agent:
                        prev = stage_map.get(current_agent, {})
                        yield {"event": "stage_done", "data": json.dumps({"stage": prev.get("stage"), "label": prev.get("label")})}
                    current_agent = clean_author
                    yield {"event": "stage_start", "data": json.dumps(info)}

                if event.content and event.content.parts:
                    for part in event.content.parts:
                        text = getattr(part, "text", None)
                        if text:
                            yield {"event": "text", "data": json.dumps({"stage": info["stage"], "text": text})}

                        fc = getattr(part, "function_call", None)
                        if fc:
                            yield {"event": "tool_call", "data": json.dumps({
                                "stage": info["stage"], "tool": fc.name,
                                "args": dict(fc.args) if fc.args else {},
                            })}

                        fr = getattr(part, "function_response", None)
                        if fr:
                            yield {"event": "tool_result", "data": json.dumps({
                                "stage": info["stage"], "tool": fr.name,
                            })}

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

        if current_agent:
            prev = stage_map.get(current_agent, {})
            yield {"event": "stage_done", "data": json.dumps({"stage": prev.get("stage"), "label": prev.get("label")})}

        yield {"event": "done", "data": json.dumps({"ts": time.time()})}

    return EventSourceResponse(event_generator())


# Static files (must be last)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
