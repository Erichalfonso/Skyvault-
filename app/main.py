"""
Skyvault KYC Extraction API
Main FastAPI application
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import logging

from .extractor import KYCExtractor
from .validator import KYCValidator
from .pdf_filler import KYCPDFFiller
from .emailer import send_kyc_email

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Skyvault KYC Extraction API",
    description="Multilingual AI-powered KYC form filling for Axcess Capital",
    version="1.0.0"
)


class TranscriptRequest(BaseModel):
    """Incoming transcript payload"""
    transcript: str
    source_language: Optional[str] = "auto"  # auto, ru, uk, en
    client_id: Optional[str] = None
    dealing_rep: Optional[str] = "Andrii Andriushchenko"
    call_date: Optional[str] = None
    form_type: Optional[str] = "individual"  # individual, corporate, trade


class ExtractionResponse(BaseModel):
    """Response after extraction"""
    status: str
    client_name: Optional[str]
    form_type: str
    fields_extracted: int
    missing_fields: list
    red_flags: list
    message: str


# Initialize components
extractor = KYCExtractor()
validator = KYCValidator()
pdf_filler = KYCPDFFiller()


async def process_kyc_background(
    transcript: str,
    source_language: str,
    form_type: str,
    dealing_rep: str,
    client_id: Optional[str]
):
    """Background task to process KYC extraction"""
    try:
        # Step 1: Extract data from transcript
        logger.info(f"Extracting KYC data for client_id: {client_id}")
        extracted_data = await extractor.extract(
            transcript=transcript,
            source_language=source_language,
            form_type=form_type
        )

        # Step 2: Validate extracted data
        logger.info("Validating extracted data")
        validation_result = validator.validate(extracted_data, form_type)

        # Step 3: Generate filled PDF
        logger.info("Generating PDF")
        pdf_path = pdf_filler.fill(
            data=extracted_data,
            form_type=form_type,
            dealing_rep=dealing_rep
        )

        # Step 4: Send email notification
        logger.info("Sending email notification")
        await send_kyc_email(
            extracted_data=extracted_data,
            validation_result=validation_result,
            pdf_path=pdf_path,
            form_type=form_type
        )

        logger.info(f"KYC processing complete for {extracted_data.get('client_name', 'Unknown')}")

    except Exception as e:
        logger.error(f"Error processing KYC: {str(e)}")
        # TODO: Send error notification


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Skyvault KYC API"}


@app.post("/webhook/transcript", response_model=ExtractionResponse)
async def receive_transcript(
    request: TranscriptRequest,
    background_tasks: BackgroundTasks
):
    """
    Receive a transcript from Fireflies/Recall.ai and process KYC extraction.
    Processing happens in background, returns immediately.
    """

    if not request.transcript or len(request.transcript.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Transcript too short or empty"
        )

    # Quick extraction for immediate response
    try:
        quick_extract = await extractor.quick_extract(request.transcript)
        client_name = f"{quick_extract.get('first_name', '')} {quick_extract.get('last_name', '')}".strip()
    except Exception:
        client_name = "Unknown"
        quick_extract = {}

    # Queue full processing in background
    background_tasks.add_task(
        process_kyc_background,
        transcript=request.transcript,
        source_language=request.source_language,
        form_type=request.form_type,
        dealing_rep=request.dealing_rep,
        client_id=request.client_id
    )

    return ExtractionResponse(
        status="processing",
        client_name=client_name or None,
        form_type=request.form_type,
        fields_extracted=len([v for v in quick_extract.values() if v]),
        missing_fields=quick_extract.get("missing_fields", []),
        red_flags=[],
        message="KYC extraction started. You will receive an email when complete."
    )


@app.post("/extract/sync")
async def extract_sync(request: TranscriptRequest):
    """
    Synchronous extraction - waits for full result.
    Use for testing or when immediate response is needed.
    """

    # Step 1: Extract
    extracted_data = await extractor.extract(
        transcript=request.transcript,
        source_language=request.source_language,
        form_type=request.form_type
    )

    # Step 2: Validate
    validation_result = validator.validate(extracted_data, request.form_type)

    return {
        "status": "success",
        "extracted_data": extracted_data,
        "validation": validation_result
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
