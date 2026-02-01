# Project Context (For Continuing Development)

This file captures the conversation context and decisions made during initial development.

---

## Project Background

**Client:** Andrii Andriushchenko - Dealing Representative at Axcess Capital Advisors Inc.

**Problem:** Andrii conducts KYC calls with clients in Russian/Ukrainian. He then manually fills out lengthy KYC forms (Individual KYC is 7 pages, Corporate is 8 pages, Trade Suitability is 2 pages). This is time-consuming and error-prone.

**Solution:** AI-powered form filling that:
1. Takes call transcripts (from Fireflies.ai or similar)
2. Extracts all KYC-relevant data using Claude
3. Validates against Canadian securities regulations
4. Auto-fills PDF forms
5. Emails draft to Andrii for review

---

## Key Decisions Made

### Tech Stack Choice
- **Chose Python + FastAPI** over n8n or Node.js
- Reason: Better PDF libraries, cleaner data processing, native AI SDK support

### Delivery Method
- **MVP uses email** (not Slack)
- Future: Can add Slack with approval buttons
- Email includes: summary, red flags, draft PDF attached

### Transcript Source
- Designed for **Fireflies.ai / Recall.ai** webhook integration
- Also supports manual POST requests
- Audio transcription (Whisper) not yet implemented - transcript expected as text

### Human-in-the-Loop
- System generates DRAFT PDFs
- Andrii reviews and approves before finalizing
- Never auto-sends to clients

### Sensitive Data
- **SIN is NEVER extracted** - always returns null, flagged for manual collection
- Bank accounts similarly protected

---

## Form Analysis

### Individual KYC (7 pages)
- Section 1: Client Profile (name, address, contact, DOB, occupation)
- Section 2: Investment Knowledge (Good/Average/Limited)
- Section 3: Suitability (Risk Tolerance, Objective, Time Horizon, Risk Capacity)
- Section 4: Financial Assessment (income, assets, net worth)
- Section 5: AML/PEP checks
- Section 6: ID verification
- Section 7: Client signature
- Sections 8-9: Internal compliance use only

### Corporate KYC (8 pages)
- Corporate info + authorized persons
- Shareholders/beneficial owners
- Corporate financials
- Accredited Investor schedules (A & B)

### Trade Suitability (2 pages)
- Per-trade assessment
- Concentration checks (>10% of NFA)
- Suitability notes
- Compliance approval section

---

## Regulatory Context

### Exemption Categories (NI 45-106)

**Accredited Investor** (no investment limits):
- Income ≥ $200k (alone) or $300k (joint) for 2 years
- Net Financial Assets ≥ $1M
- Net Assets ≥ $5M

**Eligible Investor** ($100k rolling limit, non-BC):
- Income ≥ $75k (alone) or $125k (joint)
- Net Assets ≥ $400k

**Non-Eligible** (max $10k per issuer):
- Everyone else

### Red Flag Triggers
- PEP (Politically Exposed Person)
- HIO (Head of International Organization)
- Borrowed funds for investment
- High concentration in single investment
- Age/risk mismatch

---

## Files Created

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI server, webhook endpoint, background processing |
| `app/extractor.py` | Claude API integration, multilingual extraction |
| `app/validator.py` | NI 45-106 compliance checks, exemption determination |
| `app/pdf_filler.py` | PDF form filling using pypdf |
| `app/emailer.py` | Resend email integration, HTML formatting |
| `app/run.py` | Server startup script |
| `app/test_extraction.py` | End-to-end testing with sample transcripts |
| `app/requirements.txt` | Python dependencies |
| `app/.env.example` | Environment variable template |

---

## What's NOT Yet Implemented

1. **Whisper integration** - Audio → Text transcription
2. **Slack notifications** - With approval buttons
3. **Web dashboard** - For review/approval UI
4. **Google Drive** - PDF storage
5. **Airtable/CRM** - Client record keeping
6. **Webhook verification** - Signature checking from Fireflies
7. **Rate limiting** - API protection
8. **Production deployment** - Railway/Render/Fly.io setup

---

## Extraction Prompt (Key Part)

The system prompt in `extractor.py` tells Claude to:
1. Never hallucinate - return null for missing fields
2. Handle Russian/Ukrainian/English
3. Transliterate names to Latin alphabet
4. Map risk tolerance from natural language
5. Determine exemption status from financials
6. Return clean JSON only (no markdown)

---

## Testing Instructions

### Quick Test (No Email)
```bash
cd app
python test_extraction.py
# Choose option 1 (Russian) or 2 (English)
```

This will:
- Extract data from sample transcript
- Run validation
- Try to fill PDF (skips if template not found)
- Save email preview to `output/email_preview.html`

### Full Test (With Email)
1. Set up `.env` with real API keys
2. Run `python run.py`
3. POST to `http://localhost:8000/webhook/transcript`

---

## Common Issues

### PDF Not Filling
- PDF templates must be in project root (parent of `app/`)
- Check that PDFs are fillable forms (not flat PDFs)
- Run `filler.list_form_fields("individual")` to see available fields

### Extraction Returning Errors
- Check Anthropic API key is valid
- Check transcript isn't too long (token limits)
- Claude sometimes returns markdown - the code strips it

### Email Not Sending
- Verify Resend API key
- FROM_EMAIL must be verified domain in Resend
- Check spam folder

---

## Next Session TODO

When continuing development, consider:

1. **Test with real transcript** from Andrii's calls
2. **Refine PDF field mapping** - names may not match exactly
3. **Add Whisper** for audio input
4. **Deploy to Railway/Render** for public webhook URL
5. **Connect Fireflies** webhook to the deployed endpoint

---

## Useful Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python run.py

# Run tests
python test_extraction.py

# List PDF form fields (for debugging)
python -c "from pdf_filler import KYCPDFFiller; print(KYCPDFFiller().list_form_fields('individual'))"

# Test extraction only
python -c "import asyncio; from extractor import KYCExtractor; print(asyncio.run(KYCExtractor().extract('test transcript', 'en', 'individual')))"
```

---

## API Keys Needed

| Service | Purpose | Get From |
|---------|---------|----------|
| Anthropic | Claude extraction | console.anthropic.com |
| Resend | Email sending | resend.com |
| OpenAI (optional) | Whisper transcription | platform.openai.com |
