"""Tests for Indeed role presets configuration."""

from src.config.indeed_presets import (
    INDEED_ROLE_PRESETS,
    get_preset,
    get_all_presets,
    get_search_presets_for_scraper,
    get_job_defaults,
)
from src.services.filtering import SEARCH_PRESETS


EXPECTED_ROLES = [
    "massage_therapist",
    "nail_technician",
    "esthetician",
    "spa_manager",
    "guest_services_associate",
    "biosecurity_specialist",
]


class TestIndeedRolePresets:
    """Verify all six Xwell role presets are configured correctly."""

    def test_all_six_roles_present(self):
        for role in EXPECTED_ROLES:
            assert role in INDEED_ROLE_PRESETS, f"Missing preset: {role}"

    def test_preset_required_fields(self):
        required_keys = {
            "title",
            "search_terms",
            "location",
            "required_certifications",
            "role_category",
            "department",
            "shift_schedule",
            "scoring_weights",
        }
        for name, preset in INDEED_ROLE_PRESETS.items():
            missing = required_keys - set(preset.keys())
            assert not missing, f"Preset {name} missing keys: {missing}"

    def test_search_terms_non_empty(self):
        for name, preset in INDEED_ROLE_PRESETS.items():
            assert len(preset["search_terms"]) >= 2, (
                f"Preset {name} should have at least 2 search terms"
            )

    def test_spa_roles_require_license(self):
        assert INDEED_ROLE_PRESETS["massage_therapist"]["required_certifications"] == [
            "massage_therapy"
        ]
        assert INDEED_ROLE_PRESETS["nail_technician"]["required_certifications"] == [
            "nail_technician"
        ]
        assert INDEED_ROLE_PRESETS["esthetician"]["required_certifications"] == [
            "esthetician"
        ]

    def test_spa_manager_no_required_cert(self):
        assert INDEED_ROLE_PRESETS["spa_manager"]["required_certifications"] == []
        assert INDEED_ROLE_PRESETS["spa_manager"]["role_category"] == "management"

    def test_guest_services_no_required_cert(self):
        preset = INDEED_ROLE_PRESETS["guest_services_associate"]
        assert preset["required_certifications"] == []
        assert preset["role_category"] == "guest_services"

    def test_biosecurity_requires_cert(self):
        preset = INDEED_ROLE_PRESETS["biosecurity_specialist"]
        assert "biosecurity" in preset["required_certifications"]

    def test_biosecurity_availability_focused(self):
        weights = INDEED_ROLE_PRESETS["biosecurity_specialist"]["scoring_weights"]
        assert weights["availability"] == 0.35
        assert weights["availability"] > weights["certifications"]

    def test_all_naples_location(self):
        for name in ["massage_therapist", "nail_technician", "esthetician",
                     "spa_manager", "guest_services_associate"]:
            assert "Naples" in INDEED_ROLE_PRESETS[name]["location"]

    def test_scoring_weights_sum_to_one(self):
        for name, preset in INDEED_ROLE_PRESETS.items():
            total = sum(preset["scoring_weights"].values())
            assert abs(total - 1.0) < 0.01, (
                f"Preset {name} weights sum to {total}, expected 1.0"
            )

    def test_role_categories_valid(self):
        valid = {"spa", "management", "biosecurity", "guest_services"}
        for name, preset in INDEED_ROLE_PRESETS.items():
            assert preset["role_category"] in valid, (
                f"Preset {name} has invalid role_category: {preset['role_category']}"
            )


class TestPresetHelpers:
    def test_get_preset(self):
        preset = get_preset("massage_therapist")
        assert preset["title"] == "Massage Therapist"

    def test_get_preset_unknown_raises(self):
        try:
            get_preset("nonexistent")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass

    def test_get_all_presets_returns_copy(self):
        all_presets = get_all_presets()
        assert len(all_presets) == 6
        # Verify it's a new dict
        assert all_presets is not INDEED_ROLE_PRESETS

    def test_get_search_presets_for_scraper(self):
        scraper_presets = get_search_presets_for_scraper()
        for name, preset in scraper_presets.items():
            assert "search_terms" in preset
            assert "department" in preset
            assert "role_category" in preset
            # Should NOT have full preset fields
            assert "scoring_weights" not in preset
            assert "required_certifications" not in preset

    def test_get_job_defaults(self):
        defaults = get_job_defaults("massage_therapist")
        assert defaults["title"] == "Massage Therapist"
        assert defaults["location"] == "Naples, FL"
        assert defaults["role_category"] == "spa"
        assert "massage_therapy" in defaults["required_certifications"]
        assert len(defaults["shift_schedule"]) > 0


class TestPresetsWiredIntoSearchPresets:
    """Verify config presets are available in SEARCH_PRESETS used by scraper."""

    def test_config_presets_in_search_presets(self):
        for role in EXPECTED_ROLES:
            assert role in SEARCH_PRESETS, (
                f"Config preset {role} not wired into SEARCH_PRESETS"
            )

    def test_legacy_presets_still_work(self):
        for legacy in ["spa_therapists", "management", "biosecurity", "guest_services"]:
            assert legacy in SEARCH_PRESETS, (
                f"Legacy preset {legacy} missing from SEARCH_PRESETS"
            )

    def test_preset_import_handler_accepts_new_presets(self):
        """The preset_import handler validates against SEARCH_PRESETS keys."""
        assert "massage_therapist" in SEARCH_PRESETS
        preset = SEARCH_PRESETS["massage_therapist"]
        assert "search_terms" in preset
        assert "department" in preset
