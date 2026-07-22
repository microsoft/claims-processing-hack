#!/usr/bin/env python3
"""
Claims Processing API Server
FastAPI wrapper for the multi-agent workflow
"""
import os
import json
import logging
import asyncio
import tempfile
import base64
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Import workflow
from workflow_orchestrator import process_claim_workflow

# Load environment
load_dotenv(override=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Claims Processing API",
    description="Multi-agent workflow for processing insurance claim images",
    version="1.0.0"
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ClaimProcessRequest(BaseModel):
    image_base64: str
    filename: Optional[str] = "claim_image.jpg"


class ClaimProcessResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


DEFAULT_CLAIM_FILENAME = "claim_image.jpg"


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check"""
    return {
        "status": "healthy",
        "service": "Claims Processing API",
        "version": "1.0.0"
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Claims Processing API",
        "version": "1.0.0"
    }


@app.post("/process-claim/upload", response_model=ClaimProcessResponse)
async def process_claim_upload(request: Request):
    """
    Process a claim image using file upload (multipart/form-data) or raw binary
    (application/octet-stream). Accepting raw binary removes the need for an APIM
    inbound body-transformation policy, which would otherwise interfere with MCP
    streaming and prevent tool discovery.

    Args:
        request: HTTP request carrying either a multipart/form-data file or a raw
                 binary body.

    Returns:
        Structured claim data
    """
    content_type = request.headers.get("content-type", "")

    try:
        if "multipart/form-data" in content_type:
            # Standard file upload (e.g. curl -F file=@image.jpg)
            form = await request.form()
            file = form.get("file")
            if not file:
                raise HTTPException(status_code=400, detail='No file provided in form field "file"')
            content = await file.read()
            filename = file.filename or DEFAULT_CLAIM_FILENAME
            logger.info(f"📸 Received multipart claim image upload: {filename}")
        else:
            # Raw binary upload (e.g. APIM test console sending application/octet-stream)
            content = await request.body()
            filename = DEFAULT_CLAIM_FILENAME
            logger.info("📸 Received raw binary claim image upload")

        suffix = Path(filename).suffix or ".jpg"

        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        logger.info(f"💾 Saved to temporary file: {tmp_path}")

        # Process with workflow
        result = await process_claim_workflow(tmp_path)

        # Clean up temporary file
        os.unlink(tmp_path)

        # Check for errors
        if "error" in result:
            logger.error(f"❌ Workflow error: {result.get('error')}")
            return ClaimProcessResponse(
                success=False,
                error=result.get("error"),
                data=result
            )

        logger.info("✅ Successfully processed claim")
        return ClaimProcessResponse(
            success=True,
            data=result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing claim: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-claim/base64", response_model=ClaimProcessResponse)
async def process_claim_base64(request: ClaimProcessRequest):
    """
    Process a claim image using base64 encoded data
    
    Args:
        request: JSON with image_base64 and filename
        
    Returns:
        Structured claim data
    """
    logger.info(f"📸 Received base64 claim image: {request.filename}")
    
    try:
        # Decode base64 image
        image_data = base64.b64decode(request.image_base64)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(request.filename).suffix) as tmp_file:
            tmp_file.write(image_data)
            tmp_path = tmp_file.name
        
        logger.info(f"💾 Saved to temporary file: {tmp_path}")
        
        # Process with workflow
        result = await process_claim_workflow(tmp_path)
        
        # Clean up temporary file
        os.unlink(tmp_path)
        
        # Check for errors
        if "error" in result:
            logger.error(f"❌ Workflow error: {result.get('error')}")
            return ClaimProcessResponse(
                success=False,
                error=result.get("error"),
                data=result
            )
        
        logger.info("✅ Successfully processed claim")
        return ClaimProcessResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        logger.error(f"❌ Error processing claim: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Starting Claims Processing API on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
