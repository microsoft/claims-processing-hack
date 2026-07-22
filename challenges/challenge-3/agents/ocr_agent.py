#!/usr/bin/env python3
"""
OCR Agent - Specialized agent for document and image text extraction.
Uses Mistral Document AI for OCR processing with Azure AI Foundry Agents.

Usage:
    python ocr_agent.py [IMAGE_PATH]
    
Example:
    python ocr_agent.py /path/to/image.jpg
"""
import os
import sys
import base64
import json
import logging
import httpx
from datetime import datetime
from dotenv import load_dotenv

# Azure AI Foundry SDK
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
from azure.identity import DefaultAzureCredential
from openai.types.responses.response_input_param import FunctionCallOutput

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
project_endpoint = os.environ.get("AI_FOUNDRY_PROJECT_ENDPOINT")
model_deployment_name = os.environ.get("MODEL_DEPLOYMENT_NAME")


def encode_file_to_base64(file_path: str) -> tuple[str, str]:
    """
    Encode a file to base64 string and determine its type.
    
    Args:
        file_path: Path to the file to encode
        
    Returns:
        Tuple of (base64_string, file_type) where file_type is 'document_url' or 'image_url'
    """
    with open(file_path, "rb") as f:
        file_bytes = f.read()
        base64_encoded = base64.b64encode(file_bytes).decode('utf-8')
    
    # Determine file type and construct data URL
    if file_path.lower().endswith('.pdf'):
        data_url = f"data:application/pdf;base64,{base64_encoded}"
        url_type = "document_url"
    elif file_path.lower().endswith(('.jpg', '.jpeg')):
        data_url = f"data:image/jpeg;base64,{base64_encoded}"
        url_type = "image_url"
    elif file_path.lower().endswith('.png'):
        data_url = f"data:image/png;base64,{base64_encoded}"
        url_type = "image_url"
    else:
        # Default to document
        data_url = f"data:application/pdf;base64,{base64_encoded}"
        url_type = "document_url"
    
    return data_url, url_type


def extract_text_with_ocr(image_path: str) -> str:
    """
    Extract text from an image or document using Mistral Document AI OCR.
    
    Args:
        image_path: Path to the image or document file
        
    Returns:
        JSON string containing OCR results with status, text, and metadata
    """
    try:
        logger.info(f"Starting OCR for: {image_path}")
        
        # Validate file exists
        if not os.path.exists(image_path):
            return json.dumps({
                "status": "error",
                "error": f"File not found: {image_path}",
                "text": "",
                "file_path": image_path
            })
        
        # Get Mistral Document AI configuration
        mistral_endpoint = os.getenv('MISTRAL_DOCUMENT_AI_ENDPOINT')
        mistral_api_key = os.getenv('MISTRAL_DOCUMENT_AI_KEY')
        mistral_model = os.getenv('MISTRAL_DOCUMENT_AI_DEPLOYMENT_NAME', 'mistral-document-ai-2505')
        
        if not mistral_endpoint or not mistral_api_key:
            return json.dumps({
                "status": "error",
                "error": "Mistral Document AI credentials not configured in environment",
                "text": "",
                "file_path": image_path
            })
        
        # Format endpoint
        endpoint = mistral_endpoint.rstrip('/') + '/providers/mistral/azure/ocr'
        
        # Encode file to base64
        logger.info(f"Encoding file to base64: {image_path}")
        data_url, url_type = encode_file_to_base64(image_path)
        
        # Prepare API request
        headers = {
            "Content-Type": "application/json",
            "api-key": mistral_api_key
        }
        
        payload = {
            "model": mistral_model,
            "document": {
                "type": url_type,
                url_type: data_url
            }
        }
        
        logger.info(f"Submitting to Mistral Document AI: {endpoint}")
        
        # Make API call
        with httpx.Client(timeout=300.0) as client:
            response = client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Received response from Mistral Document AI")
            
            # Extract text from response
            ocr_text = ""
            pages_count = 0
            
            if "pages" in result and isinstance(result["pages"], list):
                # Extract markdown from pages (standard Mistral DocAI format)
                markdown_parts = []
                for page in result["pages"]:
                    if isinstance(page, dict) and "markdown" in page:
                        markdown_parts.append(page["markdown"])
                ocr_text = "\n\n".join(markdown_parts)
                pages_count = len(result["pages"])
                logger.info(f"Extracted markdown from {pages_count} page(s)")
            elif "content" in result:
                ocr_text = result["content"]
            elif "text" in result:
                ocr_text = result["text"]
            elif "choices" in result and len(result["choices"]) > 0:
                # Fallback: OpenAI format
                ocr_text = result["choices"][0].get("message", {}).get("content", "")
            else:
                logger.warning(f"Unexpected response format from Mistral API")
                ocr_text = ""
            
            # Build success response
            success_result = {
                "status": "success",
                "text": ocr_text,
                "file_path": image_path,
                "file_name": os.path.basename(image_path),
                "character_count": len(ocr_text),
                "pages_processed": pages_count if pages_count > 0 else 1,
                "model_used": mistral_model,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"OCR completed: {len(ocr_text)} characters extracted from {image_path}")
            return json.dumps(success_result)
            
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP Error {e.response.status_code}: {e.response.text[:500]}"
        logger.error(f"Mistral API HTTP error: {error_msg}")
        return json.dumps({
            "status": "error",
            "error": error_msg,
            "text": "",
            "file_path": image_path
        })
    except httpx.RequestError as e:
        error_msg = f"Request failed: {str(e)}"
        logger.error(f"Mistral API request error: {error_msg}")
        return json.dumps({
            "status": "error",
            "error": error_msg,
            "text": "",
            "file_path": image_path
        })
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"OCR processing error: {error_msg}")
        return json.dumps({
            "status": "error",
            "error": error_msg,
            "text": "",
            "file_path": image_path
        })



