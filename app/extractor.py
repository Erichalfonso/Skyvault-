"""
KYC Data Extractor using Claude API
Handles multilingual transcripts (Russian, Ukrainian, English)
"""

import json
import os
from typing import Optional
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

# System prompt for KYC extraction
EXTRACTION_PROMPT = """You are a KYC Data Extraction Agent for Axcess Capital Advisors Inc., a Canadian Exempt Market Dealer. Extract client information from call transcripts and return structured JSON.

## CRITICAL RULES

1. **NEVER HALLUCINATE** - If information is not explicitly stated, return null for that field.

2. **SENSITIVE DATA**:
   - SIN (Social Insurance Number): ALWAYS return null - flag for manual collection
   - Bank account numbers: ALWAYS return null

3. **MULTILINGUAL HANDLING**:
   - Transcript may be in Russian, Ukrainian, or English (or mixed)
   - Translate all values to English
   - Transliterate names to Latin alphabet (Cyrillic → English)
   - Common financial terms:
     - доход/дохід = income
     - чистая стоимость/чиста вартість = net worth
     - риск/ризик = risk
     - накопления/заощадження = savings
     - пенсия/пенсія = pension/retirement
     - недвижимость/нерухомість = real estate

4. **EXEMPTION DETERMINATION** (Canadian NI 45-106):
   - Accredited: Income >$200k (alone) or >$300k (with spouse) for 2 years, OR NFA >$1M, OR Net Assets >$5M
   - Eligible: Income >$75k (alone) or >$125k (with spouse), OR Net Assets >$400k
   - Set is_accredited/is_eligible based on stated financials

5. **RISK TOLERANCE MAPPING**:
   - LOW: "can't lose money", "safety first", "need access to funds"
   - MODERATE: "some risk ok", "long-term", "don't need money soon"
   - HIGH: "maximize returns", "willing to lose", "aggressive growth"

6. **TIME HORIZON**:
   - "1-3 years" or "short-term"
   - "3-5 years" or "medium-term"
   - "6-10 years"
   - "10+ years" or "retirement in X years" (calculate)

## OUTPUT FORMAT

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:

{
  "client_name": {
    "first": "string or null",
    "middle": "string or null",
    "last": "string or null"
  },
  "spouse_name": {
    "first": "string or null",
    "last": "string or null"
  },
  "address": {
    "street": "string or null",
    "unit": "string or null",
    "city": "string or null",
    "province": "string or null",
    "postal_code": "string or null"
  },
  "contact": {
    "phone": "string or null",
    "cell": "string or null",
    "email": "string or null"
  },
  "personal": {
    "dob": "YYYY-MM-DD or null",
    "citizenship": "string or null",
    "dependents": "number or null",
    "marital_status": "string or null"
  },
  "employment": {
    "occupation": "string or null",
    "employer": "string or null",
    "years_employed": "number or null",
    "is_self_employed": "boolean or null"
  },
  "spouse_employment": {
    "occupation": "string or null",
    "employer": "string or null"
  },
  "financials": {
    "annual_income": "number or null",
    "spouse_income": "number or null",
    "other_income": "number or null",
    "total_income": "number or null",
    "net_financial_assets": "number or null",
    "non_financial_assets": "number or null",
    "total_assets": "number or null",
    "liabilities": "number or null",
    "net_worth": "number or null",
    "income_stable_2_years": "boolean or null",
    "borrowed_to_invest": "boolean or null"
  },
  "asset_composition": {
    "cash_pct": "number or null",
    "stocks_pct": "number or null",
    "bonds_pct": "number or null",
    "real_estate_pct": "number or null",
    "other_pct": "number or null"
  },
  "investment_profile": {
    "knowledge_level": "GOOD | AVERAGE | LIMITED | null",
    "risk_tolerance": "LOW | MODERATE | HIGH | null",
    "risk_capacity": "HIGH | MEDIUM | LOW | NIL | null",
    "time_horizon": "1-3 | 3-5 | 6-10 | 10+ | null",
    "investment_objective": "GROWTH | GROWTH_AND_INCOME | INCOME | TAX_EFFICIENCY | null",
    "planned_retirement_year": "number or null",
    "products_owned": ["list of: STOCKS, BONDS, MUTUAL_FUNDS, ETFS, CRYPTO, REAL_ESTATE, MICS, LIMITED_PARTNERSHIPS, EXEMPT_SECURITIES"]
  },
  "exemption_status": {
    "is_accredited": "boolean or null",
    "is_eligible": "boolean or null",
    "accreditation_reason": "string or null"
  },
  "aml": {
    "is_pep": "boolean or null",
    "pep_position": "string or null",
    "is_hio": "boolean or null"
  },
  "investment_details": {
    "issuer": "string or null",
    "amount": "number or null",
    "source_of_funds": "NON_REGISTERED | RRSP | TFSA | BORROWED | OTHER | null"
  },
  "confidence_scores": {
    "client_name": "HIGH | MEDIUM | LOW",
    "financials": "HIGH | MEDIUM | LOW",
    "risk_profile": "HIGH | MEDIUM | LOW"
  },
  "missing_fields": ["list of field names not found in transcript"],
  "ambiguous_items": ["list of items that need clarification"],
  "follow_up_questions": ["suggested questions to ask client"]
}
"""


