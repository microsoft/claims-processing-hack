#!/usr/bin/env python3
"""
OCR Text Extraction Agent - Extracts and structures text from JPEG images.
Uses GPT-4o-mini to parse OCR results and create structured text data.
Focuses solely on text extraction - does not analyze visual content like car damage.

Usage:
    python json_structuring_agent.py <ocr_result.json or ocr_text.txt>
    
Example with OCR JSON output:
    python json_structuring_agent.py ../ocr_results/document_ocr_result.json
    
"""
import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Azure AI Foundry SDK
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
project_endpoint = os.environ.get("AI_FOUNDRY_PROJECT_ENDPOINT")
# Use GPT-4o-mini for this agent
model_deployment_name = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")


def get_agent_instructions() -> str:
    """
    Generate agent instructions for OCR text extraction from JPEG pictures.
    
    Returns:
        Agent instruction string for pure OCR extraction
    """
    return """You are an expert OCR text extraction assistant specialized in extracting and structuring text content from JPEG images.

**Your Task**:
Extract all visible text from the provided JPEG image and structure it into a clean, organized JSON format. Focus solely on text extraction - do not analyze or describe any visual elements, objects, or non-text content in the image.

**JSON Output Structure**:
{
  "document_type": "form | letter | receipt | invoice | certificate | report | handwritten | mixed | other",
  "extracted_text": {
    "raw_text": "Complete extracted text preserving original layout where possible",
    "text_blocks": [
      {
        "block_id": 1,
        "content": "Text content of this block",
        "text_type": "printed | handwritten | mixed"
      }
    ],
    "structured_fields": {
      "titles": ["Any document titles or headers"],
      "dates": ["Extracted dates in original format"],
      "names": ["Person or organization names found"],
      "addresses": ["Any addresses found"],
      "phone_numbers": ["Phone numbers found"],
      "email_addresses": ["Email addresses found"],
      "reference_numbers": ["Document numbers, IDs, or reference codes"],
      "amounts": ["Monetary amounts or numeric values with context"]
    }
  },
  "text_quality": {
    "overall_legibility": "high | medium | low",
    "issues": ["List any text that was unclear or partially readable"]
  },
  "confidence": "high | medium | low",
  "extraction_notes": "Notes about the extraction quality or any ambiguities"
}

**Processing Rules**:
1. Extract ALL visible text from the image - do not skip any text content
2. Preserve the original text exactly as it appears (spelling, formatting, punctuation)
3. Organize text blocks in reading order (top to bottom, left to right)
4. Identify and categorize structured fields (dates, names, numbers, etc.)
5. Note any text that is unclear, partially visible, or difficult to read
6. Use null for structured fields where no relevant text is found
7. Set confidence level based on text clarity and extraction completeness
8. Focus ONLY on text - ignore any images, graphics, logos, or visual elements
9. Return ONLY valid JSON, no additional commentary

**Important**: 
- Your entire response must be valid JSON that can be parsed
- Do not include any text before or after the JSON object
- Do not describe or analyze any pictures, photos, or visual content - extract text only"""


