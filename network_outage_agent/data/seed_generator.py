"""
Seed-based Telco Data Generator

Generates realistic network alerts and customer account databases at any scale.
Uses deterministic seeding for reproducibility — same seed always produces
the same dataset, making demos predictable and debuggable.

Usage:
    python -m network_outage_agent.data.seed_generator --seed 42 --alerts 10 --customers 500
    python -m network_outage_agent.data.seed_generator --preset demo
    python -m network_outage_agent.data.seed_generator --preset stress-test
"""

import argparse
import json
import random
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Vocabulary pools — the building blocks for realistic data
# ---------------------------------------------------------------------------

METRO_AREAS = [
    {"code": "SM", "name": "South Metro", "city": "Atlanta South", "lat": 33.749, "lon": -84.388},
    {"code": "NM", "name": "North Metro", "city": "Atlanta North", "lat": 33.88, "lon": -84.32},
    {"code": "ND", "name": "North District", "city": "Marietta", "lat": 33.95, "lon": -84.55},
    {"code": "EM", "name": "East Metro", "city": "Decatur", "lat": 33.77, "lon": -84.30},
    {"code": "WM", "name": "West Metro", "city": "Douglasville", "lat": 33.75, "lon": -84.75},
    {"code": "DC", "name": "Data Center", "city": "Suwanee", "lat": 34.05, "lon": -84.07},
    {"code": "DT", "name": "Downtown Core", "city": "Atlanta CBD", "lat": 33.755, "lon": -84.39},
    {"code": "BIZ", "name": "Business Corridor", "city": "Buckhead", "lat": 33.84, "lon": -84.38},
]

ZONE_SUFFIXES = ["A", "B", "C", "D", "E", "F"]

ALERT_TYPES = {
    "FIBER_CUT": {
        "titles": [
            "Major Fiber Optic Cable Severed — Ring {ring} {area}",
            "Fiber Break Detected — Trunk Line {area} Segment {seg}",
            "Bidirectional Loss of Signal — {area} Distribution Fiber",
            "Aerial Fiber Damage — {area} Route {route}",
        ],
        "descriptions": [
            "Bidirectional loss of signal detected on fiber ring R{ring}-{code} between nodes {code}-OLT-{n1} and {code}-OLT-{n2}. OTDR readings confirm physical break at splice point SP-{sp} (GPS: {lat}°N, {lon}°W). Affected span: {span}km backbone segment serving {area} distribution network.",
            "Construction crew struck underground fiber conduit on {street}. Multiple fiber strands severed in 288-count cable. Affecting {area} backbone capacity. Emergency splice team dispatched.",
            "Vehicle collision with aerial fiber cable at pole #{pole}. Complete strand separation confirmed by OTDR. {area} ring protection activated on {partial} of {total} nodes.",
        ],
        "etr_range": (3, 8),
        "severity_weights": {"CRITICAL": 0.6, "MAJOR": 0.3, "MINOR": 0.1},
    },
    "ROUTING_FAILURE": {
        "titles": [
            "Core Router Failure — {area} Cluster",
            "BGP Session Storm — {area} Edge",
            "OSPF Adjacency Collapse — {area} Aggregation Layer",
            "Line Card Failure — {router} at {area}",
        ],
        "descriptions": [
            "Primary core router CR-{code}-{n1:02d} experienced catastrophic line card failure in slots {slot1} and {slot2}. OSPF adjacencies dropped across {downstream} downstream aggregation switches. Traffic rerouting through CR-{code}-{n2:02d} causing {util}% utilization on backup links.",
            "BGP peering instability between PE-{code}-{n1:02d} and upstream transit providers. Route flapping causing intermittent packet loss on {circuits} enterprise circuits. Root cause: corrupted BGP update from peer AS{asn}.",
            "Spanning tree reconvergence event in {area} aggregation layer. {switches} switches affected. Caused by dual supervisor failover in AGG-{code}-{n1:02d}.",
        ],
        "etr_range": (1, 4),
        "severity_weights": {"CRITICAL": 0.3, "MAJOR": 0.5, "MINOR": 0.2},
    },
    "POWER_OUTAGE": {
        "titles": [
            "Multi-Site Power Failure — {area} Cell Network",
            "Commercial Power Loss — {area} Exchange Building",
            "Utility Grid Fault — {area} Distribution Zone",
            "Generator Failure — {area} Critical Site",
        ],
        "descriptions": [
            "Widespread commercial power failure affecting {sites} cell tower sites in {area} following utility grid fault. Battery backup active at all sites — estimated {battery}h runtime remaining. Generator dispatch initiated.",
            "Complete power loss at {area} exchange building ({code}-EX-MAIN). UPS holding load — {battery}h runtime. Diesel generator failed to auto-start — manual start procedure initiated.",
            "Utility provider reports transformer failure affecting {area} service area. Estimated {sites} sites on battery backup. Utility ETA for restoration: {util_etr} hours.",
        ],
        "etr_range": (4, 12),
        "severity_weights": {"CRITICAL": 0.5, "MAJOR": 0.4, "MINOR": 0.1},
    },
    "HARDWARE_FAILURE": {
        "titles": [
            "Switch Fabric Failure — {area} Aggregation",
            "Optics Degradation — {area} DWDM Ring",
            "Storage Controller Crash — {area} Subscriber DB",
        ],
        "descriptions": [
            "Switch fabric module failure in AGG-{code}-{n1:02d}. Redundant fabric handling traffic but at 50% capacity. {downstream} access switches reporting increased latency.",
            "Multiple DWDM optic transceivers degrading on {area} wavelength ring. BER exceeding threshold on lambdas {l1}-{l2}. Pre-emptive failover recommended.",
        ],
        "etr_range": (2, 6),
        "severity_weights": {"CRITICAL": 0.2, "MAJOR": 0.5, "MINOR": 0.3},
    },
}

