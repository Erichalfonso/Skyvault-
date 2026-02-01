"""
Unit tests for KYC Validator module.

Tests cover:
- Exemption status determination (Accredited, Eligible, Non-Eligible)
- Required field validation
- AML/PEP red flag detection
- Suitability checks
- Concentration limits
"""

import pytest
from validator import KYCValidator, ValidationResult


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    @pytest.mark.unit
    def test_default_values(self):
        """Test default initialization values."""
        result = ValidationResult()
        assert result.is_valid is True
        assert result.exemption_status == "UNKNOWN"
        assert result.red_flags == []
        assert result.warnings == []
        assert result.missing_required == []
        assert result.suitability_concerns == []
        assert result.follow_up_needed is False

    @pytest.mark.unit
    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = ValidationResult(
            is_valid=False,
            exemption_status="ACCREDITED",
            red_flags=["PEP detected"],
            warnings=["High NFA"],
            missing_required=["email"],
            suitability_concerns=["Age mismatch"],
            follow_up_needed=True
        )
        d = result.to_dict()

        assert d["is_valid"] is False
        assert d["exemption_status"] == "ACCREDITED"
        assert d["red_flags"] == ["PEP detected"]
        assert d["warnings"] == ["High NFA"]
        assert d["missing_required"] == ["email"]
        assert d["suitability_concerns"] == ["Age mismatch"]
        assert d["follow_up_needed"] is True


class TestGetNested:
    """Tests for _get_nested helper method."""

    @pytest.fixture
    def validator(self):
        return KYCValidator()

    @pytest.mark.unit
    def test_single_level(self, validator):
        """Test single level key access."""
        data = {"name": "John"}
        assert validator._get_nested(data, "name") == "John"

    @pytest.mark.unit
    def test_nested_two_levels(self, validator):
        """Test two level nested access."""
        data = {"client_name": {"first": "John", "last": "Doe"}}
        assert validator._get_nested(data, "client_name.first") == "John"
        assert validator._get_nested(data, "client_name.last") == "Doe"

    @pytest.mark.unit
    def test_nested_three_levels(self, validator):
        """Test three level nested access."""
        data = {"a": {"b": {"c": "deep_value"}}}
        assert validator._get_nested(data, "a.b.c") == "deep_value"

    @pytest.mark.unit
    def test_missing_key_returns_none(self, validator):
        """Test that missing keys return None."""
        data = {"name": "John"}
        assert validator._get_nested(data, "email") is None

    @pytest.mark.unit
    def test_missing_nested_key_returns_none(self, validator):
        """Test that missing nested keys return None."""
        data = {"client_name": {"first": "John"}}
        assert validator._get_nested(data, "client_name.middle") is None
        assert validator._get_nested(data, "address.city") is None

    @pytest.mark.unit
    def test_empty_dict(self, validator):
        """Test access on empty dictionary."""
        assert validator._get_nested({}, "any.key") is None


