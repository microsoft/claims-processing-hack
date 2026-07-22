#!/usr/bin/env python3
"""
Claims Processing Multi-Agent Workflow
Orchestrates OCR Agent and OCR Text Extraction Agent using sequential processing
"""
import os
import sys
import json
import logging
import asyncio
from dotenv import load_dotenv

# Azure AI Foundry SDK
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

# Import the OCR and JSON structuring functions from challenge-3
# Handle both local development and container deployment paths
if os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'challenge-3', 'agents')):
    # Local development: challenge-3 is a sibling directory
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'challenge-3', 'agents'))
else:
    # Container deployment: challenge-3 is in the same directory as the app
    sys.path.append(os.path.join(os.path.dirname(__file__), 'challenge-3', 'agents'))
from ocr_agent import extract_text_with_ocr

# Load environment
load_dotenv(override=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ENDPOINT = os.environ.get("AI_FOUNDRY_PROJECT_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME")


async def process_claim_workflow(image_path: str) -> dict:
    """
    Multi-agent workflow that orchestrates OCR and JSON structuring.
    
    Args:
        image_path: Path to the claim image file
        
    Returns:
        Structured claim data as dictionary
    """
    logger.info(f"🔄 Starting claims processing workflow for: {image_path}")
    
    # Step 1: OCR Agent - Extract text from image
    logger.info("📸 Step 1: OCR Agent - Extracting text from image...")
    ocr_result_json = extract_text_with_ocr(image_path)
    ocr_result = json.loads(ocr_result_json)
    
    if ocr_result.get("status") == "error":
        logger.error(f"OCR failed: {ocr_result.get('error')}")
        return {
            "error": "OCR processing failed",
            "details": ocr_result.get("error"),
            "image_path": image_path
        }
    
    ocr_text = ocr_result.get("text", "")
    logger.info(f"✅ OCR Agent extracted {len(ocr_text)} characters")
    
    # Step 2: OCR Text Extraction Agent - Convert OCR text to structured JSON
    logger.info("📊 Step 2: OCR Text Extraction Agent - Converting to structured JSON...")
    
    # Create AI Project Client
    with AIProjectClient(
        endpoint=ENDPOINT,
        credential=DefaultAzureCredential(),
    ) as project_client:
        
        # Create OCR Text Extraction agent
        agent = project_client.agents.create_version(
            agent_name="WorkflowOCRTextExtractionAgent",
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions="""You are an expert OCR text extraction assistant specialized in extracting and structuring text content from JPEG images.

Your task:
1. Receive OCR text extracted from documents
2. Extract ALL visible text and structure it into a clean, organized JSON format
3. Focus solely on text extraction - do not analyze any visual elements or pictures
4. Structure the text into valid JSON format with these fields:
   - document_type: form | letter | receipt | invoice | certificate | report | handwritten | mixed | other
   - extracted_text: {raw_text, text_blocks[], structured_fields}
   - text_quality: {overall_legibility, issues[]}
   - confidence: high | medium | low
5. Return ONLY valid JSON, no markdown or explanations

Always return properly formatted JSON.""",
                temperature=0.1,
            ),
        )
        
        logger.info(f"Created OCR Text Extraction Agent: {agent.name}")
        
        # Get OpenAI client for agent responses
        openai_client = project_client.get_openai_client()
        
        # Create user query with OCR text
        user_query = f"""Please extract and structure all text from the following OCR output into the standardized JSON format.

---OCR TEXT START---
{ocr_text}
---OCR TEXT END---

Return only the structured JSON object with all extracted text."""
        
        logger.info("Sending OCR text to extraction agent...")
        
        # Get response from agent
        response = openai_client.responses.create(
            input=user_query,
            extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
        )
        
        # Extract the JSON from response
        response_text = response.output_text.strip()
        
        # Parse JSON from response
        try:
            # Remove markdown code fences if present
            if response_text.startswith("```"):
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start != -1 and end != -1:
                    response_text = response_text[start:end]
            
            structured_data = json.loads(response_text)
            logger.info("✅ Successfully extracted and structured OCR text into JSON")
            
            # Add metadata
            structured_data["metadata"] = {
                "source_image": image_path,
                "ocr_characters": len(ocr_text),
                "workflow": "multi-agent"
            }
            
            return structured_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {
                "error": "JSON parsing failed",
                "details": str(e),
                "raw_response": response_text
            }


async def main():
    """Test the workflow with a sample image"""
    if len(sys.argv) < 2:
        print("Usage: python workflow_orchestrator.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"❌ Error: Image not found: {image_path}")
        sys.exit(1)
    
    # Run workflow
    result = await process_claim_workflow(image_path)
    
    print("\n" + "="*60)
    print("📊 WORKFLOW OUTPUT")
    print("="*60)
    print(json.dumps(result, indent=2))
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