def structure_ocr_to_json(ocr_text: str, source_file: str = None, project_client=None, agent=None) -> dict:
    """
    Convert OCR text into structured JSON format using GPT-4o-mini agent.
    
    Args:
        ocr_text: The raw OCR text to structure
        source_file: Optional path to the source file for metadata
        project_client: Optional existing AIProjectClient
        agent: Optional existing agent to reuse
        
    Returns:
        Structured JSON dictionary containing extracted text information
    """
    try:
        logger.info(f"Processing OCR text from: {source_file or 'unknown source'}")
        
        # Create client if not provided
        should_close_client = False
        if project_client is None:
            logger.info("Creating AI Project Client...")
            project_client = AIProjectClient(
                endpoint=project_endpoint,
                credential=DefaultAzureCredential(),
            )
            should_close_client = True
        
        # Get agent instructions for pure OCR text extraction
        agent_instructions = get_agent_instructions()
        
        # Create the agent
        agent = project_client.agents.create_version(
            agent_name="OCRTextExtractionAgent",
            definition=PromptAgentDefinition(
                model=model_deployment_name,
                instructions=agent_instructions,
                temperature=0.1,  # Low temperature for consistent, factual extraction
            ),
        )
        
        logger.info(f"✅ Created OCR Text Extraction Agent: {agent.name} (version {agent.version})")
        
        # Get OpenAI client for responses
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
        
        # Try to parse the response as JSON
        # Remove markdown code fences if present
        if response_text.startswith("```"):
            # Find first { and last }
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}")
            if start_idx != -1 and end_idx != -1:
                response_text = response_text[start_idx:end_idx+1]
        
        structured_data = json.loads(response_text)
        
        # Add metadata
        structured_data["metadata"] = {
            "source_file": source_file or "unknown",
            "processing_timestamp": datetime.now().isoformat(),
            "agent_model": model_deployment_name,
            "original_text_length": len(ocr_text)
        }
        
        logger.info("✓ Successfully extracted and structured OCR text into JSON")
        return structured_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse agent response as JSON: {e}")
        # Return error structure
        return {
            "error": "JSON parsing failed",
            "error_details": str(e),
            "raw_response": response_text if 'response_text' in locals() else "No response",
            "metadata": {
                "source_file": source_file or "unknown",
                "processing_timestamp": datetime.now().isoformat(),
                "agent_model": model_deployment_name
            }
        }
    
    except Exception as e:
        logger.error(f"Error in JSON structuring: {e}")
        return {
            "error": "Processing failed",
            "error_details": str(e),
            "metadata": {
                "source_file": source_file or "unknown",
                "processing_timestamp": datetime.now().isoformat()
            }
        }


def process_ocr_result(ocr_result_json: str) -> dict:
    """
    Process an OCR result JSON string and structure its text content.
    
    Args:
        ocr_result_json: JSON string from OCR agent output
        
    Returns:
        Structured JSON dictionary
    """
    try:
        # Parse OCR result
        ocr_data = json.loads(ocr_result_json)
        
        if ocr_data.get("status") != "success":
            return {
                "error": "OCR processing failed",
                "ocr_error": ocr_data.get("error", "Unknown error"),
                "metadata": {
                    "source_file": ocr_data.get("file_path", "unknown"),
                    "processing_timestamp": datetime.now().isoformat()
                }
            }
        
        # Extract OCR text and metadata
        ocr_text = ocr_data.get("text", "")
        source_file = ocr_data.get("file_path")
        
        if not ocr_text:
            return {
                "error": "No text extracted from OCR",
                "metadata": {
                    "source_file": source_file or "unknown",
                    "processing_timestamp": datetime.now().isoformat()
                }
            }
        
        # Structure the OCR text
        return structure_ocr_to_json(ocr_text, source_file)
        
    except json.JSONDecodeError as e:
        return {
            "error": "Invalid OCR result JSON",
            "error_details": str(e),
            "metadata": {
                "processing_timestamp": datetime.now().isoformat()
            }
        }


