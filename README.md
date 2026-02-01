# Project Skyvault

Multilingual AI-powered KYC form filling system for Axcess Capital Advisors Inc. (Canadian Exempt Market Dealer).

## Overview

This system extracts client information from multilingual call transcripts (Russian, Ukrainian, English) and populates Canadian exempt market dealer KYC forms with human-in-the-loop verification via email.

### The Problem
Andrii conducts client calls in Russian/Ukrainian. He then manually fills out 60+ page KYC forms. This is time-consuming and error-prone.

### The Solution
1. Client call transcript comes in (from Fireflies.ai, Recall.ai, or manual upload)
2. Claude extracts all KYC-relevant data into structured JSON
3. Validation layer checks Canadian securities regulations (NI 45-106)
4. PDF forms are auto-filled
5. Email sent to Andrii with summary + draft PDF for review

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Transcript     │────▶│  Claude 3.5     │────▶│  Validation     │
│  (Webhook)      │     │  Extraction     │     │  Layer          │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Email to      │◀────│   PDF           │◀────│  Field          │
│   Andrii        │     │   Generation    │     │  Mapping        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Project Structure

```
Project Skyvault/
├── PDF Templates
│   ├── 3. ACA KYC Individual v.5.f - 2025.10.01.pdf    # 7 pages
│   ├── 4. ACA Corporate KYC v.6.5 - 2025.10.01.pdf     # 8 pages
│   └── 7. Trade Suitability V.6.pdf                     # 2 pages
│
├── app/
│   ├── main.py           # FastAPI server + webhook endpoint
│   ├── extractor.py      # Claude-powered data extraction
│   ├── validator.py      # NI 45-106 compliance checks
│   ├── pdf_filler.py     # PDF form filling
│   ├── emailer.py        # Email notifications via Resend
│   ├── run.py            # Start the server
│   ├── test_extraction.py # Test the pipeline
│   ├── requirements.txt  # Python dependencies
│   ├── .env.example      # Environment template
│   └── output/           # Generated PDFs and email previews
│
├── .gitignore
└── README.md
```

---

## Setup Instructions

### 1. Install Python Dependencies

```bash
cd "C:\Users\erich\Downloads\Project Skyvault\app"
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
copy .env.example .env
```

Edit `.env` with your API keys:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-xxxxx          # From console.anthropic.com
RESEND_API_KEY=re_xxxxx                  # From resend.com
NOTIFICATION_EMAIL=andrii@example.com    # Where to send results
FROM_EMAIL=kyc@yourdomain.com            # Sender email (must be verified in Resend)

# Optional
WEBHOOK_SECRET=your-secret-here          # For webhook verification
```

### 3. Start the Server

```bash
python run.py
```

Server runs at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Webhook endpoint: `POST http://localhost:8000/webhook/transcript`

### 4. Test the Pipeline

```bash
python test_extraction.py
```

Select option 1 (Russian) or 2 (English) to test full pipeline.

---

## API Endpoints

### POST /webhook/transcript

Receive a transcript and process KYC extraction (async).

**Request:**
```json
{
  "transcript": "Добрый день! Меня зовут Иван Петренко...",
  "source_language": "ru",
  "form_type": "individual",
  "dealing_rep": "Andrii Andriushchenko",
  "client_id": "CLT-2025-001"
}
```

**Response:**
```json
{
  "status": "processing",
  "client_name": "Ivan Petrenko",
  "form_type": "individual",
  "fields_extracted": 12,
  "missing_fields": ["sin", "employer"],
  "red_flags": [],
  "message": "KYC extraction started. You will receive an email when complete."
}
```

### POST /extract/sync

Synchronous extraction - waits for full result (for testing).

---

## KYC Data Schema

The extractor outputs this JSON structure:

```json
{
  "client_name": {
    "first": "string",
    "middle": "string or null",
    "last": "string"
  },
  "spouse_name": {
    "first": "string or null",
    "last": "string or null"
  },
  "address": {
    "street": "string",
    "unit": "string or null",
    "city": "string",
    "province": "string",
    "postal_code": "string"
  },
  "contact": {
    "phone": "string",
    "cell": "string",
    "email": "string"
  },
  "personal": {
    "dob": "YYYY-MM-DD",
    "citizenship": "string",
    "dependents": "number",
    "marital_status": "string"
  },
  "employment": {
    "occupation": "string",
    "employer": "string",
    "years_employed": "number",
    "is_self_employed": "boolean"
  },
  "financials": {
    "annual_income": "number",
    "spouse_income": "number",
    "other_income": "number",
    "total_income": "number",
    "net_financial_assets": "number",
    "non_financial_assets": "number",
    "total_assets": "number",
    "liabilities": "number",
    "net_worth": "number",
    "income_stable_2_years": "boolean",
    "borrowed_to_invest": "boolean"
  },
  "investment_profile": {
    "knowledge_level": "GOOD | AVERAGE | LIMITED",
    "risk_tolerance": "LOW | MODERATE | HIGH",
    "risk_capacity": "HIGH | MEDIUM | LOW | NIL",
    "time_horizon": "1-3 | 3-5 | 6-10 | 10+",
    "investment_objective": "GROWTH | GROWTH_AND_INCOME | INCOME | TAX_EFFICIENCY",
    "products_owned": ["STOCKS", "MUTUAL_FUNDS", "CRYPTO", ...]
  },
  "exemption_status": {
    "is_accredited": "boolean",
    "is_eligible": "boolean",
    "accreditation_reason": "string"
  },
  "aml": {
    "is_pep": "boolean",
    "pep_position": "string or null",
    "is_hio": "boolean"
  },
  "confidence_scores": {
    "client_name": "HIGH | MEDIUM | LOW",
    "financials": "HIGH | MEDIUM | LOW",
    "risk_profile": "HIGH | MEDIUM | LOW"
  },
  "missing_fields": ["list of fields not found"],
  "follow_up_questions": ["suggested questions to ask client"]
}
```

