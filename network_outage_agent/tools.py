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