class TestExemptionDetermination:
    """Tests for investor exemption status determination."""

    @pytest.fixture
    def validator(self):
        return KYCValidator()

    @pytest.mark.unit
    def test_accredited_by_single_income(self, validator):
        """Test accreditation via single income >= $200k."""
        data = {
            "financials": {
                "annual_income": 200000,
                "income_stable_2_years": True
            }
        }
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "ACCREDITED"
        assert data["exemption_status"]["is_accredited"] is True

    @pytest.mark.unit
    def test_accredited_by_joint_income(self, validator):
        """Test accreditation via joint income >= $300k."""
        data = {
            "financials": {
                "annual_income": 180000,
                "spouse_income": 150000,
                "income_stable_2_years": True
            }
        }
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "ACCREDITED"
        assert data["exemption_status"]["is_accredited"] is True
        assert "Joint income" in data["exemption_status"]["accreditation_reason"]

    @pytest.mark.unit
    def test_accredited_by_nfa(self, validator):
        """Test accreditation via net financial assets >= $1M."""
        data = {
            "financials": {
                "annual_income": 50000,
                "net_financial_assets": 1000000
            }
        }
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "ACCREDITED"
        assert "Net financial assets" in data["exemption_status"]["accreditation_reason"]

    @pytest.mark.unit
    def test_accredited_by_net_worth(self, validator):
        """Test accreditation via net assets >= $5M."""
        data = {
            "financials": {
                "annual_income": 50000,
                "net_worth": 5000000
            }
        }
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "ACCREDITED"
        assert "Net assets" in data["exemption_status"]["accreditation_reason"]

    @pytest.mark.unit
    def test_not_accredited_without_stable_income(self, validator):
        """Test high income without stable history does not qualify."""
        data = {
            "financials": {
                "annual_income": 250000,
                "income_stable_2_years": False
            }
        }
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status != "ACCREDITED"

    @pytest.mark.unit
    def test_eligible_by_single_income(self, validator):
        """Test eligible investor via single income >= $75k."""
        data = {
            "financials": {
                "annual_income": 75000
            }
        }
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "ELIGIBLE"
        assert any("$100k rolling" in w for w in result.warnings)

    @pytest.mark.unit
    def test_eligible_by_joint_income(self, validator):
        """Test eligible investor via joint income >= $125k."""
        data = {
            "financials": {
                "annual_income": 50000,
                "spouse_income": 75000
            }
        }
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "ELIGIBLE"

    @pytest.mark.unit
    def test_eligible_by_net_worth(self, validator):
        """Test eligible investor via net assets >= $400k."""
        data = {
            "financials": {
                "annual_income": 50000,
                "net_worth": 400000
            }
        }
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "ELIGIBLE"

    @pytest.mark.unit
    def test_non_eligible(self, validator):
        """Test non-eligible investor (below all thresholds)."""
        data = {
            "financials": {
                "annual_income": 50000,
                "net_financial_assets": 50000,
                "net_worth": 100000
            }
        }
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "NON_ELIGIBLE"
        assert any("$10,000" in w for w in result.warnings)

    @pytest.mark.unit
    def test_accredited_takes_priority_over_eligible(self, validator):
        """Test that accredited status takes priority over eligible."""
        data = {
            "financials": {
                "annual_income": 100000,
                "net_financial_assets": 1500000
            }
        }
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "ACCREDITED"

    @pytest.mark.unit
    def test_empty_financials(self, validator):
        """Test handling of empty financials."""
        data = {"financials": {}}
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "NON_ELIGIBLE"

    @pytest.mark.unit
    def test_missing_financials(self, validator):
        """Test handling of missing financials key."""
        data = {}
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "NON_ELIGIBLE"


class TestAMLFlags:
    """Tests for AML/FINTRAC red flag detection."""

    @pytest.fixture
    def validator(self):
        return KYCValidator()

    @pytest.mark.unit
    def test_pep_detection(self, validator):
        """Test PEP (Politically Exposed Person) detection."""
        data = {
            "aml": {
                "is_pep": True,
                "pep_position": "Member of Parliament"
            }
        }
        result = ValidationResult()
        validator._check_aml_flags(data, result)

        assert len(result.red_flags) == 1
        assert "Politically Exposed Person" in result.red_flags[0]
        assert "Member of Parliament" in result.red_flags[0]

    @pytest.mark.unit
    def test_pep_without_position(self, validator):
        """Test PEP detection without position specified."""
        data = {"aml": {"is_pep": True}}
        result = ValidationResult()
        validator._check_aml_flags(data, result)

        assert len(result.red_flags) == 1
        assert "position unknown" in result.red_flags[0]

    @pytest.mark.unit
    def test_hio_detection(self, validator):
        """Test HIO (Head of International Organization) detection."""
        data = {"aml": {"is_hio": True}}
        result = ValidationResult()
        validator._check_aml_flags(data, result)

        assert len(result.red_flags) == 1
        assert "Head of International Organization" in result.red_flags[0]

    @pytest.mark.unit
    def test_borrowed_funds_warning(self, validator):
        """Test borrowed funds warning."""
        data = {"financials": {"borrowed_to_invest": True}}
        result = ValidationResult()
        validator._check_aml_flags(data, result)

        assert len(result.warnings) == 1
        assert "borrowed funds" in result.warnings[0]

    @pytest.mark.unit
    def test_high_nfa_verification(self, validator):
        """Test high NFA verification warning."""
        data = {"financials": {"net_financial_assets": 2000000}}
        result = ValidationResult()
        validator._check_aml_flags(data, result)

        assert any("requires verification" in w for w in result.warnings)

    @pytest.mark.unit
    def test_no_flags_for_clean_client(self, validator):
        """Test no flags for clean client."""
        data = {
            "aml": {"is_pep": False, "is_hio": False},
            "financials": {"borrowed_to_invest": False, "net_financial_assets": 500000}
        }
        result = ValidationResult()
        validator._check_aml_flags(data, result)

        assert len(result.red_flags) == 0


