"""
PDF Form Filler for KYC Documents
Fills Axcess Capital KYC forms with extracted data
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from pypdf import PdfReader, PdfWriter


class KYCPDFFiller:
    """Fill KYC PDF forms with extracted data"""

    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize PDF filler.

        Args:
            templates_dir: Directory containing PDF templates
        """
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            # Default to parent directory where PDFs are stored
            self.templates_dir = Path(__file__).parent.parent

        self.output_dir = Path(__file__).parent / "output"
        self.output_dir.mkdir(exist_ok=True)

        # Template file mapping
        self.templates = {
            "individual": "3. ACA KYC Individual v.5.f - 2025.10.01.pdf",
            "corporate": "4. ACA Corporate KYC v.6.5 - 2025.10.01.pdf",
            "trade": "7. Trade Suitability V.6.pdf"
        }

    def fill(
        self,
        data: dict,
        form_type: str = "individual",
        dealing_rep: str = "Andrii Andriushchenko"
    ) -> str:
        """
        Fill a PDF form with extracted data.

        Args:
            data: Extracted KYC data
            form_type: Type of form (individual, corporate, trade)
            dealing_rep: Name of dealing representative

        Returns:
            Path to the filled PDF file
        """
        template_name = self.templates.get(form_type)
        if not template_name:
            raise ValueError(f"Unknown form type: {form_type}")

        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        # Map data to PDF fields based on form type
        if form_type == "individual":
            field_mapping = self._map_individual_fields(data, dealing_rep)
        elif form_type == "corporate":
            field_mapping = self._map_corporate_fields(data, dealing_rep)
        elif form_type == "trade":
            field_mapping = self._map_trade_fields(data, dealing_rep)
        else:
            field_mapping = {}

        # Fill the PDF
        output_path = self._fill_pdf(template_path, field_mapping, data, form_type)

        return str(output_path)

    def _map_individual_fields(self, data: dict, dealing_rep: str) -> dict:
        """Map extracted data to Individual KYC form fields"""

        client_name = data.get("client_name", {})
        address = data.get("address", {})
        contact = data.get("contact", {})
        personal = data.get("personal", {})
        employment = data.get("employment", {})
        spouse_emp = data.get("spouse_employment", {})
        financials = data.get("financials", {})
        profile = data.get("investment_profile", {})
        exemption = data.get("exemption_status", {})

        # Build full name
        full_name = " ".join(filter(None, [
            client_name.get("last", ""),
            client_name.get("first", ""),
            client_name.get("middle", "")
        ]))

        # Build full address
        full_address = ", ".join(filter(None, [
            address.get("street", ""),
            address.get("unit", ""),
        ]))

        return {
            # Header
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Dealing Representative": dealing_rep,

            # Section 1 - Client Profile
            "Full Name": full_name,
            "Last": client_name.get("last", ""),
            "First": client_name.get("first", ""),
            "Middle": client_name.get("middle", ""),
            "Street Address cannot be a PO Box": address.get("street", ""),
            "ApartmentUnit": address.get("unit", ""),
            "City": address.get("city", ""),
            "Prov": address.get("province", ""),
            "Postal Code": address.get("postal_code", ""),
            "Phone day": contact.get("phone", ""),
            "Cell": contact.get("cell", ""),
            "Email": contact.get("email", ""),
            "Date of Birth": personal.get("dob", ""),
            "SIN": "",  # Never auto-fill SIN
            "Dependents": str(personal.get("dependents", "")),
            "Primary Occupation": employment.get("occupation", ""),
            "Employer": employment.get("employer", ""),

            # Section 2 - Investment Knowledge (checkboxes)
            "Good": profile.get("knowledge_level") == "GOOD",
            "Average": profile.get("knowledge_level") == "AVERAGE",
            "Limited": profile.get("knowledge_level") == "LIMITED",

            # Section 3 - Suitability
            "LOW": profile.get("risk_tolerance") == "LOW",
            "MODERATE": profile.get("risk_tolerance") == "MODERATE",
            "HIGH": profile.get("risk_tolerance") == "HIGH",

            "Growth": profile.get("investment_objective") == "GROWTH",
            "Growth  Income": profile.get("investment_objective") == "GROWTH_AND_INCOME",
            "Income": profile.get("investment_objective") == "INCOME",
            "Tax Efficiency": profile.get("investment_objective") == "TAX_EFFICIENCY",

            "13 years": profile.get("time_horizon") == "1-3",
            "35 years": profile.get("time_horizon") == "3-5",
            "610 years": profile.get("time_horizon") == "6-10",
            "10 years": profile.get("time_horizon") == "10+",

            # Section 4 - Financial
            "Employment Annual Income": str(financials.get("annual_income", "")),
            "SpousePartner Annual Income": str(financials.get("spouse_income", "")),
            "Other Income": str(financials.get("other_income", "")),
            "Total Income": str(financials.get("total_income", "")),

            "Estimated Net Financial Assets": str(financials.get("net_financial_assets", "")),
            "Estimated NonFinancial Assets": str(financials.get("non_financial_assets", "")),
            "Estimated Total Assets": str(financials.get("total_assets", "")),
            "Estimated Liabilities": str(financials.get("liabilities", "")),
            "Estimated Net Worth": str(financials.get("net_worth", "")),

            # Asset composition (percentages)
            "Cash  Deposits": str(data.get("asset_composition", {}).get("cash_pct", "")),
            "Public Equities  Stocks": str(data.get("asset_composition", {}).get("stocks_pct", "")),
            "Fixed Income  Bonds": str(data.get("asset_composition", {}).get("bonds_pct", "")),

            # Section 5 - AML/PEP
            "PEP Yes": data.get("aml", {}).get("is_pep", False),
            "PEP No": not data.get("aml", {}).get("is_pep", True),
            "HIO Yes": data.get("aml", {}).get("is_hio", False),
            "HIO No": not data.get("aml", {}).get("is_hio", True),
        }

    def _map_corporate_fields(self, data: dict, dealing_rep: str) -> dict:
        """Map extracted data to Corporate KYC form fields"""

        corp_info = data.get("corporate_info", {})
        address = corp_info.get("legal_address", {}) or data.get("address", {})
        financials = data.get("financials", {})
        auth_persons = data.get("authorized_persons", [{}])

        return {
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Dealing Representative": dealing_rep,

            # Section 1 - Corporate Information
            "Name": corp_info.get("legal_name", ""),
            "Legal Address": address.get("street", ""),
            "City": address.get("city", ""),
            "Prov": address.get("province", ""),
            "Postal Code": address.get("postal_code", ""),
            "CRA Business Number": corp_info.get("cra_business_number", ""),
            "Industry and Business Type": corp_info.get("industry_type", ""),
            "Province of IncorpReg": corp_info.get("province_of_incorporation", ""),
            "Date of IncorpReg": corp_info.get("date_of_incorporation", ""),

            # Section 2 - Authorized Person 1
            "Person 1": auth_persons[0].get("full_name", "") if auth_persons else "",

            # Section 5 - Corporate Financial Summary
            "Estimated annual income from all sources": str(financials.get("annual_income", "")),
            "Net Assets of corporation": str(financials.get("net_assets", "")),
        }

    def _map_trade_fields(self, data: dict, dealing_rep: str) -> dict:
        """Map extracted data to Trade Suitability form fields"""

        client_name = data.get("client_name", {})
        investment = data.get("investment_details", {})
        financials = data.get("financials", {})

        full_name = f"{client_name.get('first', '')} {client_name.get('last', '')}".strip()

        return {
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Dealing Representative": dealing_rep,
            "Client": full_name,

            # Source of funds checkboxes
            "Nonregd": investment.get("source_of_funds") == "NON_REGISTERED",
            "RRSP": investment.get("source_of_funds") == "RRSP",
            "TFSA": investment.get("source_of_funds") == "TFSA",
            "Borrowed": investment.get("source_of_funds") == "BORROWED",
            "Other": investment.get("source_of_funds") == "OTHER",

            # Investment details
            "Issuer 1": investment.get("issuer", ""),
            "Amount 1": str(investment.get("amount", "")),
        }

    def _fill_pdf(
        self,
        template_path: Path,
        field_mapping: dict,
        data: dict,
        form_type: str
    ) -> Path:
        """
        Fill a PDF with the provided field mapping.

        Args:
            template_path: Path to template PDF
            field_mapping: Dictionary mapping PDF field names to values
            data: Original extracted data (for filename)
            form_type: Type of form

        Returns:
            Path to filled PDF
        """
        # Read the template
        reader = PdfReader(str(template_path))
        writer = PdfWriter()

        # Copy pages and fill fields
        for page in reader.pages:
            writer.add_page(page)

        # Get existing form fields
        if reader.get_fields():
            # Update fields with our values
            writer.update_page_form_field_values(
                writer.pages[0],
                field_mapping,
                auto_regenerate=False
            )

        # Generate output filename
        client_name = data.get("client_name", {})
        name_part = f"{client_name.get('first', 'Unknown')}_{client_name.get('last', 'Client')}"
        name_part = name_part.replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        output_filename = f"{form_type.upper()}_KYC_{name_part}_{timestamp}.pdf"
        output_path = self.output_dir / output_filename

        # Write the filled PDF
        with open(output_path, "wb") as output_file:
            writer.write(output_file)

        return output_path

    def list_form_fields(self, form_type: str) -> list:
        """
        List all fillable fields in a PDF template.
        Useful for debugging field mapping.

        Args:
            form_type: Type of form

        Returns:
            List of field names
        """
        template_name = self.templates.get(form_type)
        if not template_name:
            return []

        template_path = self.templates_dir / template_name
        if not template_path.exists():
            return []

        reader = PdfReader(str(template_path))
        fields = reader.get_fields()

        if fields:
            return list(fields.keys())
        return []