def main():
    """Main function to create and test the JSON Structuring Agent."""
    
    print("=== JSON Structuring Agent with GPT-4o-mini ===\n")
    
    try:
        # Get input from CLI args
        if len(sys.argv) < 2:
            print("Usage: python json_structuring_agent.py <ocr_text_file_or_json>")
            print("\nExample with OCR JSON result:")
            print("  python json_structuring_agent.py ocr_result.json")
            print("\nExample with raw text file:")
            print("  python json_structuring_agent.py extracted_text.txt")
            return
        
        input_file = sys.argv[1]
        
        if not os.path.exists(input_file):
            print(f"❌ Error: File not found: {input_file}")
            return
        
        print(f"📄 Processing file: {input_file}\n")
        
        # Create AI Project Client
        project_client = AIProjectClient(
            endpoint=project_endpoint,
            credential=DefaultAzureCredential(),
        )
        
        with project_client:
            # Generate agent instructions for OCR text extraction
            agent_instructions = get_agent_instructions()
            
            # Create the agent
            agent = project_client.agents.create_version(
                agent_name="OCRTextExtractionAgent",
                definition=PromptAgentDefinition(
                    model=model_deployment_name,
                    instructions=agent_instructions,
                    temperature=0.1,
                ),
            )
            
            print(f"✅ Created OCR Text Extraction Agent: {agent.name} (version {agent.version})")
            print(f"   Agent visible in Foundry portal\n")
            
            # Read input file
            with open(input_file, 'r') as f:
                file_content = f.read()
            
            # Check if it's OCR JSON result or raw text
            is_ocr_json = False
            ocr_text = ""
            source_file = input_file
            
            try:
                # Try to parse as JSON (OCR result)
                ocr_data = json.loads(file_content)
                if "text" in ocr_data and "status" in ocr_data:
                    is_ocr_json = True
                    if ocr_data.get("status") == "success":
                        ocr_text = ocr_data.get("text", "")
                        source_file = ocr_data.get("file_path", input_file)
                    else:
                        print(f"❌ OCR failed: {ocr_data.get('error', 'Unknown error')}")
                        return
                else:
                    # JSON but not OCR format, treat as raw text
                    ocr_text = file_content
            except json.JSONDecodeError:
                # Not JSON, treat as raw text
                ocr_text = file_content
            
            print(f"   Type: {'OCR JSON result' if is_ocr_json else 'Raw text'}")
            print(f"   Text length: {len(ocr_text)} characters\n")
            
            # Get OpenAI client
            openai_client = project_client.get_openai_client()
            
            # Create user query
            user_query = f"""Please extract and structure all text from the following OCR output into the standardized JSON format.

---OCR TEXT START---
{ocr_text}
---OCR TEXT END---

Return only the structured JSON object with all extracted text."""
            
            print("🤖 Sending to agent for text extraction...")
            
            # Get response from agent
            response = openai_client.responses.create(
                input=user_query,
                extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            )
            
            # Extract and parse response
            response_text = response.output_text.strip()
            
            # Remove markdown code fences if present
            if response_text.startswith("```"):
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    response_text = response_text[start_idx:end_idx+1]
            
            try:
                result = json.loads(response_text)
                
                # Add metadata
                result["metadata"] = {
                    "source_file": source_file,
                    "processing_timestamp": datetime.now().isoformat(),
                    "agent_model": model_deployment_name,
                    "original_text_length": len(ocr_text)
                }
                
                # Output results
                print("\n=== Structured JSON Output ===")
                print(json.dumps(result, indent=2))
                
                # Save to output file
                output_file = input_file.rsplit('.', 1)[0] + '_structured.json'
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2)
                
                print(f"\n✓ Structured JSON saved to: {output_file}")
                
                # Summary
                print(f"\n📊 Summary:")
                print(f"   Document type: {result.get('document_type', 'unknown')}")
                print(f"   Vehicle side: {result.get('vehicle_side', 'unspecified')}")
                print(f"   Confidence: {result.get('confidence', 'unknown')}")
                
                if result.get('extracted_data', {}).get('policy_holder', {}).get('name'):
                    print(f"   Policy holder: {result['extracted_data']['policy_holder']['name']}")
                if result.get('extracted_data', {}).get('damages', {}).get('estimated_amount'):
                    print(f"   Estimated amount: ${result['extracted_data']['damages']['estimated_amount']}")
                
                print("\n✓ JSON Structuring Agent completed successfully!")
                
            except json.JSONDecodeError as e:
                print(f"\n❌ Failed to parse agent response as JSON: {e}")
                print(f"Raw response:\n{response_text}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        print(f"❌ Error: {e}")
        import traceback
        print(f"\nStack trace:\n{traceback.format_exc()}")


if __name__ == "__main__":
    main()