class TestConcentration:
    """Tests for investment concentration limit checks."""

    @pytest.fixture
    def validator(self):
        return KYCValidator()

    @pytest.mark.unit
    def test_concentration_over_10_percent(self, validator):
        """Test warning for concentration > 10% of NFA."""
        data = {
            "financials": {"net_financial_assets": 100000},
            "investment_details": {"amount": 15000}
        }
        result = ValidationResult()
        validator._check_concentration(data, result)

        assert any("15.0% of NFA" in w for w in result.warnings)

    @pytest.mark.unit
    def test_concentration_over_25_percent(self, validator):
        """Test concern for concentration > 25% of NFA."""
        data = {
            "financials": {"net_financial_assets": 100000},
            "investment_details": {"amount": 30000}
        }
        result = ValidationResult()
        validator._check_concentration(data, result)

        assert any("30.0% of NFA" in c for c in result.suitability_concerns)

    @pytest.mark.unit
    def test_concentration_under_10_percent(self, validator):
        """Test no warning for concentration < 10%."""
        data = {
            "financials": {"net_financial_assets": 1000000},
            "investment_details": {"amount": 50000}
        }
        result = ValidationResult()
        validator._check_concentration(data, result)

        assert len(result.warnings) == 0
        assert len(result.suitability_concerns) == 0

    @pytest.mark.unit
    def test_zero_nfa_no_error(self, validator):
        """Test that zero NFA doesn't cause division error."""
        data = {
            "financials": {"net_financial_assets": 0},
            "investment_details": {"amount": 10000}
        }
        result = ValidationResult()
        validator._check_concentration(data, result)

        assert len(result.warnings) == 0

    @pytest.mark.unit
    def test_missing_investment_amount(self, validator):
        """Test handling of missing investment amount."""
        data = {
            "financials": {"net_financial_assets": 100000},
            "investment_details": {}
        }
        result = ValidationResult()
        validator._check_concentration(data, result)

        assert len(result.warnings) == 0


class TestSuitability:
    """Tests for investment suitability checks."""

    @pytest.fixture
    def validator(self):
        return KYCValidator()

    @pytest.mark.unit
    def test_risk_tolerance_capacity_mismatch(self, validator):
        """Test detection of risk tolerance vs capacity mismatch."""
        data = {
            "investment_profile": {
                "risk_tolerance": "HIGH",
                "risk_capacity": "LOW"
            }
        }
        result = ValidationResult()
        validator._check_suitability(data, result)

        assert any("Risk tolerance (HIGH) exceeds risk capacity" in c for c in result.suitability_concerns)

    @pytest.mark.unit
    def test_growth_objective_low_risk(self, validator):
        """Test concern for growth objective with low risk tolerance."""
        data = {
            "investment_profile": {
                "investment_objective": "GROWTH",
                "risk_tolerance": "LOW"
            }
        }
        result = ValidationResult()
        validator._check_suitability(data, result)

        assert any("Growth objective may not align" in c for c in result.suitability_concerns)

    @pytest.mark.unit
    def test_income_objective_high_risk(self, validator):
        """Test warning for income objective with high risk tolerance."""
        data = {
            "investment_profile": {
                "investment_objective": "INCOME",
                "risk_tolerance": "HIGH"
            }
        }
        result = ValidationResult()
        validator._check_suitability(data, result)

        assert any("Income objective with HIGH risk tolerance" in w for w in result.warnings)

    @pytest.mark.unit
    def test_elderly_high_risk(self, validator):
        """Test concern for elderly client with high risk tolerance."""
        data = {
            "personal": {"dob": "1955-01-15"},
            "investment_profile": {"risk_tolerance": "HIGH"}
        }
        result = ValidationResult()
        validator._check_suitability(data, result)

        # Client would be ~71 years old
        assert any("years old with HIGH risk tolerance" in c for c in result.suitability_concerns)

    @pytest.mark.unit
    def test_elderly_long_time_horizon(self, validator):
        """Test concern for elderly client with 10+ year horizon."""
        data = {
            "personal": {"dob": "1950-01-15"},
            "investment_profile": {"time_horizon": "10+"}
        }
        result = ValidationResult()
        validator._check_suitability(data, result)

        assert any("10+ year time horizon" in c for c in result.suitability_concerns)

    @pytest.mark.unit
    def test_young_client_no_age_concerns(self, validator):
        """Test no age concerns for young client with high risk."""
        data = {
            "personal": {"dob": "1990-01-15"},
            "investment_profile": {
                "risk_tolerance": "HIGH",
                "time_horizon": "10+"
            }
        }
        result = ValidationResult()
        validator._check_suitability(data, result)

        assert not any("years old" in c for c in result.suitability_concerns)

    @pytest.mark.unit
    def test_invalid_dob_format(self, validator):
        """Test handling of invalid DOB format."""
        data = {
            "personal": {"dob": "invalid-date"},
            "investment_profile": {"risk_tolerance": "HIGH"}
        }
        result = ValidationResult()
        # Should not raise exception
        validator._check_suitability(data, result)


