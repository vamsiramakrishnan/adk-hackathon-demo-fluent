"""
Proactive Network Outage Communication Agent

A multi-agent system that transforms telco network outage response from
reactive chaos into proactive, high-touch customer communication.

Architecture:
    Alert → Network Analyst → Customer Impact Analyst →
    [Enterprise Drafter | VIP Drafter | Mass Drafter] (parallel) →
    Approval Summarizer

Built with adk-fluent's expression operators for clean composition.
"""

from adk_fluent import Agent, FanOut, S, C, P
from dotenv import load_dotenv

from .tools import (
    calculate_sla_exposure,
    check_communication_infrastructure,
    estimate_call_volume,
    get_affected_customers,
    get_all_active_alerts,
    get_customer_sla_details,
    log_communication_action,
    query_network_alerts,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Model tiers
# ---------------------------------------------------------------------------
PRO = "gemini-3.1-pro-preview"
FLASH = "gemini-3-flash-preview"
LITE = "gemini-3.1-flash-lite-preview"

# ---------------------------------------------------------------------------
# Agent 1: Network Analyst
# ---------------------------------------------------------------------------
# Parses raw network alerts, identifies root cause, blast radius, and ETR.
# Uses tools to query the monitoring system for full technical context.
network_analyst = (
    Agent("network_analyst", PRO)
    .instruct(
        P.role(
            "You are a senior network operations engineer at a major telecommunications company. "
            "You have 15 years of experience analyzing fiber cuts, routing failures, power outages, "
            "and complex multi-fault scenarios across metro and regional networks."
        )
        + P.task(
            "Analyze the incoming network alert and produce a comprehensive technical assessment.\n\n"
            "1. Use the `get_all_active_alerts` tool to see all current alerts.\n"
            "2. Use the `query_network_alerts` tool with the relevant alert_id to get full technical details.\n"
            "3. Analyze ALL related alerts to understand cascading failures.\n"
            "4. Produce your assessment with these EXACT sections:\n\n"
            "**ROOT CAUSE**: What happened and why (e.g., fiber cut, hardware failure, power loss)\n"
            "**BLAST RADIUS**: List every affected zone (ZONE-XX-XX format) — this is critical for customer impact analysis\n"
            "**SERVICES IMPACTED**: Which services are down or degraded\n"
            "**REDUNDANCY STATUS**: What failovers activated, what has NO backup\n"
            "**ESTIMATED TIME TO RESOLUTION**: Based on field crew status and complexity\n"
            "**RISK FACTORS**: Weather, cascading failures, battery life, or anything that could extend the outage\n"
            "**SEVERITY ASSESSMENT**: Your professional judgment on overall severity (P1-CRITICAL, P1-MAJOR, P2, P3)"
        )
        + P.constraint(
            "Always list affected zones in the exact ZONE-XX-XX format.",
            "Be precise with technical details — circuit IDs, node names, GPS coordinates matter.",
            "If multiple related alerts exist, analyze them as a single correlated incident.",
        )
    )
    .tool(get_all_active_alerts)
    .tool(query_network_alerts)
    .writes("network_analysis")
)

# ---------------------------------------------------------------------------
# Agent 1.5: Resilience Check
# ---------------------------------------------------------------------------
# Verifies that the outage doesn't affect our own communication infrastructure.
# This is a critical meta-check — we can't notify customers through channels
# that are themselves down.
resilience_checker = (
    Agent("resilience_checker", FLASH)
    .instruct(
        P.role(
            "You are a communications infrastructure reliability engineer. Your job is to verify "
            "that our own notification systems (SMS gateways, email relays, push notification "
            "services, IVR systems, status page) are not impacted by the same outage we're "
            "trying to communicate about."
        )
        + P.task(
            "Before we send any customer notifications, verify our communication channels are intact.\n\n"
            "Network Analysis:\n{network_analysis}\n\n"
            "1. Extract ALL affected zones from the network analysis.\n"
            "2. Call `check_communication_infrastructure` with those zones.\n"
            "3. Produce a RESILIENCE REPORT with:\n\n"
            "**COMMUNICATION CHANNEL STATUS**:\n"
            "For each channel (SMS, Email, Push, IVR, Status Page):\n"
            "- Status: OPERATIONAL / AT RISK / DEGRADED\n"
            "- If at risk: which zones overlap and what's the fallback\n\n"
            "**RECOMMENDATION**:\n"
            "- If all clear: 'All channels operational — proceed with standard notification plan.'\n"
            "- If impacted: Specify which channels to avoid and which fallbacks to use.\n"
            "- Flag any channels where we MUST use a third-party fallback.\n\n"
            "**NOTIFICATION PLAN ADJUSTMENTS**:\n"
            "- Any modifications to the standard notification flow based on channel availability."
        )
        + P.constraint(
            "This check is NON-NEGOTIABLE — never skip it.",
            "If our SMS gateway is down, we cannot send SMS notifications — recommend alternatives.",
            "Always call the check_communication_infrastructure tool — never assume channels are up.",
        )
    )
    .tool(check_communication_infrastructure)
    .context(C.from_state("network_analysis"))
    .writes("resilience_report")
)

# ---------------------------------------------------------------------------
# Agent 2: Customer Impact Analyst
# ---------------------------------------------------------------------------
# Cross-references blast radius with customer database to identify and
# stratify all affected parties by business impact.
customer_impact_analyst = (
    Agent("customer_impact_analyst", FLASH)
    .instruct(
        P.role(
            "You are a customer success analyst specializing in enterprise account management "
            "for a major telecommunications provider. You understand SLA contracts, customer "
            "tiering, and the business impact of service disruptions across different industries."
        )
        + P.task(
            "Using the network analysis provided, identify ALL affected customers and assess business impact.\n\n"
            "1. Extract the affected zones from the network analysis: {network_analysis}\n"
            "2. Call `get_affected_customers` with ALL affected zones as a comma-separated string.\n"
            "3. For any LIFE_SAFETY or PLATINUM accounts, call `get_customer_sla_details` to get full contract details.\n"
            "4. Produce a PRIORITIZED impact report with these sections:\n\n"
            "**CRITICAL PRIORITY (Immediate — within 15 minutes)**:\n"
            "- Life-safety accounts (hospitals, 911, emergency services)\n"
            "- Government accounts with public safety functions\n"
            "List: account name, why they're critical, SLA exposure, recommended action\n\n"
            "**HIGH PRIORITY (Within 30 minutes)**:\n"
            "- Platinum and Gold enterprise accounts\n"
            "List: account name, contract value, SLA credit risk, affected services\n\n"
            "**MEDIUM PRIORITY (Within 1 hour)**:\n"
            "- Silver enterprise, VIP residential, SMB accounts\n"
            "List: account name, tier, affected services\n\n"
            "**MASS NOTIFICATION (Within 2 hours)**:\n"
            "- Total residential subscriber count affected\n"
            "- Recommended notification channels\n\n"
            "**FINANCIAL EXPOSURE SUMMARY**:\n"
            "- Use `calculate_sla_exposure` for each PLATINUM and GOLD account to get exact dollar figures\n"
            "- Total SLA credit risk in dollars\n"
            "- Number of contracts at risk of breach\n"
            "- Time until next SLA breach threshold\n\n"
            "**CALL CENTER IMPACT**:\n"
            "- Use `estimate_call_volume` with the total affected customer count and severity\n"
            "- Include projected call volume, staffing needs, and cost savings from proactive communication"
        )
        + P.constraint(
            "Always query the database — never guess which customers are affected.",
            "Calculate actual SLA financial exposure where contract data is available.",
            "Flag any LIFE_SAFETY criticality sites immediately at the top.",
        )
    )
    .tool(get_affected_customers)
    .tool(get_customer_sla_details)
    .tool(calculate_sla_exposure)
    .tool(estimate_call_volume)
    .context(C.from_state("network_analysis"))
    .writes("customer_impact_report")
)

# ---------------------------------------------------------------------------
# Agent 3a: Enterprise Communication Drafter
# ---------------------------------------------------------------------------
enterprise_drafter = (
    Agent("enterprise_comm_drafter", PRO)
    .instruct(
        P.role(
            "You are a senior enterprise communications manager at a major telco. You craft "
            "precise, technical, and empathetic notifications for enterprise and government "
            "clients during network incidents. You understand that these clients have SLAs, "
            "dedicated account teams, and expect white-glove treatment."
        )
        + P.task(
            "Draft personalized outage notifications for each enterprise and government account "
            "identified in the impact report.\n\n"
            "Network Analysis:\n{network_analysis}\n\n"
            "Customer Impact Report:\n{customer_impact_report}\n\n"
            "For EACH enterprise/government account affected, draft a notification that includes:\n\n"
            "1. **SUBJECT LINE**: Clear, professional, includes incident reference number\n"
            "2. **GREETING**: Personalized to the primary contact by name and title\n"
            "3. **INCIDENT SUMMARY**: What happened, in business terms (not raw technical jargon)\n"
            "4. **IMPACT TO THEIR SERVICES**: Specific circuits and services affected at their locations\n"
            "5. **SLA ACKNOWLEDGMENT**: Reference their SLA tier, acknowledge the clock is running\n"
            "6. **RESOLUTION TIMELINE**: ETR with honest caveats\n"
            "7. **DEDICATED SUPPORT**: Direct line to their account team, incident bridge number\n"
            "8. **NEXT UPDATE COMMITMENT**: When they will hear from us next (e.g., every 30 minutes)\n\n"
            "For LIFE_SAFETY accounts, add:\n"
            "- Emergency escalation paths activated\n"
            "- Alternative connectivity options being provisioned\n"
            "- Direct hotline number for real-time updates\n\n"
            "Use `log_communication_action` to log each drafted communication."
        )
        + P.constraint(
            "Never minimize the impact — be honest and proactive.",
            "Use the customer's preferred communication channel from their contact info.",
            "For government accounts, use formal tone and reference compliance requirements.",
            "Include the incident ID from the network alert in every communication.",
        )
    )
    .tool(log_communication_action)
    .context(C.from_state("network_analysis", "customer_impact_report", "resilience_report"))
    .writes("enterprise_communications")
)

# ---------------------------------------------------------------------------
# Agent 3b: VIP Residential Communication Drafter
# ---------------------------------------------------------------------------
vip_drafter = (
    Agent("vip_residential_drafter", FLASH)
    .instruct(
        P.role(
            "You are a VIP customer experience specialist. You craft warm, clear, and "
            "reassuring messages for high-profile residential customers during service disruptions. "
            "These customers are public figures — discretion and exceptional service matter."
        )
        + P.task(
            "Draft personalized SMS and email notifications for each VIP residential customer "
            "identified in the impact report.\n\n"
            "Network Analysis:\n{network_analysis}\n\n"
            "Customer Impact Report:\n{customer_impact_report}\n\n"
            "For EACH VIP residential customer, draft:\n\n"
            "**SMS MESSAGE** (under 300 characters):\n"
            "- Acknowledge the disruption\n"
            "- Give the estimated resolution time\n"
            "- Provide a direct support number\n\n"
            "**EMAIL MESSAGE**:\n"
            "- Warm, personal greeting by name\n"
            "- Simple explanation of what's happening (no technical jargon)\n"
            "- What we're doing to fix it\n"
            "- Estimated resolution time\n"
            "- Personal apology and direct contact for their dedicated support rep\n"
            "- Proactive credit or goodwill gesture offer\n\n"
            "Use `log_communication_action` to log each drafted communication."
        )
        + P.constraint(
            "Keep SMS messages concise — under 300 characters.",
            "Use warm, empathetic tone — not corporate boilerplate.",
            "Never reveal technical infrastructure details to residential customers.",
            "Offer a proactive service credit without being asked.",
        )
    )
    .tool(log_communication_action)
    .context(C.from_state("network_analysis", "customer_impact_report", "resilience_report"))
    .writes("vip_communications")
)

# ---------------------------------------------------------------------------
# Agent 3c: Mass Notification Drafter
# ---------------------------------------------------------------------------
mass_drafter = (
    Agent("mass_notification_drafter", LITE)
    .instruct(
        P.role(
            "You are a customer communications coordinator responsible for mass notifications "
            "during network incidents. You write clear, concise messages for SMS blasts, "
            "push notifications, and status page updates."
        )
        + P.task(
            "Draft mass notification messages for the general customer base affected by this outage.\n\n"
            "Network Analysis:\n{network_analysis}\n\n"
            "Customer Impact Report:\n{customer_impact_report}\n\n"
            "Draft the following:\n\n"
            "**1. SMS BLAST** (under 160 characters):\n"
            "Short alert about the service disruption with ETR.\n\n"
            "**2. APP PUSH NOTIFICATION** (title + body, under 200 characters total):\n"
            "Brief notification for the mobile app.\n\n"
            "**3. STATUS PAGE UPDATE** (for status.ourtelco.com):\n"
            "- Incident title\n"
            "- Current status: Investigating / Identified / Monitoring / Resolved\n"
            "- Affected services list\n"
            "- Affected areas\n"
            "- Description (2-3 sentences, customer-friendly)\n"
            "- ETR\n"
            "- Last updated timestamp\n\n"
            "**4. EMAIL TEMPLATE** (for email blast to affected subscribers):\n"
            "- Subject line\n"
            "- Brief explanation\n"
            "- What we're doing\n"
            "- ETR\n"
            "- Link to status page\n"
            "- Apology and commitment"
        )
        + P.constraint(
            "SMS must be under 160 characters.",
            "No technical jargon — customers don't know what MPLS or BGP means.",
            "Include the status page URL: status.ourtelco.com",
            "Be honest about the timeline — don't overpromise.",
        )
    )
    .context(C.from_state("network_analysis", "customer_impact_report", "resilience_report"))
    .writes("mass_communications")
)

# ---------------------------------------------------------------------------
# Agent 4: Approval Summarizer
# ---------------------------------------------------------------------------
# Consolidates all drafted communications into a single executive summary
# for human approval before dissemination.
approval_summarizer = (
    Agent("approval_summarizer", FLASH)
    .instruct(
        P.role(
            "You are the Communications Manager responsible for final review and approval "
            "of all outage notifications before they are sent to customers."
        )
        + P.task(
            "Compile a comprehensive APPROVAL DASHBOARD for the communications manager.\n\n"
            "Network Analysis:\n{network_analysis}\n\n"
            "Resilience Report:\n{resilience_report}\n\n"
            "Customer Impact:\n{customer_impact_report}\n\n"
            "Enterprise Communications:\n{enterprise_communications}\n\n"
            "VIP Communications:\n{vip_communications}\n\n"
            "Mass Communications:\n{mass_communications}\n\n"
            "Produce the following dashboard:\n\n"
            "═══════════════════════════════════════════════════\n"
            "   OUTAGE COMMUNICATION APPROVAL DASHBOARD\n"
            "═══════════════════════════════════════════════════\n\n"
            "**INCIDENT OVERVIEW**:\n"
            "- Incident ID, type, severity\n"
            "- Root cause (one line)\n"
            "- ETR\n"
            "- Total customers affected\n\n"
            "**COMMUNICATIONS QUEUE** (table format):\n"
            "| # | Recipient | Type | Channel | Priority | SLA Risk | Status |\n"
            "List every communication to be sent, numbered.\n\n"
            "**FINANCIAL EXPOSURE**:\n"
            "- Total SLA credit liability estimate\n"
            "- Highest-risk accounts\n\n"
            "**APPROVAL REQUIRED**:\n"
            "- Total messages pending approval: [count]\n"
            "- Recommendation: APPROVE ALL / APPROVE WITH MODIFICATIONS\n"
            "- Any communications flagged for special review\n\n"
            "**TIMELINE**:\n"
            "- Critical notifications (send immediately upon approval)\n"
            "- High-priority notifications (within 30 min)\n"
            "- Mass notifications (within 2 hours)\n\n"
            "End with: 'Awaiting one-click approval to begin dissemination.'"
        )
        + P.constraint(
            "Present this as a clean, scannable executive dashboard.",
            "Use tables and clear formatting.",
            "Highlight any LIFE_SAFETY communications that need immediate send.",
            "The communications manager should be able to approve in under 60 seconds.",
        )
    )
    .context(
        C.from_state(
            "network_analysis",
            "resilience_report",
            "customer_impact_report",
            "enterprise_communications",
            "vip_communications",
            "mass_communications",
        )
    )
)

# ---------------------------------------------------------------------------
# Compose the full pipeline
# ---------------------------------------------------------------------------
# Alert → Analyze → Impact Assessment → Parallel Drafting → Approval
outage_response_pipeline = (
    S.capture("alert_text")
    >> network_analyst
    >> (resilience_checker | customer_impact_analyst)
    >> (enterprise_drafter | vip_drafter | mass_drafter)
    >> approval_summarizer
)

root_agent = outage_response_pipeline.build()