RELATED_ALERT_TYPES = [
    ("POWER_ALARM", "Battery backup engaged at {node} — commercial power interrupted"),
    ("BGP_SESSION_DOWN", "BGP peering lost between {node} and upstream PE router PE-CORE-{n:02d}"),
    ("MOBILE_BACKHAUL_DEGRADED", "5G backhaul capacity reduced {pct}% across {count} cell sites in {area}"),
    ("QOS_VIOLATION", "SLA threshold breached on {count} enterprise circuits — jitter >{jitter}ms"),
    ("BATTERY_MONITOR", "{node} battery degraded — estimated runtime reduced to {hours}h"),
    ("WEATHER_ADVISORY", "NWS {weather} Warning in effect for {area} through {end_time}"),
    ("OSPF_RECONVERGENCE", "OSPF reconvergence in progress — {count} adjacencies rebuilding"),
    ("ALARM_FLOOD", "NOC receiving {count}+ alarms/min from {area} — auto-correlation active"),
]

SERVICES = [
    "BROADBAND", "IPTV", "VOIP", "MOBILE_VOICE", "MOBILE_DATA",
    "MOBILE_5G", "MOBILE_BACKHAUL", "ENTERPRISE_MPLS", "CLOUD_CONNECT",
    "COLOCATION", "SIP_TRUNKING", "IOT_CONNECTIVITY",
]

ENTERPRISE_SERVICES = ["ENTERPRISE_MPLS", "CLOUD_CONNECT", "SIP_TRUNKING", "COLOCATION", "MOBILE_BACKHAUL"]
RESIDENTIAL_SERVICES = ["BROADBAND", "IPTV", "VOIP", "MOBILE_VOICE", "MOBILE_DATA", "MOBILE_5G"]
SMB_SERVICES = ["BROADBAND", "VOIP", "CLOUD_CONNECT", "MOBILE_DATA"]

