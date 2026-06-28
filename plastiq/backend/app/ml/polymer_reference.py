"""
Polymer reference data for pyrolysis suitability and yield prediction.

This is the domain knowledge base the entire prediction engine is built on.
Values are sourced from published pyrolysis literature ranges (typical lab/pilot
scale figures) and are intentionally conservative, central estimates. They are
configurable per-deployment via the AI_SETTINGS table (see models/settings.py) —
a plant should calibrate these against its own historical pyrolysis_runs data
over time (see services/calibration.py).
"""

from enum import Enum


class PlasticType(str, Enum):
    PET = "PET"
    HDPE = "HDPE"
    LDPE = "LDPE"
    PP = "PP"
    PS = "PS"
    PVC = "PVC"
    MIXED = "MIXED"
    OTHER = "OTHER"


class Suitability(str, Enum):
    HIGHLY_SUITABLE = "HIGHLY_SUITABLE"
    MODERATE = "MODERATE"
    POOR_HAZARDOUS = "POOR_HAZARDOUS"
    UNKNOWN = "UNKNOWN"


# Central per-polymer reference table.
# oil_yield / gas_yield / char_yield / wax_yield are mass fractions of the
# INPUT plastic mass and should sum to <= 1.0 (remainder is process loss / moisture).
POLYMER_PROFILE = {
    PlasticType.HDPE: {
        "label": "High-Density Polyethylene",
        "common_items": "Detergent containers, milk jugs, crates",
        "suitability": Suitability.HIGHLY_SUITABLE,
        "oil_yield": 0.80,
        "gas_yield": 0.12,
        "char_yield": 0.06,
        "wax_yield": 0.02,
        "hazard_notes": None,
        "max_recommended_contamination_pct": 5.0,
    },
    PlasticType.LDPE: {
        "label": "Low-Density Polyethylene",
        "common_items": "Plastic bags, film, wraps",
        "suitability": Suitability.HIGHLY_SUITABLE,
        "oil_yield": 0.85,
        "gas_yield": 0.09,
        "char_yield": 0.04,
        "wax_yield": 0.02,
        "hazard_notes": None,
        "max_recommended_contamination_pct": 5.0,
    },
    PlasticType.PP: {
        "label": "Polypropylene",
        "common_items": "Food containers, bottle caps, straws",
        "suitability": Suitability.HIGHLY_SUITABLE,
        "oil_yield": 0.75,
        "gas_yield": 0.15,
        "char_yield": 0.07,
        "wax_yield": 0.03,
        "hazard_notes": None,
        "max_recommended_contamination_pct": 5.0,
    },
    PlasticType.PS: {
        "label": "Polystyrene",
        "common_items": "Foam products, disposable cutlery, trays",
        "suitability": Suitability.MODERATE,
        "oil_yield": 0.70,
        "gas_yield": 0.20,
        "char_yield": 0.08,
        "wax_yield": 0.02,
        "hazard_notes": "Styrene off-gassing; requires good vapor capture.",
        "max_recommended_contamination_pct": 10.0,
    },
    PlasticType.PET: {
        "label": "Polyethylene Terephthalate",
        "common_items": "Water bottles, beverage containers",
        "suitability": Suitability.POOR_HAZARDOUS,
        "oil_yield": 0.30,
        "gas_yield": 0.15,
        "char_yield": 0.45,
        "wax_yield": 0.0,
        "hazard_notes": (
            "Low oil yield; tends to char and can produce terephthalic acid "
            "residues that foul reactor surfaces. Mechanical recycling is "
            "strongly preferred over pyrolysis for PET."
        ),
        "max_recommended_contamination_pct": 5.0,
    },
    PlasticType.PVC: {
        "label": "Polyvinyl Chloride",
        "common_items": "Pipes, blister packaging, vinyl products",
        "suitability": Suitability.POOR_HAZARDOUS,
        "oil_yield": 0.0,
        "gas_yield": 0.0,
        "char_yield": 0.0,
        "wax_yield": 0.0,
        "hazard_notes": (
            "Releases hydrogen chloride (HCl) gas on thermal decomposition. "
            "Corrodes reactor internals and poisons catalysts; contaminates "
            "oil product with chlorinated compounds. MUST be removed before "
            "feedstock enters the reactor, not merely down-weighted."
        ),
        "max_recommended_contamination_pct": 1.0,
    },
    PlasticType.MIXED: {
        "label": "Mixed / Co-mingled Plastics",
        "common_items": "Unsorted multi-polymer waste streams",
        "suitability": Suitability.MODERATE,
        "oil_yield": 0.55,
        "gas_yield": 0.15,
        "char_yield": 0.20,
        "wax_yield": 0.02,
        "hazard_notes": (
            "Yield is volatile and depends on actual polymer composition; "
            "treat this figure as a low-confidence estimate until sorted."
        ),
        "max_recommended_contamination_pct": 8.0,
    },
    PlasticType.OTHER: {
        "label": "Other / Unidentified",
        "common_items": "Unclassified or low-confidence detections",
        "suitability": Suitability.UNKNOWN,
        "oil_yield": 0.40,
        "gas_yield": 0.15,
        "char_yield": 0.30,
        "wax_yield": 0.0,
        "hazard_notes": "Unidentified composition; manual inspection recommended.",
        "max_recommended_contamination_pct": 5.0,
    },
}

# Default market reference prices (USD per metric ton). Configurable in AI Settings;
# the BI engine should pull live values from a market-price feed/service when one
# is configured, falling back to these defaults otherwise.
DEFAULT_PRICING = {
    "pyrolysis_oil_usd_per_ton": 600.0,
    "carbon_black_usd_per_ton": 250.0,
    "wax_usd_per_ton": 300.0,
    "pyrolysis_gas_usd_per_ton": 0.0,  # typically combusted on-site for process heat, not sold
}

# Risk thresholds (overridable per-factory in AI Settings) — pulled from the
# generic RISK DETECTION RULES, adapted to this domain.
RISK_THRESHOLDS = {
    "pvc_contamination_pct_warning": 2.0,
    "pvc_contamination_pct_critical": 5.0,
    "machine_utilization_pct_warning": 90.0,
    "safety_stock_feedstock_tons": 1.0,
    "min_target_profit_margin_pct": 15.0,
    "low_confidence_detection_threshold": 0.60,
}
