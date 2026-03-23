"""Indeed search presets for Xwell's active roles.

Each preset defines the search configuration for a specific Xwell position:
job title search terms, location, required certifications, role category,
and scoring weights used by the filtering service.

These presets are used as defaults when syncing jobs from Indeed via the
``POST /scrape/preset`` endpoint and when auto-scoring inbound candidates.
"""

INDEED_ROLE_PRESETS = {
    "massage_therapist": {
        "title": "Massage Therapist",
        "search_terms": [
            "massage therapist",
            "licensed massage therapist",
            "LMT",
            "spa massage therapist",
        ],
        "location": "Naples, FL",
        "required_certifications": ["massage_therapy"],
        "preferred_certifications": ["aromatherapy", "hot_stone", "deep_tissue"],
        "role_category": "spa",
        "department": "Spa",
        "shift_schedule": ["morning", "afternoon", "evening"],
        "scoring_weights": {
            "certifications": 0.40,
            "availability": 0.25,
            "experience": 0.20,
            "location": 0.15,
        },
    },
    "nail_technician": {
        "title": "Nail Technician",
        "search_terms": [
            "nail technician",
            "nail tech",
            "manicurist",
            "licensed nail technician",
        ],
        "location": "Naples, FL",
        "required_certifications": ["nail_technician"],
        "preferred_certifications": ["gel_nails", "acrylic_nails"],
        "role_category": "spa",
        "department": "Spa",
        "shift_schedule": ["morning", "afternoon", "evening"],
        "scoring_weights": {
            "certifications": 0.40,
            "availability": 0.25,
            "experience": 0.20,
            "location": 0.15,
        },
    },
    "esthetician": {
        "title": "Esthetician",
        "search_terms": [
            "esthetician",
            "licensed esthetician",
            "skincare specialist",
            "facial specialist",
        ],
        "location": "Naples, FL",
        "required_certifications": ["esthetician"],
        "preferred_certifications": ["microdermabrasion", "chemical_peel", "lash_extensions"],
        "role_category": "spa",
        "department": "Spa",
        "shift_schedule": ["morning", "afternoon", "evening"],
        "scoring_weights": {
            "certifications": 0.40,
            "availability": 0.25,
            "experience": 0.20,
            "location": 0.15,
        },
    },
    "spa_manager": {
        "title": "Spa Manager",
        "search_terms": [
            "spa manager",
            "salon manager",
            "spa director",
            "wellness manager",
        ],
        "location": "Naples, FL",
        "required_certifications": [],
        "preferred_certifications": ["cosmetology", "business_management"],
        "role_category": "management",
        "department": "Management",
        "shift_schedule": ["morning", "afternoon"],
        "scoring_weights": {
            "certifications": 0.15,
            "availability": 0.25,
            "experience": 0.40,
            "location": 0.20,
        },
    },
    "guest_services_associate": {
        "title": "Guest Services Associate",
        "search_terms": [
            "guest service associate",
            "front desk spa",
            "spa receptionist",
            "guest services representative",
        ],
        "location": "Naples, FL",
        "required_certifications": [],
        "preferred_certifications": ["customer_service"],
        "role_category": "guest_services",
        "department": "Guest Services",
        "shift_schedule": ["morning", "afternoon", "evening", "weekend"],
        "scoring_weights": {
            "certifications": 0.15,
            "availability": 0.35,
            "experience": 0.25,
            "location": 0.25,
        },
    },
    "biosecurity_specialist": {
        "title": "Biosecurity Specialist",
        "search_terms": [
            "biosecurity specialist",
            "bio-security specialist",
            "health screening specialist",
            "biosecurity officer",
        ],
        "location": "Naples, FL",
        "required_certifications": ["biosecurity"],
        "preferred_certifications": ["first_aid", "osha_safety"],
        "role_category": "biosecurity",
        "department": "Biosecurity",
        "shift_schedule": ["morning", "afternoon", "evening", "overnight", "weekend"],
        "scoring_weights": {
            "certifications": 0.25,
            "availability": 0.35,
            "experience": 0.20,
            "location": 0.20,
        },
    },
}


def get_preset(name: str) -> dict:
    """Return a single preset by name, or raise KeyError."""
    return INDEED_ROLE_PRESETS[name]


def get_all_presets() -> dict:
    """Return all role presets."""
    return dict(INDEED_ROLE_PRESETS)


def get_search_presets_for_scraper() -> dict:
    """Convert role presets to the SEARCH_PRESETS format used by the scraper.

    Returns a dict compatible with ``src.services.filtering.SEARCH_PRESETS``,
    keyed by preset name with ``search_terms``, ``department``, and
    ``role_category`` fields.
    """
    return {
        name: {
            "search_terms": preset["search_terms"],
            "department": preset["department"],
            "role_category": preset["role_category"],
        }
        for name, preset in INDEED_ROLE_PRESETS.items()
    }


def get_job_defaults(preset_name: str) -> dict:
    """Return default Job fields derived from a preset.

    Useful when creating a Job record from a preset — provides
    required_certifications, preferred_certifications, shift_schedule,
    role_category, and location.
    """
    preset = INDEED_ROLE_PRESETS[preset_name]
    return {
        "title": preset["title"],
        "location": preset["location"],
        "department": preset["department"],
        "role_category": preset["role_category"],
        "required_certifications": list(preset["required_certifications"]),
        "preferred_certifications": list(preset["preferred_certifications"]),
        "shift_schedule": list(preset["shift_schedule"]),
    }