# Define the OCR function tool for the agent
ocr_function_tool = FunctionTool(
    name="extract_text_with_ocr",
    parameters={
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": "Path to the image or document file to extract text from (JPEG, PNG, PDF)"
            }
        },
        "required": ["image_path"],
        "additionalProperties": False
    },
    description="Extract text from an image or document using Mistral Document AI OCR. Supports JPEG, PNG, and PDF files.",
    strict=True
)


def main():
    """Main function to create and test the OCR Agent."""
    
    print("=== OCR Agent with Azure AI Foundry ===\n")
    
    try:
        # Get image path from CLI args or use default
        test_image_path = sys.argv[1] if len(sys.argv) > 1 else "/workspaces/claims-processing-hack/challenge-1/data/statements/crash1_front.jpeg"
        
        # Create output directory for OCR results
        output_dir = "/workspaces/claims-processing-hack/challenge-3/ocr_results"
        os.makedirs(output_dir, exist_ok=True)
        
        # Create AI Project Client
        project_client = AIProjectClient(
            endpoint=project_endpoint,
            credential=DefaultAzureCredential(),
        )
        
        with project_client:
            # Agent instructions
            agent_instructions = """You are an expert OCR (Optical Character Recognition) Agent specialized in extracting text from images and documents.

Your primary responsibility is to extract text from images and documents using the available OCR tool.

**Available Tool**:
- `extract_text_with_ocr`: Extracts text from image or document files using Mistral Document AI

**Processing Approach**:
- When given a file path, use the OCR tool to extract text
- Report extraction results including character count and status
- For errors, provide clear diagnostic information
- For successful extractions, summarize key content found in the document

You are designed to be a reliable, accurate OCR processing service for insurance claims processing."""
            
            # Create the agent version with the function tool
            agent = project_client.agents.create_version(
                agent_name="OCRAgent",
                definition=PromptAgentDefinition(
                    model=model_deployment_name,
                    instructions=agent_instructions,
                    tools=[ocr_function_tool],
                ),
            )
            
            print(f"✅ Created OCR Agent: {agent.name} (version {agent.version})")
            print(f"   Agent visible in Foundry portal\n")
            
            # Get OpenAI client for responses
            openai_client = project_client.get_openai_client()
            
            # Test the agent
            print(f"🧪 Testing the agent with OCR extraction...")
            print(f"   Processing: {test_image_path}\n")
            
            if not os.path.exists(test_image_path):
                print(f"   ✗ Error: File not found: {test_image_path}")
                return
            
            # Create initial response with user query
            user_query = f"""Please extract all text from this image file:
{test_image_path}

Provide a summary of what text was found and what it represents."""
            
            response = openai_client.responses.create(
                input=user_query,
                extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            )
            
            print(f"Response output: {response.output_text}")
            
            # Process function calls and save results
            input_list = []
            ocr_result_json = None
            
            for item in response.output:
                if item.type == "function_call":
                    if item.name == "extract_text_with_ocr":
                        print(f"\n📞 Agent calling function: {item.name}")
                        
                        # Parse function arguments
                        args = json.loads(item.arguments)
                        print(f"   Arguments: {args}")
                        
                        # Execute the OCR function
                        ocr_result_json = extract_text_with_ocr(**args)
                        
                        print(f"   ✓ Function executed successfully")
                        
                        # Save OCR result to JSON file
                        base_name = os.path.splitext(os.path.basename(test_image_path))[0]
                        output_file = os.path.join(output_dir, f"{base_name}_ocr_result.json")
                        
                        with open(output_file, 'w') as f:
                            ocr_data = json.loads(ocr_result_json)
                            json.dump(ocr_data, f, indent=2)
                        
                        print(f"   💾 Saved OCR result to: {output_file}")
                        
                        # Provide function call results back to the agent
                        input_list.append(
                            FunctionCallOutput(
                                type="function_call_output",
                                call_id=item.call_id,
                                output=ocr_result_json,
                            )
                        )
            
            # If function was called, get final response
            if input_list:
                print(f"\n🤖 Getting agent's final response...\n")
                
                final_response = openai_client.responses.create(
                    input=input_list,
                    previous_response_id=response.id,
                    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
                )
                
                print("=== OCR Agent Final Response ===")
                print(final_response.output_text)
                print()
            
            print("✓ OCR Agent completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        print(f"❌ Error: {e}")
        print("Make sure you have run 'az login' and have proper Azure credentials configured.")
        import traceback
        print(f"\nStack trace:\n{traceback.format_exc()}")


if __name__ == "__main__":
    main()