class TestRequiredFields:
    """Tests for required field validation."""

    @pytest.fixture
    def validator(self):
        return KYCValidator()

    @pytest.mark.unit
    def test_all_required_fields_present(self, validator):
        """Test validation passes when all required fields present."""
        data = {
            "client_name": {"first": "John", "last": "Doe"},
            "address": {"city": "Toronto", "province": "ON"},
            "contact": {"email": "john@example.com"},
            "personal": {"dob": "1980-01-15"},
            "employment": {"occupation": "Engineer"},
            "financials": {
                "annual_income": 100000,
                "net_financial_assets": 500000
            },
            "investment_profile": {
                "risk_tolerance": "MODERATE",
                "time_horizon": "5-10",
                "investment_objective": "GROWTH"
            }
        }
        result = ValidationResult()
        validator._check_required_fields(data, "individual", result)

        assert len(result.missing_required) == 0

    @pytest.mark.unit
    def test_missing_required_fields(self, validator):
        """Test detection of missing required fields."""
        data = {
            "client_name": {"first": "John"},  # missing last
            "contact": {}  # missing email
        }
        result = ValidationResult()
        validator._check_required_fields(data, "individual", result)

        assert "client_name.last" in result.missing_required
        assert "contact.email" in result.missing_required

    @pytest.mark.unit
    def test_empty_string_treated_as_missing(self, validator):
        """Test that empty strings are treated as missing."""
        data = {
            "client_name": {"first": "John", "last": ""},
            "address": {"city": "", "province": "ON"}
        }
        result = ValidationResult()
        validator._check_required_fields(data, "individual", result)

        assert "client_name.last" in result.missing_required
        assert "address.city" in result.missing_required

    @pytest.mark.unit
    def test_corporate_required_fields(self, validator):
        """Test corporate form required fields."""
        data = {}
        result = ValidationResult()
        validator._check_required_fields(data, "corporate", result)

        assert "corporate_name" in result.missing_required
        assert "business_number" in result.missing_required

    @pytest.mark.unit
    def test_trade_required_fields(self, validator):
        """Test trade form required fields."""
        data = {}
        result = ValidationResult()
        validator._check_required_fields(data, "trade", result)

        assert "client_name" in result.missing_required
        assert "investment_details.issuer" in result.missing_required