# For testing
if __name__ == "__main__":
    filler = KYCPDFFiller()

    # List available fields in each form
    print("Individual KYC Fields:")
    for field in filler.list_form_fields("individual")[:20]:
        print(f"  - {field}")

    print("\nTrade Suitability Fields:")
    for field in filler.list_form_fields("trade")[:20]:
        print(f"  - {field}")

    # Test fill
    test_data = {
        "client_name": {"first": "Ivan", "last": "Petrenko"},
        "address": {
            "street": "123 Main Street",
            "city": "Calgary",
            "province": "AB",
            "postal_code": "T2P 1J9"
        },
        "contact": {
            "email": "ivan@example.com",
            "phone": "403-555-1234"
        },
        "personal": {"dob": "1980-01-15"},
        "employment": {"occupation": "Engineer", "employer": "Tech Corp"},
        "financials": {
            "annual_income": 180000,
            "net_financial_assets": 500000,
            "net_worth": 1300000
        },
        "investment_profile": {
            "risk_tolerance": "MODERATE",
            "time_horizon": "10+",
            "investment_objective": "GROWTH_AND_INCOME",
            "knowledge_level": "GOOD"
        },
        "aml": {"is_pep": False, "is_hio": False}
    }

    try:
        output = filler.fill(test_data, "individual")
        print(f"\nFilled PDF saved to: {output}")
    except FileNotFoundError as e:
        print(f"\nNote: {e}")
        print("Copy the PDF templates to the project root directory")