---

## Validation Rules (NI 45-106)

### Exemption Thresholds

**Accredited Investor:**
- Net income ≥ $200,000 (alone) for 2 consecutive years, OR
- Net income ≥ $300,000 (with spouse) for 2 consecutive years, OR
- Net financial assets ≥ $1,000,000, OR
- Net assets ≥ $5,000,000

**Eligible Investor:**
- Net income ≥ $75,000 (alone), OR
- Net income ≥ $125,000 (with spouse), OR
- Net assets ≥ $400,000
- Note: $100k rolling 12-month limit for non-BC residents

**Non-Eligible:**
- May only invest up to $10,000 under minimum amount exemption

### Red Flags (Automatic Detection)
- PEP (Politically Exposed Person) status
- HIO (Head of International Organization) status
- High concentration (>10% of NFA in single investment)
- Risk tolerance vs risk capacity mismatch
- Age vs risk profile concerns

---

## Multilingual Support

The system handles Russian, Ukrainian, and English transcripts.

### Key Financial Term Translations

| Russian | Ukrainian | English |
|---------|-----------|---------|
| доход | дохід | income |
| чистая стоимость | чиста вартість | net worth |
| риск | ризик | risk |
| накопления | заощадження | savings |
| пенсия | пенсія | pension/retirement |
| недвижимость | нерухомість | real estate |
| ипотека | іпотека | mortgage |
| акции | акції | stocks |

### Name Transliteration
Names are automatically transliterated from Cyrillic to Latin alphabet:
- Иван Петренко → Ivan Petrenko
- Олександр Шевченко → Oleksandr Shevchenko

---

## PDF Form Field Mapping

The PDF filler maps extracted data to form fields. Field names may vary by PDF version.

To discover field names in a PDF:
```python
from pdf_filler import KYCPDFFiller
filler = KYCPDFFiller()
fields = filler.list_form_fields("individual")
print(fields)
```

---

## Connecting to Transcript Sources

### Fireflies.ai
1. Go to Settings → Integrations → Webhooks
2. Add URL: `https://your-server.com/webhook/transcript`
3. Configure to send transcript on meeting end

### Recall.ai
1. Configure Recall bot to join Zoom/Meet calls
2. Set webhook endpoint for transcript delivery
3. Transform Recall's format in the webhook handler if needed

### Manual Upload
Send POST request with transcript text to the webhook endpoint.

---

## Email Output

Andrii receives an email with:
- Client name and exemption status badge
- Red flags (if any) - highlighted in red
- Warnings - highlighted in yellow
- Missing fields that need follow-up
- Full extracted data summary
- Suggested follow-up questions
- Draft PDF attached

---

## Development Notes

### Testing Without API Keys
- Use `test_extraction.py` option 1 or 2 with your Anthropic key
- Email preview saves to `app/output/email_preview.html` (no Resend key needed)

### Adding New Form Types
1. Add PDF template to project root
2. Update `KYCPDFFiller.templates` dict in `pdf_filler.py`
3. Add field mapping method `_map_{form_type}_fields()`
4. Update validator if form has unique requirements

### Debugging Extraction
- Check `extracted_data` in the sync endpoint response
- Review `confidence_scores` to see extraction quality
- Check `missing_fields` and `ambiguous_items` for issues

---

## Security Considerations

- **SIN**: Never auto-extracted from transcripts (always null)
- **Bank accounts**: Never auto-extracted
- **API keys**: Store in `.env`, never commit
- **Transcripts**: Consider data residency (host in Canada for PIPEDA)

---

## Next Steps / TODO

- [ ] Add Whisper integration for audio file transcription
- [ ] Add Slack notifications with approval buttons
- [ ] Create web dashboard for review/approval
- [ ] Add Google Drive integration for PDF storage
- [ ] Add Airtable/CRM integration for client records
- [ ] Implement webhook signature verification
- [ ] Add rate limiting
- [ ] Add logging to file/service

---

## Sample Test Transcript (Russian)

```
Добрый день! Меня зовут Иван Сергеевич Петренко.

Да, я живу в Калгари, Альберта. Мой адрес: 123 Main Street Northwest,
квартира 456, почтовый код T2P 1J9.

Мой телефон 403-555-1234, а мобильный 403-555-5678.
Электронная почта ivan.petrenko@gmail.com

Мне 44 года, я родился 15 января 1980 года. Я женат, у нас двое детей.

Я работаю программистом в компании Tech Solutions уже 8 лет.
Моя жена Анна работает бухгалтером в небольшой фирме.

Мой годовой доход примерно 180 тысяч долларов до налогов.
Жена зарабатывает около 75 тысяч в год.
Доход стабильный последние несколько лет.

У нас есть сбережения около 400 тысяч в банке и инвестициях.
Также есть дом, который стоит примерно 850 тысяч.
Ипотека осталась около 200 тысяч.

Я хочу инвестировать на долгий срок - планирую выйти на пенсию лет через 15-20.
Готов к умеренному риску. Не хочу слишком рисковать, но понимаю что нужен рост.
Моя цель - рост капитала с небольшим доходом.

У меня есть опыт инвестирования - владею акциями и ETF фондами.

Нет, я не политик и не работаю в международных организациях.
```

---

## Contact

For Axcess Capital form questions: compliance@axcesscapital.com
