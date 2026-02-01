"""
Run the Skyvault KYC API server
"""

import uvicorn

if __name__ == "__main__":
    print("Starting Skyvault KYC API...")
    print("API docs available at: http://localhost:8000/docs")
    print("Webhook endpoint: POST http://localhost:8000/webhook/transcript")
    print("\nPress Ctrl+C to stop\n")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes
    )