COMPANY_TEMPLATES = {
    "ENTERPRISE": {
        "PLATINUM": [
            {"pattern": "{city} Health Systems", "industry": "Healthcare", "value_range": (1500000, 3000000), "sla": "99.999%", "credit_rate": "10x hourly rate per minute of downtime", "criticality": "LIFE_SAFETY", "note": "CRITICAL: Operates emergency telemedicine services. Any outage may impact patient care."},
            {"pattern": "City of {city} — Public Safety", "industry": "Government — Emergency Services", "value_range": (1200000, 2500000), "sla": "99.999%", "credit_rate": "15x hourly rate per minute of downtime", "criticality": "LIFE_SAFETY", "note": "GOVERNMENT PRIORITY: 911 services depend on this connectivity."},
            {"pattern": "{city} Regional Medical Center", "industry": "Healthcare", "value_range": (1800000, 3500000), "sla": "99.999%", "credit_rate": "10x hourly rate per minute of downtime", "criticality": "LIFE_SAFETY", "note": "Level 1 trauma center. Network supports critical monitoring systems."},
            {"pattern": "{adj} Federal Credit Union", "industry": "Financial Services", "value_range": (2000000, 4000000), "sla": "99.999%", "credit_rate": "12x hourly rate per minute of downtime", "criticality": "HIGH", "note": "Real-time transaction processing. PCI-DSS compliance requirements."},
        ],
        "GOLD": [
            {"pattern": "{adj} Financial Group", "industry": "Financial Services", "value_range": (600000, 1200000), "sla": "99.99%", "credit_rate": "5x hourly rate per minute of downtime", "criticality": "HIGH", "note": "Financial trading operations. Latency-sensitive."},
            {"pattern": "{adj} Logistics International", "industry": "Logistics & Supply Chain", "value_range": (400000, 900000), "sla": "99.99%", "credit_rate": "3x hourly rate per minute of downtime", "criticality": "HIGH", "note": "IoT fleet tracking and warehouse automation."},
            {"pattern": "{city} Manufacturing Corp", "industry": "Manufacturing", "value_range": (500000, 1000000), "sla": "99.99%", "credit_rate": "4x hourly rate per minute of downtime", "criticality": "HIGH", "note": "SCADA and industrial control systems on this circuit."},
            {"pattern": "{adj} Insurance Partners", "industry": "Insurance", "value_range": (350000, 800000), "sla": "99.99%", "credit_rate": "3x hourly rate per minute of downtime", "criticality": "MEDIUM", "note": "Claims processing and customer portal."},
            {"pattern": "{city} Data Solutions", "industry": "Technology", "value_range": (450000, 950000), "sla": "99.99%", "credit_rate": "5x hourly rate per minute of downtime", "criticality": "HIGH", "note": "SaaS provider hosting 200+ client applications."},
        ],
        "SILVER": [
            {"pattern": "{adj} Academy — School District", "industry": "Education", "value_range": (200000, 500000), "sla": "99.9%", "credit_rate": "2x hourly rate per hour of downtime", "criticality": "MEDIUM", "note": "Online learning platform. Extended outage during school hours requires parent notification."},
            {"pattern": "{adj} Hotel & Conference Center", "industry": "Hospitality", "value_range": (150000, 400000), "sla": "99.9%", "credit_rate": "2x hourly rate per hour of downtime", "criticality": "MEDIUM", "note": "Guest WiFi and POS systems."},
            {"pattern": "{city} Legal Associates", "industry": "Legal", "value_range": (180000, 350000), "sla": "99.9%", "credit_rate": "2x hourly rate per hour of downtime", "criticality": "MEDIUM", "note": "Cloud-based case management. Court filing deadlines at risk during outage."},
            {"pattern": "{adj} Media Group", "industry": "Media & Entertainment", "value_range": (250000, 600000), "sla": "99.9%", "credit_rate": "2x hourly rate per hour of downtime", "criticality": "MEDIUM", "note": "Live broadcast operations. Outage during air time is catastrophic."},
        ],
    },
    "GOVERNMENT": [
        {"pattern": "{city} County — Emergency Management", "industry": "Government — Emergency Services", "value_range": (800000, 2000000), "sla": "99.999%", "credit_rate": "15x hourly rate per minute of downtime", "criticality": "LIFE_SAFETY", "note": "Emergency management coordination. FEMA compliance."},
        {"pattern": "{city} Police Department", "industry": "Government — Law Enforcement", "value_range": (600000, 1500000), "sla": "99.999%", "credit_rate": "12x hourly rate per minute of downtime", "criticality": "LIFE_SAFETY", "note": "Body cam uploads and dispatch systems."},
        {"pattern": "{city} Fire & Rescue", "industry": "Government — Fire Services", "value_range": (500000, 1200000), "sla": "99.999%", "credit_rate": "12x hourly rate per minute of downtime", "criticality": "LIFE_SAFETY", "note": "CAD dispatch and station alerting systems."},
        {"pattern": "{city} Water Authority", "industry": "Government — Utilities", "value_range": (400000, 900000), "sla": "99.99%", "credit_rate": "8x hourly rate per minute of downtime", "criticality": "HIGH", "note": "SCADA monitoring for water treatment and distribution."},
    ],
}

