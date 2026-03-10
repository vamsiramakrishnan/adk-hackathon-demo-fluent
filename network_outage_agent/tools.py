"""
Tool functions for the Proactive Network Outage Communication Agent.

These tools give agents access to simulated network monitoring data
and customer account databases — the two critical data sources
for outage response orchestration.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

# Pre-load data at import time for fast tool execution
_alerts = json.loads((DATA_DIR / "network_alerts.json").read_text())
_customers = json.loads((DATA_DIR / "customer_accounts.json").read_text())


def query_network_alerts(alert_id: str = "", severity: str = "", alert_type: str = "") -> str:
    """Query the network monitoring system for active alerts.

    Args:
        alert_id: Specific alert ID to look up (e.g. 'ALT-2026-03-10-0847'). Leave empty to search by other fields.
        severity: Filter by severity level: 'CRITICAL', 'MAJOR', 'MINOR'. Leave empty for all.
        alert_type: Filter by type: 'FIBER_CUT', 'ROUTING_FAILURE', 'POWER_OUTAGE'. Leave empty for all.

    Returns:
        JSON string with matching alerts and their full technical details.
    """
    results = _alerts
    if alert_id:
        results = [a for a in results if a["alert_id"] == alert_id]
    if severity:
        results = [a for a in results if a["severity"] == severity.upper()]
    if alert_type:
        results = [a for a in results if a["alert_type"] == alert_type.upper()]

    if not results:
        return json.dumps({"status": "no_alerts_found", "filters": {"alert_id": alert_id, "severity": severity, "alert_type": alert_type}})

    return json.dumps(results, indent=2)


def get_all_active_alerts() -> str:
    """Retrieve all currently active network alerts from the monitoring system.

    Returns:
        JSON string with a summary of all active alerts including IDs, severity, type, and affected zones.
    """
    summary = []
    for a in _alerts:
        summary.append({
            "alert_id": a["alert_id"],
            "severity": a["severity"],
            "alert_type": a["alert_type"],
            "title": a["title"],
            "affected_zones": a["affected_zones"],
            "estimated_customers_affected": a["estimated_customers_affected"],
            "preliminary_etr": a["preliminary_etr"],
            "escalation_level": a["escalation_level"],
        })
    return json.dumps(summary, indent=2)


def get_affected_customers(zones: str) -> str:
    """Query the customer database to find all accounts with locations in the specified zones.

    Args:
        zones: Comma-separated list of affected zone IDs (e.g. 'ZONE-SM-A,ZONE-SM-B,ZONE-SM-C').

    Returns:
        JSON string with affected customers grouped by priority tier, including contact info and SLA details.
    """
    zone_list = [z.strip() for z in zones.split(",")]

    affected = {
        "life_safety": [],
        "enterprise_platinum": [],
        "enterprise_gold": [],
        "enterprise_silver": [],
        "government": [],
        "vip_residential": [],
        "smb": [],
        "residential_count": 0,
    }

    for customer in _customers:
        if customer["account_type"] == "RESIDENTIAL_BULK":
            count = sum(
                customer["total_subscribers_by_zone"].get(z, 0)
                for z in zone_list
            )
            if count > 0:
                affected["residential_count"] = count
            continue

        locations = customer.get("locations", [])
        matched_locations = [loc for loc in locations if loc.get("zone") in zone_list]

        if not matched_locations:
            continue

        has_life_safety = any(loc.get("criticality") == "LIFE_SAFETY" for loc in matched_locations)
        affected_services = list(set(customer.get("services", [])))

        entry = {
            "account_id": customer["account_id"],
            "name": customer.get("company_name") or customer.get("customer_name"),
            "account_type": customer["account_type"],
            "tier": customer.get("tier"),
            "contract_value_annual": customer.get("contract_value_annual"),
            "sla_tier": customer.get("sla_tier"),
            "sla_credit_rate": customer.get("sla_credit_rate"),
            "primary_contact": customer.get("primary_contact"),
            "escalation_contact": customer.get("escalation_contact"),
            "affected_locations": matched_locations,
            "affected_services": affected_services,
            "has_life_safety_sites": has_life_safety,
            "notes": customer.get("notes"),
        }

        if has_life_safety:
            affected["life_safety"].append(entry)
        elif customer["account_type"] == "GOVERNMENT":
            affected["government"].append(entry)
        elif customer["account_type"] == "VIP_RESIDENTIAL":
            affected["vip_residential"].append(entry)
        elif customer["account_type"] == "SMB":
            affected["smb"].append(entry)
        elif customer.get("tier") == "PLATINUM":
            affected["enterprise_platinum"].append(entry)
        elif customer.get("tier") == "GOLD":
            affected["enterprise_gold"].append(entry)
        else:
            affected["enterprise_silver"].append(entry)

    # Build summary
    total_named = sum(
        len(v) for k, v in affected.items() if isinstance(v, list)
    )

    result = {
        "query_zones": zone_list,
        "summary": {
            "total_named_accounts_affected": total_named,
            "total_residential_subscribers_affected": affected["residential_count"],
            "life_safety_accounts": len(affected["life_safety"]),
            "government_accounts": len(affected["government"]),
            "platinum_enterprise": len(affected["enterprise_platinum"]),
            "gold_enterprise": len(affected["enterprise_gold"]),
            "silver_enterprise": len(affected["enterprise_silver"]),
            "vip_residential": len(affected["vip_residential"]),
            "smb_accounts": len(affected["smb"]),
        },
        "affected_accounts": affected,
    }

    return json.dumps(result, indent=2)


def get_customer_sla_details(account_id: str) -> str:
    """Get detailed SLA and contract information for a specific customer account.

    Args:
        account_id: The customer account ID (e.g. 'ENT-001', 'VIP-001').

    Returns:
        JSON string with full account details including SLA terms, contact info, and service history.
    """
    for customer in _customers:
        if customer.get("account_id") == account_id:
            return json.dumps(customer, indent=2)

    return json.dumps({"error": f"Account {account_id} not found"})


def calculate_sla_exposure(account_id: str, outage_duration_hours: float) -> str:
    """Calculate the exact SLA credit exposure in dollars for a customer account based on outage duration.

    Args:
        account_id: The customer account ID (e.g. 'ENT-001').
        outage_duration_hours: How long the outage has lasted or is expected to last, in hours.

    Returns:
        JSON string with SLA tier, credit rate, calculated exposure, and whether the SLA is breached.
    """
    for customer in _customers:
        if customer.get("account_id") == account_id:
            contract_value = customer.get("contract_value_annual", 0)
            sla_tier = customer.get("sla_tier", "STANDARD")
            credit_rate = customer.get("sla_credit_rate", "")

            # Calculate hourly credit rate from contract value and credit formula
            import re
            hourly_rate = 0.0
            base_hourly = contract_value / 8760  # annual to hourly
            if credit_rate:
                # Parse multiplier (e.g. "10x hourly rate per minute of downtime")
                mult_match = re.search(r"(\d+)x", credit_rate)
                multiplier = float(mult_match.group(1)) if mult_match else 5
                if "per minute" in credit_rate:
                    hourly_rate = base_hourly * multiplier * 60  # per minute * 60
                else:
                    hourly_rate = base_hourly * multiplier
            else:
                hourly_rate = base_hourly * 5  # default 5x penalty

            total_credit = hourly_rate * outage_duration_hours

            # SLA breach thresholds by uptime guarantee
            breach_thresholds = {
                "99.999%": 0.087,   # ~5 min/year → breach fast
                "99.99%": 0.5,      # 30 min
                "99.95%": 1.0,      # 1 hour
                "99.9%": 4.0,       # 4 hours
                "99%": 8.0,         # 8 hours
            }
            threshold = breach_thresholds.get(sla_tier, 4.0)
            is_breached = outage_duration_hours > threshold

            return json.dumps({
                "account_id": account_id,
                "name": customer.get("company_name") or customer.get("customer_name"),
                "sla_tier": sla_tier,
                "contract_value_annual": contract_value,
                "credit_rate_hourly": hourly_rate,
                "outage_duration_hours": outage_duration_hours,
                "total_credit_exposure": total_credit,
                "breach_threshold_hours": threshold,
                "sla_breached": is_breached,
                "time_until_breach_hours": max(0, threshold - outage_duration_hours),
                "exposure_as_percent_of_contract": round((total_credit / contract_value * 100), 2) if contract_value else 0,
            }, indent=2)

    return json.dumps({"error": f"Account {account_id} not found"})


def estimate_call_volume(affected_customers: int, severity: str) -> str:
    """Estimate the expected inbound call volume to the NOC/call center based on affected customers and severity.

    Args:
        affected_customers: Total number of affected customer accounts (named + residential).
        severity: Outage severity: 'CRITICAL', 'MAJOR', 'MINOR'.

    Returns:
        JSON string with call volume projections, staffing recommendations, and overflow risk.
    """
    # Call-in rates by severity (% of affected customers who call)
    call_rates = {
        "CRITICAL": 0.15,
        "MAJOR": 0.08,
        "MINOR": 0.03,
    }
    rate = call_rates.get(severity.upper(), 0.05)

    projected_calls = int(affected_customers * rate)
    peak_calls_per_hour = int(projected_calls * 0.4)  # 40% in first hour

    # Staffing model: 1 agent handles ~8 calls/hour
    agents_needed = max(1, peak_calls_per_hour // 8 + 1)
    baseline_agents = 5
    overflow = peak_calls_per_hour > baseline_agents * 8

    # Cost estimates
    avg_call_duration_min = 6 if severity == "CRITICAL" else 4
    total_agent_hours = (projected_calls * avg_call_duration_min) / 60
    cost_per_agent_hour = 45
    estimated_call_center_cost = round(total_agent_hours * cost_per_agent_hour, 2)

    # Proactive notification savings
    if severity == "CRITICAL":
        reduction_rate = 0.40  # proactive comms reduce calls by 40%
    elif severity == "MAJOR":
        reduction_rate = 0.50
    else:
        reduction_rate = 0.60

    calls_with_proactive = int(projected_calls * (1 - reduction_rate))
    cost_with_proactive = round((calls_with_proactive * avg_call_duration_min / 60) * cost_per_agent_hour, 2)

    return json.dumps({
        "affected_customers": affected_customers,
        "severity": severity.upper(),
        "call_in_rate": f"{rate*100:.0f}%",
        "projected_total_calls": projected_calls,
        "peak_calls_first_hour": peak_calls_per_hour,
        "avg_call_duration_minutes": avg_call_duration_min,
        "staffing": {
            "agents_needed": agents_needed,
            "baseline_agents": baseline_agents,
            "overflow_risk": overflow,
            "additional_agents_needed": max(0, agents_needed - baseline_agents),
        },
        "cost_without_proactive_comms": estimated_call_center_cost,
        "proactive_notification_impact": {
            "call_reduction_rate": f"{reduction_rate*100:.0f}%",
            "projected_calls_with_proactive": calls_with_proactive,
            "cost_with_proactive_comms": cost_with_proactive,
            "estimated_savings": round(estimated_call_center_cost - cost_with_proactive, 2),
        },
    }, indent=2)


def check_communication_infrastructure(zones: str) -> str:
    """Check whether the outage affects our own communication infrastructure (SMS gateways, email servers, push notification services).

    Args:
        zones: Comma-separated list of affected zone IDs to check against our infrastructure map.

    Returns:
        JSON string with communication channel availability and recommended fallback channels.
    """
    zone_list = [z.strip() for z in zones.split(",")]

    # Simulated infrastructure map — our own systems
    infra_map = {
        "sms_gateway": {"zones": ["ZONE-DC-A", "ZONE-DC-B"], "status": "operational", "provider": "Internal SMS Platform"},
        "email_relay": {"zones": ["ZONE-DC-A"], "status": "operational", "provider": "Internal SMTP Cluster"},
        "push_notification": {"zones": ["ZONE-DC-B"], "status": "operational", "provider": "FCM/APNs Gateway"},
        "ivr_system": {"zones": ["ZONE-DC-A", "ZONE-DC-B"], "status": "operational", "provider": "Voice IVR Platform"},
        "status_page": {"zones": ["ZONE-DC-A"], "status": "operational", "provider": "status.ourtelco.com (CDN-backed)"},
    }

    affected_channels = []
    operational_channels = []

    for channel, info in infra_map.items():
        overlap = set(info["zones"]) & set(zone_list)
        if overlap:
            affected_channels.append({
                "channel": channel,
                "provider": info["provider"],
                "affected_zones": list(overlap),
                "risk": "HIGH" if len(overlap) == len(info["zones"]) else "MEDIUM",
                "fallback": _get_fallback(channel),
            })
        else:
            operational_channels.append({
                "channel": channel,
                "provider": info["provider"],
                "status": "FULLY_OPERATIONAL",
            })

    all_clear = len(affected_channels) == 0

    return json.dumps({
        "communication_infrastructure_check": {
            "zones_checked": zone_list,
            "all_channels_clear": all_clear,
            "affected_channels": affected_channels,
            "operational_channels": operational_channels,
            "recommendation": (
                "All communication channels operational. Proceed with standard notification plan."
                if all_clear else
                "WARNING: Some communication channels may be impacted. Use fallback channels listed above."
            ),
        }
    }, indent=2)


def _get_fallback(channel: str) -> str:
    fallbacks = {
        "sms_gateway": "Use third-party SMS API (Twilio) as backup",
        "email_relay": "Route through cloud email provider (SendGrid)",
        "push_notification": "Fall back to SMS for critical notifications",
        "ivr_system": "Redirect to backup call center in alternate region",
        "status_page": "CDN-cached; should remain available. Update via API.",
    }
    return fallbacks.get(channel, "Manual outreach via alternate channel")


def log_communication_action(account_id: str, channel: str, message_type: str, status: str) -> str:
    """Log a communication action taken for audit and compliance tracking.

    Args:
        account_id: Customer account ID the communication was sent to.
        channel: Communication channel used: 'phone', 'email', 'sms', 'app_push'.
        message_type: Type of message: 'initial_notification', 'update', 'resolution'.
        status: Status of the action: 'drafted', 'approved', 'sent', 'pending_approval'.

    Returns:
        Confirmation string with logged action details.
    """
    return json.dumps({
        "logged": True,
        "action": {
            "account_id": account_id,
            "channel": channel,
            "message_type": message_type,
            "status": status,
            "timestamp": "2026-03-10T09:15:00Z",
            "logged_by": "outage_communication_agent",
        }
    }, indent=2)
