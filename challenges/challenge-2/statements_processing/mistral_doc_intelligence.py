"""
Mistral Document AI integration for OCR processing.
Adapted for claims processing hackathon - uses .env file configuration.
"""

import base64
import json
import logging
import httpx
import os
from collections import defaultdict
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Statements files location (match GPT script structure)
STATEMENTS_IMAGE_FOLDER = "../../challenge-1/data/statements/"
STATEMENTS_OUTPUT_LOCATION = "../output/mistral/"


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
        base64_encoded = base64.b64encode(file_bytes).decode("utf-8")

    # Determine file type and construct data URL
    if file_path.lower().endswith(".pdf"):
        data_url = f"data:application/pdf;base64,{base64_encoded}"
        url_type = "document_url"
    elif file_path.lower().endswith((".jpg", ".jpeg")):
        data_url = f"data:image/jpeg;base64,{base64_encoded}"
        url_type = "image_url"
    elif file_path.lower().endswith(".png"):
        data_url = f"data:image/png;base64,{base64_encoded}"
        url_type = "image_url"
    else:
        # Default to document
        data_url = f"data:application/pdf;base64,{base64_encoded}"
        url_type = "document_url"

    return data_url, url_type


def get_mistral_doc_ai_client():
    """
    Get Mistral Document AI configuration from environment variables.

    Returns:
        Dictionary with endpoint, API key, and model name
    """
    mistral_endpoint = os.getenv("MISTRAL_DOCUMENT_AI_ENDPOINT")
    mistral_api_key = os.getenv("MISTRAL_DOCUMENT_AI_KEY")
    mistral_model = os.getenv(
        "MISTRAL_DOCUMENT_AI_DEPLOYMENT_NAME", "mistral-document-ai-2505"
    )

    # Endpoint format: https://<resource>.cognitiveservices.azure.com/providers/mistral/azure/ocr
    endpoint = mistral_endpoint.rstrip("/") + "/providers/mistral/azure/ocr"

    return {"endpoint": endpoint, "api_key": mistral_api_key, "model": mistral_model}


def get_ocr_results(file_path: str, json_schema: Optional[dict] = None) -> str:
    """
    Extract text from document using Mistral Document AI.

    Args:
        file_path: Path to the file to process
        json_schema: Optional JSON schema for structured extraction with bbox annotation

    Returns:
        Extracted text content from the document
    """
    import threading

    thread_id = threading.current_thread().ident

    logger.info(
        f"[Thread-{thread_id}] Starting Mistral Document AI OCR for: {file_path}"
    )

    # Get Mistral configuration
    mistral_config = get_mistral_doc_ai_client()
    endpoint = mistral_config["endpoint"]
    api_key = mistral_config["api_key"]
    model_name = mistral_config["model"]

    # Encode file to base64
    logger.info(f"[Thread-{thread_id}] Encoding file to base64")
    data_url, url_type = encode_file_to_base64(file_path)

    # Mistral Document AI API format
    headers = {"Content-Type": "application/json", "api-key": api_key}

    # Payload format for Mistral Document AI OCR endpoint
    payload = {"model": model_name, "document": {"type": url_type, url_type: data_url}}

    logger.info(f"[Thread-{thread_id}] Submitting document to Mistral Document AI")
    print(f"   📡 Endpoint: {endpoint}")
    print(f"   📦 Model: {model_name}")
    print(f"   🔧 Format: Mistral Document AI (Foundry)")

    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(endpoint, json=payload, headers=headers)

            print(f"   📊 Response Status: {response.status_code}")
            print(f"   📄 Response Length: {len(response.text)} chars")

            # Debug: Show response preview
            if len(response.text) > 0:
                print(f"   👀 Response Preview: {response.text[:200]}")
            else:
                print(f"   ⚠️  Empty response received!")
                print(f"   Response Headers: {dict(response.headers)}")

            response.raise_for_status()

            result = response.json()
            logger.info(f"[Thread-{thread_id}] Mistral Document AI response received")

            # Extract text content from response (Mistral Document AI format)
            ocr_text = ""

            if "pages" in result and isinstance(result["pages"], list):
                # Extract markdown from pages (standard Mistral DocAI format)
                markdown_parts = []
                for page in result["pages"]:
                    if isinstance(page, dict) and "markdown" in page:
                        markdown_parts.append(page["markdown"])
                ocr_text = "\n\n".join(markdown_parts)
                logger.info(
                    f"[Thread-{thread_id}] Extracted markdown from {len(result['pages'])} page(s)"
                )
                print(f"   ✅ Extracted markdown from {len(result['pages'])} page(s)")
            elif "content" in result:
                ocr_text = result["content"]
                print(f"   ✅ Extracted content field")
            elif "text" in result:
                ocr_text = result["text"]
                print(f"   ✅ Extracted text field")
            elif "choices" in result and len(result["choices"]) > 0:
                # Fallback: OpenAI format
                ocr_text = result["choices"][0].get("message", {}).get("content", "")
                print(f"   ✅ Extracted from OpenAI format")
            else:
                logger.warning(f"[Thread-{thread_id}] Unexpected response format")
                print(f"   ⚠️  Unexpected response format. Keys: {list(result.keys())}")
                ocr_text = ""

            logger.info(
                f"[Thread-{thread_id}] Mistral Document AI OCR completed, {len(ocr_text)} characters"
            )
            print(f"   ✅ OCR completed: {len(ocr_text)} characters extracted")
            return ocr_text

    except httpx.HTTPStatusError as e:
        logger.error(
            f"[Thread-{thread_id}] Mistral API HTTP error: {e.response.status_code}"
        )
        logger.error(f"[Thread-{thread_id}] Response: {e.response.text}")
        print(f"   ❌ HTTP Error {e.response.status_code}: {e.response.text[:500]}")
        raise Exception(
            f"Mistral Document AI API error: {e.response.status_code} - {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"[Thread-{thread_id}] Mistral API request error: {str(e)}")
        print(f"   ❌ Request Error: {str(e)}")
        raise Exception(f"Mistral Document AI request failed: {str(e)}")
    except Exception as e:
        logger.error(
            f"[Thread-{thread_id}] Unexpected error during Mistral Document AI processing: {str(e)}"
        )
        print(f"   ❌ Unexpected Error: {str(e)}")
        raise


def process_statements_with_mistral():
    """Process all statement images from local folder using Mistral Document AI."""

    # List all local image files and group them by claim number
    image_files = [
        f
        for f in os.listdir(STATEMENTS_IMAGE_FOLDER)
        if f.lower().endswith((".jpeg", ".jpg", ".png"))
    ]

    # Ensure output directory exists before writing Markdown files
    os.makedirs(STATEMENTS_OUTPUT_LOCATION, exist_ok=True)

    # Process each image
    for image in image_files:
        print(f"Processing {image} with Mistral Document AI...")
        image_path = os.path.join(STATEMENTS_IMAGE_FOLDER, image)
        ocr_text = get_ocr_results(image_path)

        md_path = os.path.join(
            STATEMENTS_OUTPUT_LOCATION, f"{os.path.splitext(image)[0]}.md"
        )
        with open(md_path, "w", encoding="utf-8") as md_file:
            md_file.write(ocr_text)

        print(f"💾 Markdown saved to {md_path}")

    print(f"\n✅ Processed {len(image_files)} claims with Mistral Document AI")

    return image_files


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    process_statements_with_mistral()