VIP_TEMPLATES = [
    {"pattern": "Governor {name}", "note": "State Governor — residence. Reputational risk. White-glove support."},
    {"pattern": "Mayor {name}", "note": "City Mayor. Any disruption gets media attention."},
    {"pattern": "Coach {name}", "note": "Head coach of professional sports team. Social media amplification risk."},
    {"pattern": "{name}", "note": "High-profile philanthropist. Board member of local chamber of commerce."},
    {"pattern": "Dr. {name}", "note": "Prominent surgeon and community leader. Frequent media appearances."},
    {"pattern": "Judge {name}", "note": "Federal judge. Security-sensitive residence."},
    {"pattern": "{name}", "note": "Fortune 500 CEO residence. Expects executive-level treatment."},
    {"pattern": "{name}", "note": "Celebrity chef with large social following. Complaints go viral."},
]

SMB_TEMPLATES = [
    {"pattern": "{name}'s Restaurant Group", "industry": "Food & Beverage", "note": "POS systems require internet. Outage during service causes direct revenue loss."},
    {"pattern": "{adj} Dental Clinics", "industry": "Healthcare — Dental", "note": "Cloud-based patient records. Outage prevents access to charts."},
    {"pattern": "{adj} Auto Dealership", "industry": "Automotive", "note": "Online inventory and financing systems."},
    {"pattern": "{name} & Associates Law Firm", "industry": "Legal", "note": "Cloud-based case management and VoIP phones."},
    {"pattern": "{adj} Veterinary Hospital", "industry": "Healthcare — Veterinary", "note": "Digital imaging and patient management."},
    {"pattern": "{city} Fitness Center", "industry": "Health & Fitness", "note": "Member check-in and payment processing."},
    {"pattern": "{adj} Boutique Hotel", "industry": "Hospitality", "note": "Booking system and guest WiFi."},
    {"pattern": "{name}'s Pharmacy", "industry": "Pharmacy", "note": "Prescription processing requires live connection to insurance systems."},
    {"pattern": "{adj} Real Estate Group", "industry": "Real Estate", "note": "MLS access and virtual tour hosting."},
    {"pattern": "{city} Print & Ship", "industry": "Retail Services", "note": "POS and shipping label generation."},
]

FIRST_NAMES = [
    "James", "Sarah", "Michael", "Patricia", "Robert", "Angela", "David", "Linda",
    "Marcus", "Elena", "Kevin", "Maria", "Darnell", "Chen", "Raj", "Aisha",
    "Thomas", "Priya", "Carlos", "Yuki", "Ahmed", "Fatima", "Brian", "Olivia",
    "Derek", "Sophia", "Kwame", "Isabella", "Andre", "Valentina", "Ricardo",
    "Natasha", "William", "Grace", "Jamal", "Evelyn", "Daniel", "Nadia",
]

LAST_NAMES = [
    "Chen", "Williams", "Torres", "Kim", "Brooks", "Patel", "Hammond", "Wright",
    "Foster", "Rosario", "Whitfield", "Daniels", "Morrison", "Nakamura", "Singh",
    "Okonkwo", "Rivera", "Johansson", "Dubois", "Martinez", "Kowalski", "Gupta",
    "Andersson", "Fernandez", "Okafor", "Takahashi", "Petrov", "Larsson",
]

ADJECTIVES = [
    "Meridian", "Pinnacle", "Summit", "Horizon", "Crestview", "Sterling",
    "Beacon", "Cascade", "Ironwood", "Sapphire", "Redstone", "Goldleaf",
    "Silveroak", "Peachtree", "Magnolia", "Cypress", "Broadstone", "Clearwater",
    "Eastpoint", "Westfield", "Northgate", "Southridge", "Highland", "Lakewood",
]

STREETS = [
    "Peachtree Industrial Blvd", "Roswell Road", "Buford Highway", "Memorial Drive",
    "Ponce de Leon Ave", "Northside Drive", "Piedmont Road", "Lenox Road",
    "Johnson Ferry Road", "Holcomb Bridge Road", "Pleasant Hill Road",
]

WEATHER_EVENTS = ["Ice Storm", "Severe Thunderstorm", "Tornado", "High Wind", "Winter Storm"]

CREW_PREFIXES = ["FC", "DC", "GEN", "SPLICE", "POWER", "EMERG"]
CREW_SUFFIXES = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO"]
DISPATCH_STATUSES = ["EN_ROUTE", "ON_SITE", "DIAGNOSING", "REPAIRING", "EN_ROUTE_DELAYED"]

