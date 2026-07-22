#!/usr/bin/env python3
"""
Claims Intake Agent - Enterprise Edition

Combines OCR + JSON Structuring into a single autonomous intake workflow.
Handles multi-image claims, confidence scoring, and auto-remediation.

Key Enterprise Features:
- Automatic retry on low confidence
- Structured error reporting
- Audit trail for compliance
- Processing metrics
- Confidence-based quality gates
"""

import os
import sys
import json
import logging
import time
import base64
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

from enterprise_models import (
    ClaimProcessingState, OCRResult, StructuredClaim, ErrorInfo, 
    SeverityLevel, ClaimStatus
)

load_dotenv(override=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ENDPOINT = os.environ.get("AI_FOUNDRY_PROJECT_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-5.4")

# Confidence thresholds
MIN_OCR_CONFIDENCE = 0.75
MIN_EXTRACTION_CONFIDENCE = 0.80
MAX_RETRIES = 2


class ClaimsIntakeAgent:
    """Enterprise claims intake with built-in retry and quality assurance"""
    
    def __init__(self):
        self.client = AIProjectClient.from_config(
            credential=DefaultAzureCredential()
        )
        self.model = MODEL_DEPLOYMENT_NAME
    
    def get_intake_instructions(self) -> str:
        """System prompt for intake agent"""
        return """You are an enterprise claims intake specialist. Your role is to extract and structure insurance claim information from images with high accuracy.

**Phase 1: OCR Processing**
1. Extract ALL visible text from the claim image
2. Identify key fields: policy_number, claim_amount, damage_description, incident_date, vehicle_info
3. Rate your confidence in each extraction (0.0-1.0)
4. Flag any illegible or ambiguous text
5. Assess overall image quality (high/medium/low)

**Phase 2: Data Structuring**
1. Convert extracted text into structured JSON
2. Validate data types (amounts are floats, dates are ISO format)
3. Compute overall extraction confidence
4. Flag missing critical fields

**Output JSON:**
{
  "ocr_confidence": 0.92,
  "image_quality": "high",
  "raw_text": "...",
  "fields_detected": {
    "policy_number": 0.95,
    "claim_amount": 0.88,
    "incident_date": 0.92
  },
  "structured_claim": {
    "policy_number": "COMM-AUTO-001",
    "claim_amount": 15000.00,
    "damage_description": "Front-end collision damage",
    "incident_date": "2026-01-15",
    "vehicle_info": {"year": "2023", "make": "Toyota", "model": "Camry"},
    "claim_type": "collision",
    "extraction_confidence": 0.88
  },
  "issues": [],
  "quality_flags": []
}"""
    
    def process_claim_image(self, state: ClaimProcessingState, 
                           image_path: str, 
                           retry_count: int = 0) -> ClaimProcessingState:
        """
        Process a single claim image through intake workflow
        
        Args:
            state: Current claim state
            image_path: Path to claim image
            retry_count: Current retry attempt
        
        Returns:
            Updated claim state
        """
        start_time = time.time()
        state.update_status(ClaimStatus.INTAKE_STARTED)
        
        try:
            logger.info(f"[{state.claim_id}] Starting intake for {image_path} (retry {retry_count})")
            
            # Encode image
            image_data = self._encode_image(image_path)
            
            # Call intake agent with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Process this claim image and structure the data:"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ]
            
            # Create agent and run
            agent = PromptAgentDefinition(
                name="claims-intake-agent",
                model=self.model,
                instructions=self.get_intake_instructions()
            )
            
            result = self.client.agents.run_sync(
                agent=agent,
                user_message="Process this claim image and structure the data:\n[IMAGE]"
            )
            
            # Parse response
            response_text = result.messages[-1].content[0].text
            response_json = json.loads(response_text)
            
            # Extract OCR result
            ocr_confidence = response_json.get("ocr_confidence", 0.0)
            state.ocr_result = OCRResult(
                raw_text=response_json.get("raw_text", ""),
                confidence_score=ocr_confidence,
                image_quality=response_json.get("image_quality", "medium"),
                processing_time_ms=(time.time() - start_time) * 1000,
                fields_detected=response_json.get("fields_detected", {}),
                errors=response_json.get("issues", [])
            )
            
            # Check confidence threshold
            if ocr_confidence < MIN_OCR_CONFIDENCE and retry_count < MAX_RETRIES:
                logger.warning(f"[{state.claim_id}] Low OCR confidence {ocr_confidence}, retrying...")
                state.add_error(ErrorInfo(
                    error_code="LOW_OCR_CONFIDENCE",
                    error_message=f"OCR confidence {ocr_confidence} below threshold {MIN_OCR_CONFIDENCE}",
                    severity=SeverityLevel.WARN,
                    retry_eligible=True,
                    recommendation="Retrying with enhanced image processing",
                    agent_name="claims-intake-agent"
                ))
                return self.process_claim_image(state, image_path, retry_count + 1)
            
            # Extract structured claim
            claim_data = response_json.get("structured_claim", {})
            extraction_confidence = claim_data.get("extraction_confidence", 0.0)
            
            state.structured_claim = StructuredClaim(
                policy_number=claim_data.get("policy_number", ""),
                claim_amount=float(claim_data.get("claim_amount", 0)),
                damage_description=claim_data.get("damage_description", ""),
                incident_date=claim_data.get("incident_date", ""),
                vehicle_info=claim_data.get("vehicle_info", {}),
                claim_type=claim_data.get("claim_type", ""),
                extraction_confidence=extraction_confidence
            )
            
            # Check extraction confidence
            if extraction_confidence < MIN_EXTRACTION_CONFIDENCE:
                state.add_error(ErrorInfo(
                    error_code="LOW_EXTRACTION_CONFIDENCE",
                    error_message=f"Extraction confidence {extraction_confidence} below {MIN_EXTRACTION_CONFIDENCE}",
                    severity=SeverityLevel.WARN,
                    retry_eligible=False,
                    recommendation="Manual review recommended before proceeding",
                    agent_name="claims-intake-agent"
                ))
            
            # Quality flags
            quality_flags = response_json.get("quality_flags", [])
            if quality_flags:
                state.metadata["quality_flags"] = quality_flags
            
            # Audit trail
            state.add_audit_entry(
                agent_name="claims-intake-agent",
                action="process_image",
                status="completed",
                message=f"Extracted claim data with confidence {extraction_confidence}",
                metadata={
                    "ocr_confidence": ocr_confidence,
                    "extraction_confidence": extraction_confidence,
                    "image_quality": state.ocr_result.image_quality,
                    "retry_count": retry_count
                }
            )
            
            state.update_status(ClaimStatus.INTAKE_COMPLETED)
            state.intake_duration_ms = (time.time() - start_time) * 1000
            
            logger.info(f"[{state.claim_id}] Intake completed in {state.intake_duration_ms:.0f}ms")
            return state
            
        except Exception as e:
            logger.error(f"[{state.claim_id}] Intake failed: {str(e)}")
            state.add_error(ErrorInfo(
                error_code="INTAKE_PROCESSING_FAILED",
                error_message=str(e),
                severity=SeverityLevel.ERROR,
                retry_eligible=True if retry_count < MAX_RETRIES else False,
                recommendation="Check image format and try again" if retry_count < MAX_RETRIES else "Manual processing required",
                agent_name="claims-intake-agent"
            ))
            state.update_status(ClaimStatus.INTAKE_FAILED)
            raise
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
