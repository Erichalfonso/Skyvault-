"""
Pytest configuration and shared fixtures for Project Skyvault tests.
"""

import sys
from pathlib import Path

import pytest

# Add app directory to path for imports
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))


# --- Sample Data Fixtures ---

@pytest.fixture
def sample_individual_data():
    """Complete individual KYC extracted data for testing."""
    return {
        "client_type": "individual",
        "personal_info": {
            "first_name": "Ivan",
            "last_name": "Petrov",
            "date_of_birth": "1985-03-15",
            "citizenship": "Canada",
            "sin": None,
            "email": "ivan.petrov@email.com",
            "phone": "+1-416-555-0123",
            "address": {
                "street": "123 Main Street",
                "city": "Toronto",
                "province": "Ontario",
                "postal_code": "M5V 1A1",
                "country": "Canada"
            }
        },
        "employment": {
            "status": "employed",
            "employer": "Tech Corp Inc",
            "occupation": "Software Engineer",
            "years_employed": 5
        },
        "financial_info": {
            "annual_income": 150000,
            "joint_income": None,
            "net_financial_assets": 500000,
            "net_assets": 800000,
            "liquid_assets": 300000,
            "fixed_assets": 500000,
            "liabilities": 200000
        },
        "investment_profile": {
            "knowledge": "good",
            "experience_years": 10,
            "risk_tolerance": "medium",
            "investment_objective": "growth",
            "time_horizon": "medium",
            "risk_capacity": "medium"
        },
        "compliance": {
            "is_pep": False,
            "is_hio": False,
            "is_insider": False,
            "borrowed_funds": False,
            "third_party_account": False
        },
        "id_verification": {
            "id_type": "passport",
            "id_number": "AB123456",
            "id_expiry": "2028-05-20",
            "issuing_jurisdiction": "Canada"
        }
    }


@pytest.fixture
def sample_accredited_investor_data(sample_individual_data):
    """Individual data that qualifies as Accredited Investor."""
    data = sample_individual_data.copy()
    data["financial_info"] = {
        "annual_income": 250000,
        "joint_income": None,
        "net_financial_assets": 1500000,
        "net_assets": 6000000,
        "liquid_assets": 1000000,
        "fixed_assets": 5000000,
        "liabilities": 500000
    }
    return data


@pytest.fixture
def sample_eligible_investor_data(sample_individual_data):
    """Individual data that qualifies as Eligible Investor."""
    data = sample_individual_data.copy()
    data["financial_info"] = {
        "annual_income": 100000,
        "joint_income": None,
        "net_financial_assets": 600000,
        "net_assets": 500000,
        "liquid_assets": 400000,
        "fixed_assets": 100000,
        "liabilities": 50000
    }
    return data


@pytest.fixture
def sample_non_eligible_data(sample_individual_data):
    """Individual data that does NOT qualify for exemptions."""
    data = sample_individual_data.copy()
    data["financial_info"] = {
        "annual_income": 50000,
        "joint_income": None,
        "net_financial_assets": 50000,
        "net_assets": 100000,
        "liquid_assets": 30000,
        "fixed_assets": 70000,
        "liabilities": 20000
    }
    return data


@pytest.fixture
def sample_pep_data(sample_individual_data):
    """Individual data flagged as PEP."""
    data = sample_individual_data.copy()
    data["compliance"] = {
        "is_pep": True,
        "is_hio": False,
        "is_insider": False,
        "borrowed_funds": False,
        "third_party_account": False
    }
    return data


@pytest.fixture
def sample_corporate_data():
    """Complete corporate KYC extracted data for testing."""
    return {
        "client_type": "corporate",
        "corporate_info": {
            "legal_name": "Maple Holdings Inc.",
            "operating_name": "Maple Tech",
            "incorporation_number": "BC1234567",
            "incorporation_date": "2015-06-01",
            "jurisdiction": "British Columbia",
            "business_type": "Technology Services",
            "address": {
                "street": "500 West Georgia Street",
                "city": "Vancouver",
                "province": "British Columbia",
                "postal_code": "V6B 1Z5",
                "country": "Canada"
            }
        },
        "authorized_persons": [
            {
                "name": "John Smith",
                "title": "CEO",
                "email": "john@mapleholdings.com",
                "phone": "+1-604-555-0100"
            }
        ],
        "beneficial_owners": [
            {
                "name": "John Smith",
                "ownership_percentage": 60,
                "is_pep": False
            },
            {
                "name": "Jane Doe",
                "ownership_percentage": 40,
                "is_pep": False
            }
        ],
        "financial_info": {
            "annual_revenue": 5000000,
            "net_assets": 10000000,
            "total_assets": 15000000
        },
        "compliance": {
            "is_reporting_issuer": False,
            "is_registered_entity": False
        }
    }


@pytest.fixture
def sample_transcript_russian():
    """Sample Russian KYC call transcript."""
    return """
    Консультант: Добрый день! Давайте начнем с базовой информации. Как вас зовут?
    Клиент: Меня зовут Иван Петров.
    Консультант: Дата рождения?
    Клиент: 15 марта 1985 года.
    Консультант: Какой у вас годовой доход?
    Клиент: Около 150 тысяч долларов в год.
    Консультант: А сколько у вас финансовых активов?
    Клиент: Примерно полмиллиона.
    """


@pytest.fixture
def sample_transcript_english():
    """Sample English KYC call transcript."""
    return """
    Advisor: Good afternoon! Let's start with basic information. What is your name?
    Client: My name is Ivan Petrov.
    Advisor: Date of birth?
    Client: March 15, 1985.
    Advisor: What is your annual income?
    Client: About 150 thousand dollars per year.
    Advisor: And how much do you have in financial assets?
    Client: Approximately half a million.
    """


# --- Mock Fixtures ---

@pytest.fixture
def mock_anthropic_response():
    """Mock successful Claude API response."""
    return {
        "client_type": "individual",
        "personal_info": {
            "first_name": "Ivan",
            "last_name": "Petrov",
            "date_of_birth": "1985-03-15"
        },
        "financial_info": {
            "annual_income": 150000,
            "net_financial_assets": 500000
        }
    }