REDUNDANCY_STATUSES = [
    "FAILOVER_PARTIAL — Ring protection switched for {partial} nodes. {failed} nodes have NO redundant path.",
    "FAILOVER_DEGRADED — Backup path active but severely congested. QoS policies shedding best-effort traffic.",
    "FAILOVER_COMPLETE — All traffic rerouted via backup paths. No customer impact expected unless backup fails.",
    "NO_FAILOVER — No redundant path available. Full service loss for affected nodes.",
    "TIME_LIMITED — All sites on battery. No generator on-site. Clock is ticking.",
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
class TelcoDataGenerator:
    """Generates realistic, seeded telco network and customer data."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.base_date = datetime(2026, 3, 10, 8, 0, 0, tzinfo=timezone.utc)
        self._used_names: set[str] = set()
        self._zone_cache: dict[str, list[str]] = {}
        self._account_counter = {"ENT": 0, "GOV": 0, "VIP": 0, "SMB": 0}

    def _rand_name(self) -> str:
        for _ in range(100):
            name = f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}"
            if name not in self._used_names:
                self._used_names.add(name)
                return name
        return f"Agent {self.rng.randint(1000,9999)}"

    def _rand_phone(self) -> str:
        return f"+1-{self.rng.randint(200,999)}-555-{self.rng.randint(1000,9999)}"

    def _rand_email(self, name: str, domain: str) -> str:
        parts = name.lower().split()
        return f"{parts[0][0]}.{parts[-1]}@{domain}"

    def _rand_circuit_id(self, prefix: str) -> str:
        return f"{prefix}-{self.rng.randint(1000,9999)}"

    def _get_zones(self, area: dict) -> list[str]:
        code = area["code"]
        if code not in self._zone_cache:
            num = self.rng.randint(2, len(ZONE_SUFFIXES))
            self._zone_cache[code] = [f"ZONE-{code}-{s}" for s in ZONE_SUFFIXES[:num]]
        return self._zone_cache[code]

    def _next_account_id(self, prefix: str) -> str:
        self._account_counter[prefix] += 1
        return f"{prefix}-{self._account_counter[prefix]:03d}"

    def generate_alerts(self, count: int) -> list[dict]:
        """Generate `count` realistic network alerts."""
        alerts = []
        for i in range(count):
            alert_type = self.rng.choice(list(ALERT_TYPES.keys()))
            config = ALERT_TYPES[alert_type]
            area = self.rng.choice(METRO_AREAS)
            code = area["code"]
            zones = self._get_zones(area)
            affected_zones = self.rng.sample(zones, min(len(zones), self.rng.randint(1, len(zones))))

            # Severity
            sev_roll = self.rng.random()
            cumulative = 0
            severity = "MAJOR"
            for sev, weight in config["severity_weights"].items():
                cumulative += weight
                if sev_roll <= cumulative:
                    severity = sev
                    break

            # Timestamp
            offset_minutes = self.rng.randint(0, 720)
            timestamp = self.base_date + timedelta(minutes=offset_minutes)

            # Infrastructure details
            n1, n2 = self.rng.randint(4400, 4500), self.rng.randint(4400, 4500)
            nodes_down = [f"{code}-OLT-{self.rng.randint(4400, 4500)}" for _ in range(self.rng.randint(2, 6))]
            cell_towers = [f"TWR-{code}-{self.rng.randint(100, 300)}" for _ in range(self.rng.randint(2, 8))]
            num_services = self.rng.randint(2, 6)
            services = self.rng.sample(SERVICES, min(num_services, len(SERVICES)))

            # ETR
            etr_low, etr_high = config["etr_range"]
            etr_h = self.rng.randint(etr_low, etr_high)

            # Build title
            title = self.rng.choice(config["titles"]).format(
                ring=self.rng.randint(1, 12), area=area["name"], code=code,
                seg=self.rng.randint(1, 50), route=self.rng.randint(100, 999),
                router=f"CR-{code}-{n1:02d}",
            )

            # Build description
            desc = self.rng.choice(config["descriptions"]).format(
                ring=self.rng.randint(1, 12), code=code, area=area["name"],
                n1=n1, n2=n2, sp=self.rng.randint(5000, 9999),
                lat=round(area["lat"] + self.rng.uniform(-0.05, 0.05), 4),
                lon=round(area["lon"] + self.rng.uniform(-0.05, 0.05), 4),
                span=round(self.rng.uniform(2, 25), 1),
                street=self.rng.choice(STREETS),
                pole=self.rng.randint(1000, 9999),
                partial=self.rng.randint(1, 4), total=self.rng.randint(4, 8),
                slot1=self.rng.randint(1, 8), slot2=self.rng.randint(1, 8),
                downstream=self.rng.randint(4, 20),
                util=self.rng.randint(200, 400),
                circuits=self.rng.randint(5, 50),
                asn=self.rng.randint(10000, 65000),
                switches=self.rng.randint(3, 15),
                sites=len(cell_towers),
                battery=self.rng.randint(2, 6),
                util_etr=self.rng.randint(2, 8),
                node=self.rng.choice(nodes_down) if nodes_down else f"{code}-OLT-{n1}",
                l1=self.rng.randint(1, 20), l2=self.rng.randint(21, 40),
            )

            # Related alerts
            num_related = self.rng.randint(1, 4)
            related = []
            for j in range(num_related):
                rel_type, rel_desc = self.rng.choice(RELATED_ALERT_TYPES)
                related.append({
                    "alert_id": f"ALT-{timestamp.strftime('%Y-%m-%d')}-{(i*10+j+1):04d}",
                    "type": rel_type,
                    "description": rel_desc.format(
                        node=self.rng.choice(nodes_down) if nodes_down else f"{code}-NODE-{self.rng.randint(100,999)}",
                        n=self.rng.randint(1, 10), pct=self.rng.randint(30, 80),
                        count=self.rng.randint(3, 30), area=area["name"],
                        jitter=self.rng.randint(20, 100), hours=round(self.rng.uniform(1.5, 4), 1),
                        weather=self.rng.choice(WEATHER_EVENTS),
                        end_time=f"{timestamp.strftime('%Y-%m-%d')} {self.rng.randint(0,23):02d}:00Z",
                    ),
                })

            # Estimated customers
            est_customers = self.rng.randint(2000, 60000)

            alert = {
                "alert_id": f"ALT-{timestamp.strftime('%Y-%m-%d')}-{self.rng.randint(1000,9999)}",
                "timestamp": timestamp.isoformat(),
                "severity": severity,
                "source_system": "NOC-PRIME-MONITOR-v4.2",
                "alert_type": alert_type,
                "title": title,
                "description": desc,
                "affected_infrastructure": {
                    "nodes_down": nodes_down,
                    "cell_towers_affected": cell_towers,
                    "distribution_hubs": [f"DHUB-{code}-{k:02d}" for k in range(1, self.rng.randint(2, 5))],
                    "exchanges_impacted": [f"EX-{code}-MAIN"] + ([f"EX-{code}-BACKUP"] if self.rng.random() > 0.3 else []),
                },
                "affected_zones": affected_zones,
                "services_impacted": services,
                "redundancy_status": self.rng.choice(REDUNDANCY_STATUSES).format(
                    partial=self.rng.randint(1, 3), failed=self.rng.randint(1, 4),
                ),
                "estimated_customers_affected": est_customers,
                "preliminary_etr": f"{etr_h}-{etr_h + self.rng.randint(1, 3)} hours",
                "field_dispatch": {
                    "crew_id": f"{self.rng.choice(CREW_PREFIXES)}-{code}-{self.rng.choice(CREW_SUFFIXES)}",
                    "eta_to_site": f"{self.rng.randint(15, 120)} minutes" if self.rng.random() > 0.2 else "Already on-site",
                    "status": self.rng.choice(DISPATCH_STATUSES),
                },
                "escalation_level": f"P1-SEV{self.rng.randint(1, 3)}" if severity in ("CRITICAL", "MAJOR") else "P2",
                "related_alerts": related,
            }
            alerts.append(alert)

        return alerts

    def generate_customers(self, count: int) -> list[dict]:
        """Generate `count` customer accounts with realistic distribution."""
        customers = []

        # Distribution: ~10% platinum, ~15% gold, ~15% silver, ~10% gov, ~10% VIP res, ~25% SMB, +1 residential bulk
        targets = {
            "platinum": max(1, int(count * 0.10)),
            "gold": max(1, int(count * 0.15)),
            "silver": max(1, int(count * 0.15)),
            "government": max(1, int(count * 0.10)),
            "vip": max(1, int(count * 0.10)),
            "smb": max(1, int(count * 0.25)),
        }

        all_zones = []
        for area in METRO_AREAS:
            all_zones.extend(self._get_zones(area))

        def _make_locations(num: int, criticality: str, circuit_prefix: str) -> list[dict]:
            locs = []
            for _ in range(num):
                zone = self.rng.choice(all_zones)
                locs.append({
                    "site_name": f"Site {self.rng.choice(ADJECTIVES)} {''.join(self.rng.choices(string.ascii_uppercase, k=2))}",
                    "zone": zone,
                    "circuit_ids": [self._rand_circuit_id(circuit_prefix) for _ in range(self.rng.randint(1, 3))],
                    "criticality": criticality,
                })
            return locs

        def _make_contact(name: str, role: str, domain: str, channel: str = "email") -> dict:
            return {
                "name": name,
                "role": role,
                "email": self._rand_email(name, domain),
                "phone": self._rand_phone(),
                "preferred_channel": channel,
            }

        # Enterprise customers
        for tier in ("PLATINUM", "GOLD", "SILVER"):
            tier_key = tier.lower()
            templates = COMPANY_TEMPLATES["ENTERPRISE"][tier]
            for _ in range(targets[tier_key]):
                template = self.rng.choice(templates)
                city = self.rng.choice(METRO_AREAS)["city"]
                adj = self.rng.choice(ADJECTIVES)
                company = template["pattern"].format(city=city, adj=adj)
                domain = company.lower().replace(" ", "").replace("—", "").replace("&", "")[:20] + ".com"
                name1 = self._rand_name()
                name2 = self._rand_name()
                value = self.rng.randint(*template["value_range"])

                customers.append({
                    "account_id": self._next_account_id("ENT"),
                    "company_name": company,
                    "account_type": "ENTERPRISE",
                    "tier": tier,
                    "industry": template["industry"],
                    "contract_value_annual": value,
                    "sla_tier": template["sla"],
                    "sla_credit_rate": template["credit_rate"],
                    "primary_contact": _make_contact(name1, "CTO", domain, self.rng.choice(["email", "phone"])),
                    "escalation_contact": _make_contact(name2, "VP Infrastructure", domain),
                    "services": self.rng.sample(ENTERPRISE_SERVICES, self.rng.randint(2, 4)),
                    "locations": _make_locations(self.rng.randint(1, 4), template["criticality"], "MPLS"),
                    "notes": template["note"],
                })

        # Government customers
        gov_templates = COMPANY_TEMPLATES["GOVERNMENT"]
        for _ in range(targets["government"]):
            template = self.rng.choice(gov_templates)
            city = self.rng.choice(METRO_AREAS)["city"]
            company = template["pattern"].format(city=city)
            domain = company.lower().replace(" ", "").replace("—", "")[:15] + ".gov"
            name1 = self._rand_name()
            name2 = self._rand_name()
            value = self.rng.randint(*template["value_range"])

            customers.append({
                "account_id": self._next_account_id("GOV"),
                "company_name": company,
                "account_type": "GOVERNMENT",
                "tier": "PLATINUM",
                "industry": template["industry"],
                "contract_value_annual": value,
                "sla_tier": template["sla"],
                "sla_credit_rate": template["credit_rate"],
                "primary_contact": _make_contact(name1, "Director", domain, "phone"),
                "escalation_contact": _make_contact(name2, "City IT Director", domain),
                "services": ["ENTERPRISE_MPLS", "SIP_TRUNKING", "MOBILE_BACKHAUL", "MOBILE_VOICE"],
                "locations": _make_locations(self.rng.randint(2, 5), template["criticality"], "MPLS-GOV"),
                "notes": template["note"],
            })

        # VIP residential
        for _ in range(targets["vip"]):
            template = self.rng.choice(VIP_TEMPLATES)
            name = self._rand_name()
            vip_name = template["pattern"].format(name=name)

            customers.append({
                "account_id": self._next_account_id("VIP"),
                "company_name": None,
                "account_type": "VIP_RESIDENTIAL",
                "tier": "VIP",
                "customer_name": vip_name,
                "industry": None,
                "contract_value_annual": self.rng.choice([3600, 4800, 7200, 9600]),
                "sla_tier": None,
                "primary_contact": {
                    "name": vip_name,
                    "email": self._rand_email(name, "personal.com"),
                    "phone": self._rand_phone(),
                    "preferred_channel": "sms",
                },
                "services": self.rng.sample(RESIDENTIAL_SERVICES, self.rng.randint(3, 5)),
                "locations": [{
                    "site_name": "Private Residence",
                    "zone": self.rng.choice(all_zones),
                    "circuit_ids": [self._rand_circuit_id("RES-VIP")],
                    "criticality": self.rng.choice(["HIGH", "MEDIUM"]),
                }],
                "notes": template["note"],
            })

        # SMB customers
        for _ in range(targets["smb"]):
            template = self.rng.choice(SMB_TEMPLATES)
            name = self._rand_name()
            city = self.rng.choice(METRO_AREAS)["city"]
            adj = self.rng.choice(ADJECTIVES)
            company = template["pattern"].format(name=name.split()[0], city=city, adj=adj)
            domain = company.lower().replace(" ", "").replace("'", "")[:15] + ".com"

            customers.append({
                "account_id": self._next_account_id("SMB"),
                "company_name": company,
                "account_type": "SMB",
                "tier": "STANDARD",
                "industry": template["industry"],
                "contract_value_annual": self.rng.randint(6000, 36000),
                "sla_tier": None,
                "primary_contact": _make_contact(name, "Owner", domain, self.rng.choice(["sms", "email"])),
                "services": self.rng.sample(SMB_SERVICES, self.rng.randint(2, 3)),
                "locations": _make_locations(self.rng.randint(1, 3), "MEDIUM", "BB-SMB"),
                "notes": template["note"],
            })

        # Residential bulk entry
        zone_subs = {}
        for zone in all_zones:
            zone_subs[zone] = self.rng.randint(3000, 20000)

        customers.append({
            "account_id": "RES-BULK",
            "company_name": None,
            "account_type": "RESIDENTIAL_BULK",
            "tier": "STANDARD",
            "customer_segment": "General Residential Subscribers",
            "total_subscribers_by_zone": zone_subs,
            "services": RESIDENTIAL_SERVICES,
            "notification_channels": ["sms_blast", "email_blast", "app_push_notification", "status_page_update"],
            "notes": "Mass notification via automated systems. Status page URL: status.ourtelco.com",
        })

        return customers

    def generate(self, num_alerts: int = 3, num_customers: int = 15) -> dict:
        """Generate a complete dataset."""
        return {
            "alerts": self.generate_alerts(num_alerts),
            "customers": self.generate_customers(num_customers),
        }


# ---------------------------------------------------------------------------
# Presets for common scenarios
# ---------------------------------------------------------------------------
PRESETS = {
    "demo": {"seed": 42, "alerts": 3, "customers": 15},
    "stress-test": {"seed": 7, "alerts": 25, "customers": 500},
    "small": {"seed": 1, "alerts": 1, "customers": 5},
    "medium": {"seed": 99, "alerts": 10, "customers": 100},
    "large": {"seed": 2026, "alerts": 50, "customers": 1000},
}


def generate_and_save(seed: int = 42, num_alerts: int = 3, num_customers: int = 15, output_dir: Path | None = None):
    """Generate data and write to JSON files."""
    if output_dir is None:
        output_dir = Path(__file__).parent

    gen = TelcoDataGenerator(seed=seed)
    data = gen.generate(num_alerts, num_customers)

    alerts_path = output_dir / "network_alerts.json"
    customers_path = output_dir / "customer_accounts.json"

    alerts_path.write_text(json.dumps(data["alerts"], indent=2))
    customers_path.write_text(json.dumps(data["customers"], indent=2))

    print(f"Generated {len(data['alerts'])} alerts → {alerts_path}")
    print(f"Generated {len(data['customers'])} customers → {customers_path}")
    print(f"Seed: {seed}")

    # Print summary
    types = {}
    for c in data["customers"]:
        t = c.get("account_type", "UNKNOWN")
        types[t] = types.get(t, 0) + 1
    print(f"\nCustomer breakdown: {json.dumps(types, indent=2)}")

    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate telco network outage demo data")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--alerts", type=int, default=3, help="Number of network alerts to generate")
    parser.add_argument("--customers", type=int, default=15, help="Number of customer accounts to generate")
    parser.add_argument("--preset", choices=PRESETS.keys(), help="Use a preset configuration")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for JSON files")

    args = parser.parse_args()

    if args.preset:
        preset = PRESETS[args.preset]
        seed, num_alerts, num_customers = preset["seed"], preset["alerts"], preset["customers"]
    else:
        seed, num_alerts, num_customers = args.seed, args.alerts, args.customers

    out = Path(args.output_dir) if args.output_dir else None
    generate_and_save(seed=seed, num_alerts=num_alerts, num_customers=num_customers, output_dir=out)