class TestFullValidation:
    """Integration tests for full validate() method."""

    @pytest.fixture
    def validator(self):
        return KYCValidator()

    @pytest.mark.unit
    def test_valid_accredited_investor(self, validator):
        """Test validation of a valid accredited investor."""
        data = {
            "client_name": {"first": "John", "last": "Doe"},
            "address": {"city": "Toronto", "province": "ON"},
            "contact": {"email": "john@example.com"},
            "personal": {"dob": "1980-01-15"},
            "employment": {"occupation": "Executive"},
            "financials": {
                "annual_income": 250000,
                "income_stable_2_years": True,
                "net_financial_assets": 1500000,
                "net_worth": 3000000
            },
            "investment_profile": {
                "risk_tolerance": "MODERATE",
                "time_horizon": "5-10",
                "investment_objective": "GROWTH"
            },
            "aml": {"is_pep": False}
        }
        result = validator.validate(data, "individual")

        assert result.is_valid is True
        assert result.exemption_status == "ACCREDITED"
        assert result.follow_up_needed is False

    @pytest.mark.unit
    def test_invalid_due_to_pep(self, validator):
        """Test that PEP status makes result invalid."""
        data = {
            "client_name": {"first": "John", "last": "Doe"},
            "address": {"city": "Toronto", "province": "ON"},
            "contact": {"email": "john@example.com"},
            "personal": {"dob": "1980-01-15"},
            "employment": {"occupation": "Politician"},
            "financials": {
                "annual_income": 250000,
                "income_stable_2_years": True,
                "net_financial_assets": 1500000
            },
            "investment_profile": {
                "risk_tolerance": "MODERATE",
                "time_horizon": "5-10",
                "investment_objective": "GROWTH"
            },
            "aml": {"is_pep": True, "pep_position": "Senator"}
        }
        result = validator.validate(data, "individual")

        assert result.is_valid is False
        assert len(result.red_flags) > 0
        assert result.follow_up_needed is True

    @pytest.mark.unit
    def test_invalid_due_to_many_missing_fields(self, validator):
        """Test that too many missing fields makes result invalid."""
        data = {
            "client_name": {"first": "John"},  # missing last
            # missing most required fields
        }
        result = validator.validate(data, "individual")

        assert result.is_valid is False
        assert len(result.missing_required) > 3

    @pytest.mark.unit
    def test_follow_up_needed_for_suitability_concerns(self, validator):
        """Test follow-up needed when suitability concerns exist."""
        data = {
            "client_name": {"first": "John", "last": "Doe"},
            "address": {"city": "Toronto", "province": "ON"},
            "contact": {"email": "john@example.com"},
            "personal": {"dob": "1950-01-15"},
            "employment": {"occupation": "Retired"},
            "financials": {
                "annual_income": 50000,
                "net_financial_assets": 500000
            },
            "investment_profile": {
                "risk_tolerance": "HIGH",
                "time_horizon": "10+",
                "investment_objective": "GROWTH"
            },
            "aml": {"is_pep": False}
        }
        result = validator.validate(data, "individual")

        assert result.follow_up_needed is True
        assert len(result.suitability_concerns) > 0


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def validator(self):
        return KYCValidator()

    @pytest.mark.unit
    def test_exactly_accredited_income_threshold(self, validator):
        """Test exact accredited income threshold."""
        data = {
            "financials": {
                "annual_income": 200000,
                "income_stable_2_years": True
            }
        }
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "ACCREDITED"

    @pytest.mark.unit
    def test_just_below_accredited_income(self, validator):
        """Test just below accredited income threshold."""
        data = {
            "financials": {
                "annual_income": 199999,
                "income_stable_2_years": True
            }
        }
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "ELIGIBLE"  # Falls to eligible

    @pytest.mark.unit
    def test_exactly_nfa_threshold(self, validator):
        """Test exact NFA threshold."""
        data = {
            "financials": {"net_financial_assets": 1000000}
        }
        result = ValidationResult()
        validator._determine_exemption(data, result)

        assert result.exemption_status == "ACCREDITED"

    @pytest.mark.unit
    def test_none_values_in_financials(self, validator):
        """Test handling of None values in financials."""
        data = {
            "financials": {
                "annual_income": None,
                "spouse_income": None,
                "net_financial_assets": None,
                "net_worth": None
            }
        }
        result = ValidationResult()
        # Should not raise exception
        validator._determine_exemption(data, result)

        assert result.exemption_status == "NON_ELIGIBLE"

    @pytest.mark.unit
    def test_unknown_form_type(self, validator):
        """Test handling of unknown form type."""
        data = {}
        result = ValidationResult()
        # Should not raise exception
        validator._check_required_fields(data, "unknown_type", result)

        # No required fields for unknown type
        assert len(result.missing_required) == 0