class KYCExtractor:
    """Extract KYC data from transcripts using Claude"""

    def __init__(self):
        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-20250514"

    async def extract(
        self,
        transcript: str,
        source_language: str = "auto",
        form_type: str = "individual"
    ) -> dict:
        """
        Full extraction from transcript.

        Args:
            transcript: The call transcript text
            source_language: Language hint (auto, ru, uk, en)
            form_type: Type of form to fill (individual, corporate, trade)

        Returns:
            Extracted KYC data as dictionary
        """

        # Build the user message
        user_message = f"""Extract KYC data from this transcript.

Source language hint: {source_language}
Form type: {form_type}

TRANSCRIPT:
{transcript}

Remember: Return ONLY valid JSON, no markdown formatting."""

        # Call Claude
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=EXTRACTION_PROMPT,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        # Parse response
        response_text = response.content[0].text.strip()

        # Clean up potential markdown formatting
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        try:
            extracted = json.loads(response_text)
        except json.JSONDecodeError as e:
            # Try to salvage partial JSON
            extracted = {
                "error": "Failed to parse extraction",
                "raw_response": response_text[:500],
                "parse_error": str(e)
            }

        return extracted

    async def quick_extract(self, transcript: str) -> dict:
        """
        Quick extraction for immediate webhook response.
        Only extracts name and basic info.
        """

        quick_prompt = """Extract ONLY the client's name from this transcript.
Return JSON with: {"first_name": "...", "last_name": "...", "missing_fields": [...]}
If name not found, use null. Transliterate from Russian/Ukrainian to English if needed.
Return ONLY valid JSON."""

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=200,
            messages=[
                {"role": "user", "content": f"{quick_prompt}\n\nTRANSCRIPT:\n{transcript[:1000]}"}
            ]
        )

        response_text = response.content[0].text.strip()

        # Clean markdown if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            return {"first_name": None, "last_name": None, "missing_fields": ["name"]}


# For testing
if __name__ == "__main__":
    import asyncio

    test_transcript = """
    Добрый день! Меня зовут Иван Петренко. Мне 45 лет, я живу в Калгари
    на улице 123 Main Street, почтовый код T2P 1J9. Мой годовой доход
    примерно 180 тысяч долларов, у жены доход около 80 тысяч.
    У нас есть сбережения около 500 тысяч в банке и дом стоимостью
    примерно 800 тысяч. Я хочу инвестировать на долгий срок,
    может быть 10 лет до пенсии. Готов к умеренному риску.
    """

    async def test():
        extractor = KYCExtractor()
        result = await extractor.extract(test_transcript, "ru", "individual")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(test())
