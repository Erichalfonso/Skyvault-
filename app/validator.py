"""
KYC Validation Layer
Checks extracted data against Canadian securities regulations (NI 45-106)
"""

from typing import Optional
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of KYC validation"""
    is_valid: bool = True
    exemption_status: str = "UNKNOWN"
    red_flags: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    missing_required: list = field(default_factory=list)
    suitability_concerns: list = field(default_factory=list)
    follow_up_needed: bool = False

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "exemption_status": self.exemption_status,
            "red_flags": self.red_flags,
            "warnings": self.warnings,
            "missing_required": self.missing_required,
            "suitability_concerns": self.suitability_concerns,
            "follow_up_needed": self.follow_up_needed
        }


class KYCValidator:
    """Validate extracted KYC data for regulatory compliance"""

    # Required fields for each form type
    REQUIRED_FIELDS = {
        "individual": [
            "client_name.first",
            "client_name.last",
            "address.city",
            "address.province",
            "contact.email",
            "personal.dob",
            "employment.occupation",
            "financials.annual_income",
            "financials.net_financial_assets",
            "investment_profile.risk_tolerance",
            "investment_profile.time_horizon",
            "investment_profile.investment_objective"
        ],
        "corporate": [
            "corporate_name",
            "business_number",
            "authorized_persons",
            "financials.annual_income",
            "financials.net_assets"
        ],
        "trade": [
            "client_name",
            "investment_details.issuer",
            "investment_details.amount",
            "investment_details.source_of_funds"
        ]
    }

    # Accredited investor thresholds (NI 45-106)
    ACCREDITED_INCOME_SINGLE = 200000
    ACCREDITED_INCOME_JOINT = 300000
    ACCREDITED_NFA = 1000000
    ACCREDITED_NET_ASSETS = 5000000

    # Eligible investor thresholds
    ELIGIBLE_INCOME_SINGLE = 75000
    ELIGIBLE_INCOME_JOINT = 125000
    ELIGIBLE_NET_ASSETS = 400000

    def validate(self, data: dict, form_type: str = "individual") -> ValidationResult:
        """
        Validate extracted KYC data.

        Args:
            data: Extracted KYC data dictionary
            form_type: Type of form (individual, corporate, trade)

        Returns:
            ValidationResult with all findings
        """
        result = ValidationResult()

        # Check required fields
        self._check_required_fields(data, form_type, result)

        # Determine exemption status
        self._determine_exemption(data, result)

        # Check suitability
        self._check_suitability(data, result)

        # Check for AML red flags
        self._check_aml_flags(data, result)

        # Check concentration limits
        self._check_concentration(data, result)

        # Determine if follow-up is needed
        result.follow_up_needed = (
            len(result.red_flags) > 0 or
            len(result.missing_required) > 3 or
            len(result.suitability_concerns) > 0
        )

        result.is_valid = len(result.red_flags) == 0 and len(result.missing_required) <= 3

        return result

    def _get_nested(self, data: dict, path: str):
        """Get nested dictionary value by dot path"""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def _check_required_fields(self, data: dict, form_type: str, result: ValidationResult):
        """Check that required fields are present"""
        required = self.REQUIRED_FIELDS.get(form_type, [])

        for field_path in required:
            value = self._get_nested(data, field_path)
            if value is None or value == "":
                result.missing_required.append(field_path)

    def _determine_exemption(self, data: dict, result: ValidationResult):
        """Determine investor exemption status based on financials"""
        financials = data.get("financials", {})

        annual_income = financials.get("annual_income") or 0
        spouse_income = financials.get("spouse_income") or 0
        total_income = annual_income + spouse_income
        nfa = financials.get("net_financial_assets") or 0
        net_worth = financials.get("net_worth") or 0
        income_stable = financials.get("income_stable_2_years", False)

        # Check Accredited Investor status
        is_accredited = False
        accreditation_reason = None

        if annual_income >= self.ACCREDITED_INCOME_SINGLE and income_stable:
            is_accredited = True
            accreditation_reason = f"Annual income ${annual_income:,} >= $200,000 for 2 years"
        elif total_income >= self.ACCREDITED_INCOME_JOINT and income_stable:
            is_accredited = True
            accreditation_reason = f"Joint income ${total_income:,} >= $300,000 for 2 years"
        elif nfa >= self.ACCREDITED_NFA:
            is_accredited = True
            accreditation_reason = f"Net financial assets ${nfa:,} >= $1,000,000"
        elif net_worth >= self.ACCREDITED_NET_ASSETS:
            is_accredited = True
            accreditation_reason = f"Net assets ${net_worth:,} >= $5,000,000"

        # Check Eligible Investor status
        is_eligible = False
        if not is_accredited:
            if annual_income >= self.ELIGIBLE_INCOME_SINGLE:
                is_eligible = True
            elif total_income >= self.ELIGIBLE_INCOME_JOINT:
                is_eligible = True
            elif net_worth >= self.ELIGIBLE_NET_ASSETS:
                is_eligible = True

        # Set exemption status
        if is_accredited:
            result.exemption_status = "ACCREDITED"
        elif is_eligible:
            result.exemption_status = "ELIGIBLE"
            result.warnings.append("Eligible investors have $100k rolling 12-month limit (non-BC)")
        else:
            result.exemption_status = "NON_ELIGIBLE"
            result.warnings.append("Client may only invest up to $10,000 under minimum amount exemption")

        # Store in data for reference
        if "exemption_status" not in data:
            data["exemption_status"] = {}
        data["exemption_status"]["is_accredited"] = is_accredited
        data["exemption_status"]["is_eligible"] = is_eligible
        data["exemption_status"]["accreditation_reason"] = accreditation_reason

    def _check_suitability(self, data: dict, result: ValidationResult):
        """Check investment suitability based on profile"""
        profile = data.get("investment_profile", {})
        financials = data.get("financials", {})
        personal = data.get("personal", {})

        risk_tolerance = profile.get("risk_tolerance")
        risk_capacity = profile.get("risk_capacity")
        time_horizon = profile.get("time_horizon")
        objective = profile.get("investment_objective")

        # Check risk tolerance vs capacity mismatch
        if risk_tolerance == "HIGH" and risk_capacity in ["LOW", "NIL"]:
            result.suitability_concerns.append(
                "Risk tolerance (HIGH) exceeds risk capacity (LOW/NIL) - verify with client"
            )

        # Check time horizon vs retirement
        retirement_year = profile.get("planned_retirement_year")
        if retirement_year:
            import datetime
            years_to_retirement = retirement_year - datetime.datetime.now().year
            if time_horizon == "10+" and years_to_retirement < 5:
                result.suitability_concerns.append(
                    f"Time horizon mismatch: selected 10+ years but retirement in {years_to_retirement} years"
                )

        # Check objective vs risk tolerance alignment
        if objective == "GROWTH" and risk_tolerance == "LOW":
            result.suitability_concerns.append(
                "Growth objective may not align with LOW risk tolerance"
            )

        if objective == "INCOME" and risk_tolerance == "HIGH":
            result.warnings.append(
                "Income objective with HIGH risk tolerance - verify client understands"
            )

        # Check age-based concerns
        dob = personal.get("dob")
        if dob:
            try:
                import datetime
                birth_year = int(dob.split("-")[0])
                age = datetime.datetime.now().year - birth_year
                if age >= 65 and risk_tolerance == "HIGH":
                    result.suitability_concerns.append(
                        f"Client is {age} years old with HIGH risk tolerance - ensure this is appropriate"
                    )
                if age >= 70 and time_horizon == "10+":
                    result.suitability_concerns.append(
                        f"Client is {age} years old with 10+ year time horizon - verify suitability"
                    )
            except (ValueError, IndexError):
                pass

    def _check_aml_flags(self, data: dict, result: ValidationResult):
        """Check for AML/FINTRAC red flags"""
        aml = data.get("aml", {})
        financials = data.get("financials", {})

        # PEP check
        if aml.get("is_pep"):
            result.red_flags.append(
                f"Client is a Politically Exposed Person: {aml.get('pep_position', 'position unknown')}"
            )

        # HIO check
        if aml.get("is_hio"):
            result.red_flags.append("Client is Head of International Organization - enhanced due diligence required")

        # Borrowed funds check
        if financials.get("borrowed_to_invest"):
            result.warnings.append("Client using borrowed funds - leverage disclosure required")

        # Large NFA verification
        nfa = financials.get("net_financial_assets") or 0
        if nfa >= 1000000:
            result.warnings.append(f"NFA of ${nfa:,} requires verification documentation")

    def _check_concentration(self, data: dict, result: ValidationResult):
        """Check investment concentration limits"""
        financials = data.get("financials", {})
        investment = data.get("investment_details", {})

        nfa = financials.get("net_financial_assets") or 0
        investment_amount = investment.get("amount") or 0

        if nfa > 0 and investment_amount > 0:
            concentration_pct = (investment_amount / nfa) * 100

            if concentration_pct > 10:
                result.warnings.append(
                    f"Investment represents {concentration_pct:.1f}% of NFA (>10%) - document suitability justification"
                )

            if concentration_pct > 25:
                result.suitability_concerns.append(
                    f"High concentration: {concentration_pct:.1f}% of NFA in single investment"
                )


# For testing
if __name__ == "__main__":
    validator = KYCValidator()

    test_data = {
        "client_name": {"first": "Ivan", "last": "Petrenko"},
        "address": {"city": "Calgary", "province": "AB"},
        "contact": {"email": "ivan@example.com"},
        "personal": {"dob": "1980-01-15"},
        "employment": {"occupation": "Engineer"},
        "financials": {
            "annual_income": 180000,
            "spouse_income": 80000,
            "net_financial_assets": 500000,
            "net_worth": 1300000,
            "income_stable_2_years": True
        },
        "investment_profile": {
            "risk_tolerance": "MODERATE",
            "time_horizon": "10+",
            "investment_objective": "GROWTH_AND_INCOME"
        },
        "investment_details": {
            "amount": 75000
        },
        "aml": {
            "is_pep": False
        }
    }

    result = validator.validate(test_data, "individual")
    print("Validation Result:")
    print(f"  Valid: {result.is_valid}")
    print(f"  Exemption: {result.exemption_status}")
    print(f"  Red Flags: {result.red_flags}")
    print(f"  Warnings: {result.warnings}")
    print(f"  Missing: {result.missing_required}")
    print(f"  Suitability: {result.suitability_concerns}")
