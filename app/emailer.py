"""
Email Notification Module
Sends KYC extraction results via Resend
"""

import os
import base64
from pathlib import Path
from typing import Optional
import resend
from dotenv import load_dotenv

load_dotenv()

# Initialize Resend
resend.api_key = os.getenv("RESEND_API_KEY")

NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "andrii@example.com")
FROM_EMAIL = os.getenv("FROM_EMAIL", "kyc@yourdomain.com")


async def send_kyc_email(
    extracted_data: dict,
    validation_result: dict,
    pdf_path: Optional[str] = None,
    form_type: str = "individual"
) -> bool:
    """
    Send KYC extraction results via email.

    Args:
        extracted_data: The extracted KYC data
        validation_result: Validation results including flags and warnings
        pdf_path: Path to the filled PDF (optional)
        form_type: Type of form processed

    Returns:
        True if email sent successfully
    """

    # Build client name
    client_name = extracted_data.get("client_name", {})
    full_name = f"{client_name.get('first', 'Unknown')} {client_name.get('last', 'Client')}"

    # Build email subject
    has_flags = len(validation_result.get("red_flags", [])) > 0
    flag_indicator = "⚠️ " if has_flags else "✅ "
    subject = f"{flag_indicator}KYC Extraction Complete: {full_name}"

    # Build HTML body
    html_body = _build_email_html(extracted_data, validation_result, form_type)

    # Prepare attachments
    attachments = []
    if pdf_path and Path(pdf_path).exists():
        with open(pdf_path, "rb") as f:
            pdf_content = base64.b64encode(f.read()).decode()
        attachments.append({
            "filename": Path(pdf_path).name,
            "content": pdf_content,
            "type": "application/pdf"
        })

    # Send email
    try:
        params = {
            "from": FROM_EMAIL,
            "to": [NOTIFICATION_EMAIL],
            "subject": subject,
            "html": html_body,
        }

        if attachments:
            params["attachments"] = attachments

        response = resend.Emails.send(params)
        return True

    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def _build_email_html(data: dict, validation: dict, form_type: str) -> str:
    """Build the HTML email body"""

    client_name = data.get("client_name", {})
    full_name = f"{client_name.get('first', '')} {client_name.get('last', '')}".strip() or "Unknown"

    address = data.get("address", {})
    contact = data.get("contact", {})
    personal = data.get("personal", {})
    employment = data.get("employment", {})
    financials = data.get("financials", {})
    profile = data.get("investment_profile", {})
    exemption = data.get("exemption_status", {})

    # Format currency values
    def fmt_currency(val):
        if val is None:
            return "N/A"
        try:
            return f"${int(val):,}"
        except (ValueError, TypeError):
            return str(val)

    # Build red flags section
    red_flags = validation.get("red_flags", [])
    red_flags_html = ""
    if red_flags:
        flags_list = "".join(f"<li style='color: #dc3545;'>{flag}</li>" for flag in red_flags)
        red_flags_html = f"""
        <div style="background: #fff5f5; border-left: 4px solid #dc3545; padding: 15px; margin: 20px 0;">
            <h3 style="color: #dc3545; margin-top: 0;">⚠️ Red Flags - Action Required</h3>
            <ul>{flags_list}</ul>
        </div>
        """

    # Build warnings section
    warnings = validation.get("warnings", [])
    warnings_html = ""
    if warnings:
        warnings_list = "".join(f"<li>{w}</li>" for w in warnings)
        warnings_html = f"""
        <div style="background: #fff8e6; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
            <h3 style="color: #856404; margin-top: 0;">⚡ Warnings</h3>
            <ul>{warnings_list}</ul>
        </div>
        """

    # Build suitability concerns section
    suitability = validation.get("suitability_concerns", [])
    suitability_html = ""
    if suitability:
        suit_list = "".join(f"<li>{s}</li>" for s in suitability)
        suitability_html = f"""
        <div style="background: #e7f3ff; border-left: 4px solid #0066cc; padding: 15px; margin: 20px 0;">
            <h3 style="color: #0066cc; margin-top: 0;">📋 Suitability Concerns</h3>
            <ul>{suit_list}</ul>
        </div>
        """

    # Build missing fields section
    missing = validation.get("missing_required", [])
    missing_html = ""
    if missing:
        missing_html = f"""
        <div style="background: #f8f9fa; border-left: 4px solid #6c757d; padding: 15px; margin: 20px 0;">
            <h3 style="color: #6c757d; margin-top: 0;">❓ Missing Fields</h3>
            <p>The following required fields were not found in the transcript:</p>
            <p><code>{", ".join(missing)}</code></p>
        </div>
        """

    # Build follow-up questions section
    follow_ups = data.get("follow_up_questions", [])
    follow_up_html = ""
    if follow_ups:
        fu_list = "".join(f"<li>{q}</li>" for q in follow_ups)
        follow_up_html = f"""
        <div style="background: #f0f7ff; border-left: 4px solid #17a2b8; padding: 15px; margin: 20px 0;">
            <h3 style="color: #17a2b8; margin-top: 0;">💬 Suggested Follow-up Questions</h3>
            <ul>{fu_list}</ul>
        </div>
        """

    # Exemption badge
    exemption_status = validation.get("exemption_status", "UNKNOWN")
    exemption_colors = {
        "ACCREDITED": ("#28a745", "white"),
        "ELIGIBLE": ("#17a2b8", "white"),
        "NON_ELIGIBLE": ("#6c757d", "white"),
        "UNKNOWN": ("#ffc107", "black")
    }
    ex_bg, ex_fg = exemption_colors.get(exemption_status, ("#6c757d", "white"))

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #34495e; margin-top: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; font-weight: 600; width: 40%; }}
            .badge {{
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 14px;
            }}
            .header-section {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="header-section">
            <h1>KYC Extraction Results</h1>
            <span class="badge" style="background: {ex_bg}; color: {ex_fg};">
                {exemption_status}
            </span>
        </div>

        <p><strong>Form Type:</strong> {form_type.upper()} KYC</p>
        <p><strong>Confidence:</strong> Name: {data.get('confidence_scores', {}).get('client_name', 'N/A')} |
            Financials: {data.get('confidence_scores', {}).get('financials', 'N/A')} |
            Risk Profile: {data.get('confidence_scores', {}).get('risk_profile', 'N/A')}</p>

        {red_flags_html}
        {warnings_html}
        {suitability_html}
        {missing_html}

        <h2>👤 Client Information</h2>
        <table>
            <tr><th>Full Name</th><td>{full_name}</td></tr>
            <tr><th>Address</th><td>{address.get('street', 'N/A')}, {address.get('city', 'N/A')}, {address.get('province', 'N/A')} {address.get('postal_code', '')}</td></tr>
            <tr><th>Phone</th><td>{contact.get('phone', 'N/A')} / {contact.get('cell', 'N/A')}</td></tr>
            <tr><th>Email</th><td>{contact.get('email', 'N/A')}</td></tr>
            <tr><th>Date of Birth</th><td>{personal.get('dob', 'N/A')}</td></tr>
            <tr><th>Occupation</th><td>{employment.get('occupation', 'N/A')}</td></tr>
            <tr><th>Employer</th><td>{employment.get('employer', 'N/A')}</td></tr>
        </table>

        <h2>💰 Financial Profile</h2>
        <table>
            <tr><th>Annual Income</th><td>{fmt_currency(financials.get('annual_income'))}</td></tr>
            <tr><th>Spouse Income</th><td>{fmt_currency(financials.get('spouse_income'))}</td></tr>
            <tr><th>Total Income</th><td>{fmt_currency(financials.get('total_income'))}</td></tr>
            <tr><th>Net Financial Assets</th><td>{fmt_currency(financials.get('net_financial_assets'))}</td></tr>
            <tr><th>Non-Financial Assets</th><td>{fmt_currency(financials.get('non_financial_assets'))}</td></tr>
            <tr><th>Total Assets</th><td>{fmt_currency(financials.get('total_assets'))}</td></tr>
            <tr><th>Liabilities</th><td>{fmt_currency(financials.get('liabilities'))}</td></tr>
            <tr><th>Net Worth</th><td><strong>{fmt_currency(financials.get('net_worth'))}</strong></td></tr>
        </table>

        <h2>📊 Investment Profile</h2>
        <table>
            <tr><th>Knowledge Level</th><td>{profile.get('knowledge_level', 'N/A')}</td></tr>
            <tr><th>Risk Tolerance</th><td>{profile.get('risk_tolerance', 'N/A')}</td></tr>
            <tr><th>Risk Capacity</th><td>{profile.get('risk_capacity', 'N/A')}</td></tr>
            <tr><th>Time Horizon</th><td>{profile.get('time_horizon', 'N/A')} years</td></tr>
            <tr><th>Investment Objective</th><td>{profile.get('investment_objective', 'N/A')}</td></tr>
        </table>

        <h2>🏦 Exemption Status</h2>
        <table>
            <tr><th>Status</th><td><strong>{exemption_status}</strong></td></tr>
            <tr><th>Is Accredited</th><td>{'Yes' if exemption.get('is_accredited') else 'No'}</td></tr>
            <tr><th>Is Eligible</th><td>{'Yes' if exemption.get('is_eligible') else 'No'}</td></tr>
            <tr><th>Reason</th><td>{exemption.get('accreditation_reason', 'N/A')}</td></tr>
        </table>

        {follow_up_html}

        <hr style="margin-top: 40px;">
        <p style="color: #6c757d; font-size: 12px;">
            This extraction was generated automatically by Skyvault KYC.
            Please review all data before finalizing the KYC form.
            The attached PDF is a draft and may require manual adjustments.
        </p>
    </body>
    </html>
    """

    return html


# For testing without Resend
def send_kyc_email_test(
    extracted_data: dict,
    validation_result: dict,
    pdf_path: Optional[str] = None,
    form_type: str = "individual"
) -> str:
    """
    Test version that returns HTML instead of sending.
    """
    html = _build_email_html(extracted_data, validation_result, form_type)

    # Save to file for preview
    output_path = Path(__file__).parent / "output" / "email_preview.html"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return str(output_path)


# For testing
if __name__ == "__main__":
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
            "phone": "403-555-1234",
            "cell": "403-555-5678"
        },
        "personal": {"dob": "1980-01-15"},
        "employment": {"occupation": "Software Engineer", "employer": "Tech Corp Inc."},
        "financials": {
            "annual_income": 180000,
            "spouse_income": 80000,
            "total_income": 260000,
            "net_financial_assets": 500000,
            "non_financial_assets": 800000,
            "total_assets": 1300000,
            "liabilities": 200000,
            "net_worth": 1100000
        },
        "investment_profile": {
            "knowledge_level": "GOOD",
            "risk_tolerance": "MODERATE",
            "risk_capacity": "MEDIUM",
            "time_horizon": "10+",
            "investment_objective": "GROWTH_AND_INCOME"
        },
        "exemption_status": {
            "is_accredited": True,
            "is_eligible": True,
            "accreditation_reason": "Joint income $260,000 >= $300,000 for 2 years"
        },
        "confidence_scores": {
            "client_name": "HIGH",
            "financials": "MEDIUM",
            "risk_profile": "HIGH"
        },
        "follow_up_questions": [
            "Can you confirm your SIN for the form?",
            "What is your spouse's occupation?",
            "Do you have any existing exempt market investments?"
        ]
    }

    test_validation = {
        "is_valid": True,
        "exemption_status": "ACCREDITED",
        "red_flags": [],
        "warnings": ["NFA of $500,000 requires verification documentation"],
        "missing_required": ["contact.cell"],
        "suitability_concerns": []
    }

    output = send_kyc_email_test(test_data, test_validation, form_type="individual")
    print(f"Email preview saved to: {output}")
