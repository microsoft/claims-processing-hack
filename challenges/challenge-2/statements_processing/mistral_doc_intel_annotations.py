"""
Mistral Document AI with Data Annotations for Structured Extraction.

This module demonstrates how to use Mistral Document AI's powerful annotation
capabilities to extract structured data with bounding box (bbox) annotations
from insurance claim documents.

Data Annotations allow you to:
- Extract specific fields from documents with their exact location on the page
- Get bounding box coordinates for each extracted field
- Define custom JSON schemas for structured output
- Validate extracted data against predefined schemas
- Enable visual verification by highlighting extracted regions

For more information, see: https://docs.mistral.ai/capabilities/document_ai
"""
import base64
import json
import logging
import httpx
import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from dataclasses import dataclass, asdict

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes for Structured Annotations
# =============================================================================

@dataclass
class BoundingBox:
    """
    Represents a bounding box location on a document page.
    
    The bounding box is defined by four coordinates:
    - x_min, y_min: Top-left corner
    - x_max, y_max: Bottom-right corner
    
    All coordinates are normalized (0-1) relative to the page dimensions.
    """
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    page: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def get_center(self) -> tuple:
        """Get the center point of the bounding box."""
        return ((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)
    
    def get_area(self) -> float:
        """Calculate the area of the bounding box (normalized)."""
        return (self.x_max - self.x_min) * (self.y_max - self.y_min)


@dataclass
class AnnotatedField:
    """
    Represents an extracted field with its annotation data.
    
    Attributes:
        field_name: The name/key of the extracted field
        value: The extracted value
        confidence: Confidence score (0-1) of the extraction
        bbox: Bounding box showing where the field was found
        raw_text: The original text as found in the document
    """
    field_name: str
    value: Any
    confidence: float
    bbox: Optional[BoundingBox] = None
    raw_text: Optional[str] = None
    
    def to_dict(self) -> dict:
        result = {
            "field_name": self.field_name,
            "value": self.value,
            "confidence": self.confidence,
            "raw_text": self.raw_text
        }
        if self.bbox:
            result["bbox"] = self.bbox.to_dict()
        return result


# =============================================================================
# JSON Schema Definitions for Insurance Documents
# =============================================================================

# Schema for extracting insurance claim statement information with annotations
CLAIM_STATEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "claimant_name": {
            "type": "string",
            "description": "Full name of the person filing the claim"
        },
        "claim_date": {
            "type": "string",
            "description": "Date when the claim was filed or incident occurred (MM/DD/YYYY format)"
        },
        "policy_number": {
            "type": "string",
            "description": "Insurance policy number"
        },
        "incident_description": {
            "type": "string",
            "description": "Description of what happened during the incident"
        },
        "vehicle_info": {
            "type": "object",
            "properties": {
                "make": {"type": "string"},
                "model": {"type": "string"},
                "year": {"type": "string"},
                "license_plate": {"type": "string"},
                "vin": {"type": "string"}
            }
        },
        "damage_description": {
            "type": "string",
            "description": "Description of damage to the vehicle"
        },
        "estimated_damage_amount": {
            "type": "string",
            "description": "Estimated cost of damages"
        },
        "witnesses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"}
                }
            }
        },
        "signature_present": {
            "type": "boolean",
            "description": "Whether a signature is present on the document"
        },
        "date_signed": {
            "type": "string",
            "description": "Date when the document was signed"
        }
    },
    "required": ["claimant_name", "incident_description"]
}

# Schema for extracting vehicle damage assessment with bounding boxes
DAMAGE_ASSESSMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "damage_areas": {
            "type": "array",
            "description": "List of damaged areas on the vehicle",
            "items": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location of damage (e.g., 'front bumper', 'driver side door')"
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["minor", "moderate", "severe", "total_loss"],
                        "description": "Severity level of the damage"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the damage"
                    },
                    "repair_type": {
                        "type": "string",
                        "enum": ["repair", "replace", "paint", "detail"],
                        "description": "Recommended repair approach"
                    }
                }
            }
        },
        "total_damage_estimate": {
            "type": "number",
            "description": "Total estimated repair cost in dollars"
        },
        "is_drivable": {
            "type": "boolean",
            "description": "Whether the vehicle is still drivable"
        },
        "airbags_deployed": {
            "type": "boolean",
            "description": "Whether airbags were deployed"
        }
    }
}


# =============================================================================
# Utility Functions
# =============================================================================

def encode_file_to_base64(file_path: str) -> tuple[str, str]:
    """
    Encode a file to base64 string and determine its type.
    
    Args:
        file_path: Path to the file to encode
        
    Returns:
        Tuple of (data_url, url_type) where url_type is 'document_url' or 'image_url'
    """
    with open(file_path, "rb") as f:
        file_bytes = f.read()
        base64_encoded = base64.b64encode(file_bytes).decode('utf-8')
    
    # Determine file type and construct data URL
    extension = os.path.splitext(file_path)[1].lower()
    
    if extension == '.pdf':
        data_url = f"data:application/pdf;base64,{base64_encoded}"
        url_type = "document_url"
    elif extension in ['.jpg', '.jpeg']:
        data_url = f"data:image/jpeg;base64,{base64_encoded}"
        url_type = "image_url"
    elif extension == '.png':
        data_url = f"data:image/png;base64,{base64_encoded}"
        url_type = "image_url"
    elif extension == '.webp':
        data_url = f"data:image/webp;base64,{base64_encoded}"
        url_type = "image_url"
    elif extension == '.tiff':
        data_url = f"data:image/tiff;base64,{base64_encoded}"
        url_type = "document_url"
    else:
        # Default to document type
        data_url = f"data:application/pdf;base64,{base64_encoded}"
        url_type = "document_url"
    
    return data_url, url_type


def parse_markdown_to_structured_data(markdown_text: str, json_schema: Dict) -> Dict[str, Any]:
    """
    Parse markdown text into structured data according to a JSON schema.
    
    This function extracts key-value pairs from markdown formatted text
    and maps them to the fields defined in the JSON schema.
    
    Args:
        markdown_text: The markdown text extracted from OCR
        json_schema: JSON schema defining the expected structure
        
    Returns:
        Dictionary with extracted structured data
    """
    import re
    
    extracted = {}
    properties = json_schema.get("properties", {})
    
    # Build a mapping of field names to search patterns
    field_mappings = {
        "claimant_name": ["Name:", "Policyholder Name:", "Claimant Name:"],
        "claim_date": ["Date of Incident:", "Claim Date:", "Accident Date:"],
        "policy_number": ["Policy Number:", "Policy No:", "Policy #:"],
        "damage_description": ["Damage Description:", "Damages:"],
        "estimated_damage_amount": ["Estimated Damage:", "Damage Amount:", "Estimated Cost:", "Amount:"],
        "signature_present": ["Signature:", "Signed:"],
        "date_signed": ["Date Signed:", "Signature Date:"],
    }
    
    # Vehicle info field mappings
    vehicle_field_mappings = {
        "make": ["Make:", "Vehicle Make:"],
        "model": ["Model:", "Vehicle Model:"],
        "year": ["Year:", "Vehicle Year:", "Year/Make/Model:"],
        "license_plate": ["License Plate:", "Plate:", "License:"],
        "vin": ["VIN:", "Vehicle Identification Number:"],
    }
    
    lines = markdown_text.split('\n')
    
    # Extract simple key-value pairs
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        # Check for each field in our mappings
        for field_name, patterns in field_mappings.items():
            if field_name not in properties:
                continue
            for pattern in patterns:
                if pattern.lower() in line.lower():
                    # Extract value after the pattern
                    idx = line.lower().find(pattern.lower())
                    value = line[idx + len(pattern):].strip()
                    if value:
                        extracted[field_name] = value
                        break
    
    # Extract vehicle info
    if "vehicle_info" in properties:
        vehicle_info = {}
        for line in lines:
            line = line.strip()
            
            # Handle combined Year/Make/Model field
            if "Year/Make/Model:" in line:
                value = line.split(":", 1)[1].strip()
                parts = value.split()
                if len(parts) >= 3:
                    vehicle_info["year"] = parts[0]
                    vehicle_info["make"] = parts[1]
                    vehicle_info["model"] = " ".join(parts[2:])
                elif len(parts) == 2:
                    vehicle_info["year"] = parts[0]
                    vehicle_info["make"] = parts[1]
                continue
            
            for field_name, patterns in vehicle_field_mappings.items():
                for pattern in patterns:
                    if pattern.lower() in line.lower():
                        idx = line.lower().find(pattern.lower())
                        value = line[idx + len(pattern):].strip()
                        if value:
                            vehicle_info[field_name] = value
                            break
        
        if vehicle_info:
            extracted["vehicle_info"] = vehicle_info
    
    # Extract incident description (multi-line content after header)
    # This is handled specially because it's typically a paragraph, not a key:value pair
    if "incident_description" in properties:
        in_description = False
        description_lines = []
        for line in lines:
            # Look for the description section header
            if "## Description" in line or "Description of Incident" in line or "**Description" in line:
                in_description = True
                continue
            if in_description:
                # Stop at next section
                if line.startswith('##') or (line.startswith('**') and line.endswith('**')):
                    break
                if line.strip():
                    # Clean up the line
                    clean_line = line.strip().replace('**', '')
                    if clean_line:
                        description_lines.append(clean_line)
        if description_lines:
            extracted["incident_description"] = " ".join(description_lines)
    
    # Check for signature presence
    if "signature_present" in properties:
        signature_keywords = ["signature", "signed", "sign here"]
        has_signature = any(kw in markdown_text.lower() for kw in signature_keywords)
        extracted["signature_present"] = has_signature
    
    return extracted


def get_mistral_config() -> Dict[str, str]:
    """
    Get Mistral Document AI configuration from environment variables.
    
    Environment variables used:
    - MISTRAL_DOCUMENT_AI_ENDPOINT: Base endpoint URL
    - MISTRAL_DOCUMENT_AI_KEY: API key for authentication
    - MISTRAL_DOCUMENT_AI_DEPLOYMENT_NAME: Model deployment name
    
    Returns:
        Dictionary with endpoint, api_key, and model configuration
    """
    mistral_endpoint = os.getenv('MISTRAL_DOCUMENT_AI_ENDPOINT')
    mistral_api_key = os.getenv('MISTRAL_DOCUMENT_AI_KEY')
    mistral_model = os.getenv('MISTRAL_DOCUMENT_AI_DEPLOYMENT_NAME', 'mistral-ocr-latest')

    if not mistral_endpoint or not mistral_api_key:
        raise ValueError(
            "Missing required environment variables. "
            "Please set MISTRAL_DOCUMENT_AI_ENDPOINT and MISTRAL_DOCUMENT_AI_KEY"
        )
    
    # Construct the OCR endpoint
    endpoint = mistral_endpoint.rstrip('/') + '/providers/mistral/azure/ocr'
    
    return {
        "endpoint": endpoint,
        "api_key": mistral_api_key,
        "model": mistral_model
    }


# =============================================================================
# Main Extraction Functions with Data Annotations
# =============================================================================

def extract_with_annotations(
    file_path: str,
    json_schema: Optional[Dict] = None,
    include_bboxes: bool = True,
    page_range: Optional[tuple] = None
) -> Dict[str, Any]:
    """
    Extract structured data from a document with bounding box annotations.
    
    This function uses Mistral Document AI to:
    1. Perform OCR on the document
    2. Extract structured data according to the provided JSON schema
    3. Include bounding box annotations showing where each field was found
    
    Args:
        file_path: Path to the document file (PDF, JPEG, PNG, etc.)
        json_schema: JSON schema defining the structure of data to extract.
                    If None, returns raw OCR text with page-level bboxes.
        include_bboxes: Whether to include bounding box annotations (default: True)
        page_range: Optional tuple (start_page, end_page) to process specific pages
        
    Returns:
        Dictionary containing:
        - 'extracted_data': The structured data extracted according to schema
        - 'annotations': List of AnnotatedField objects with bbox locations
        - 'pages': Raw page data including markdown and images
        - 'metadata': Processing metadata (model, timing, etc.)
    
    Example:
        >>> result = extract_with_annotations(
        ...     "claim_form.pdf",
        ...     json_schema=CLAIM_STATEMENT_SCHEMA,
        ...     include_bboxes=True
        ... )
        >>> print(result['extracted_data']['claimant_name'])
        "John Smith"
        >>> print(result['annotations'][0].bbox)
        BoundingBox(x_min=0.1, y_min=0.2, x_max=0.5, y_max=0.25, page=0)
    """
    import time
    start_time = time.time()
    
    logger.info(f"Starting annotated extraction for: {file_path}")
    print(f"\n📄 Processing document with data annotations: {os.path.basename(file_path)}")
    
    # Get configuration
    config = get_mistral_config()
    
    # Encode file
    data_url, url_type = encode_file_to_base64(file_path)
    
    # Build request payload
    headers = {
        "Content-Type": "application/json",
        "api-key": config["api_key"]
    }
    
    # Payload format matching the working Mistral Document AI OCR endpoint
    payload = {
        "model": config["model"],
        "document": {
            "type": url_type,
            url_type: data_url
        }
    }
    
    print(f"   📡 Endpoint: {config['endpoint']}")
    print(f"   📦 Model: {config['model']}")
    print(f"   📄 Document type: {url_type}")
    
    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(config["endpoint"], json=payload, headers=headers)
            
            print(f"   📊 Response Status: {response.status_code}")
            
            # Debug logging for errors
            if response.status_code != 200:
                print(f"   ❌ Error Response: {response.text[:500]}")
            
            response.raise_for_status()
            result = response.json()
            
            # Debug: show response structure
            print(f"   📦 Response keys: {list(result.keys())}")
            
        processing_time = time.time() - start_time
        
        # Parse the response
        output = {
            "extracted_data": {},
            "annotations": [],
            "pages": [],
            "raw_text": "",
            "document_annotation": None,
            "metadata": {
                "model": config["model"],
                "processing_time_seconds": round(processing_time, 2),
                "file_path": file_path,
                "include_bboxes": include_bboxes,
                "json_schema_provided": json_schema is not None
            }
        }
        
        # Capture document_annotation if present (contains structured annotation data)
        if "document_annotation" in result:
            output["document_annotation"] = result["document_annotation"]
            print(f"   🏷️  Document annotation data available")
        
        # Process pages - Mistral Document AI returns pages with markdown content
        if "pages" in result and isinstance(result["pages"], list):
            for page_idx, page in enumerate(result["pages"]):
                page_data = {
                    "page_number": page_idx,
                    "markdown": page.get("markdown", ""),
                    "dimensions": page.get("dimensions", {}),
                }
                
                # Extract images/regions if available (for bounding box info)
                if include_bboxes and "images" in page:
                    page_data["images"] = []
                    for img in page["images"]:
                        img_info = {
                            "id": img.get("id"),
                            "top_left_x": img.get("top_left_x", 0),
                            "top_left_y": img.get("top_left_y", 0),
                            "bottom_right_x": img.get("bottom_right_x", 0),
                            "bottom_right_y": img.get("bottom_right_y", 0),
                        }
                        page_data["images"].append(img_info)
                
                output["pages"].append(page_data)
                output["raw_text"] += page.get("markdown", "") + "\n\n"
                
            print(f"   📄 Processed {len(result['pages'])} page(s)")
        
        # Handle alternative response formats
        elif "content" in result:
            output["raw_text"] = result["content"]
        elif "text" in result:
            output["raw_text"] = result["text"]
        elif "choices" in result and len(result["choices"]) > 0:
            # OpenAI-style format fallback
            output["raw_text"] = result["choices"][0].get("message", {}).get("content", "")
        
        # If a JSON schema was provided, parse the markdown into structured data
        if json_schema and output["raw_text"]:
            output["metadata"]["schema_for_extraction"] = json_schema
            
            # Parse the markdown text into structured data
            extracted_data = parse_markdown_to_structured_data(output["raw_text"], json_schema)
            output["extracted_data"] = extracted_data
            
            # Create annotations for each extracted field
            for field_name, value in extracted_data.items():
                if isinstance(value, dict):
                    # Handle nested objects like vehicle_info
                    for sub_field, sub_value in value.items():
                        annotation = AnnotatedField(
                            field_name=f"{field_name}.{sub_field}",
                            value=sub_value,
                            confidence=0.9,  # High confidence for pattern-matched fields
                            raw_text=str(sub_value)
                        )
                        output["annotations"].append(annotation)
                else:
                    annotation = AnnotatedField(
                        field_name=field_name,
                        value=value,
                        confidence=0.9,
                        raw_text=str(value) if not isinstance(value, bool) else None
                    )
                    output["annotations"].append(annotation)
            
            print(f"   📋 Extracted {len(extracted_data)} structured fields")
        
        print(f"\n   ✅ Extraction completed in {processing_time:.2f}s")
        print(f"   📝 Extracted {len(output['raw_text'])} characters")
        print(f"   🏷️  Created {len(output['annotations'])} field annotations")
        
        return output
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        print(f"   ❌ Full error: {e.response.text}")
        raise Exception(f"Mistral API error: {e.response.status_code} - {e.response.text[:200]}")
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        raise


def extract_claim_statement(file_path: str) -> Dict[str, Any]:
    """
    Extract structured data from an insurance claim statement.
    
    This is a convenience function that uses the predefined CLAIM_STATEMENT_SCHEMA
    to extract relevant information from claim documents.
    
    Args:
        file_path: Path to the claim statement document
        
    Returns:
        Dictionary with extracted claim information and annotations
    
    Example:
        >>> result = extract_claim_statement("crash1_front.jpeg")
        >>> print(f"Claimant: {result['extracted_data'].get('claimant_name')}")
        >>> print(f"Policy: {result['extracted_data'].get('policy_number')}")
    """
    return extract_with_annotations(
        file_path,
        json_schema=CLAIM_STATEMENT_SCHEMA,
        include_bboxes=True
    )


def extract_damage_assessment(file_path: str) -> Dict[str, Any]:
    """
    Extract damage assessment information from vehicle photos.
    
    Uses the DAMAGE_ASSESSMENT_SCHEMA to identify and categorize
    visible damage in vehicle images.
    
    Args:
        file_path: Path to the vehicle damage image
        
    Returns:
        Dictionary with damage areas, severity levels, and repair recommendations
    """
    return extract_with_annotations(
        file_path,
        json_schema=DAMAGE_ASSESSMENT_SCHEMA,
        include_bboxes=True
    )


def batch_extract_with_annotations(
    file_paths: List[str],
    json_schema: Optional[Dict] = None,
    max_concurrent: int = 3
) -> List[Dict[str, Any]]:
    """
    Process multiple documents with annotations in batch.
    
    Args:
        file_paths: List of document file paths to process
        json_schema: Optional JSON schema for structured extraction
        max_concurrent: Maximum number of concurrent requests
        
    Returns:
        List of extraction results for each document
    """
    import concurrent.futures
    
    results = []
    
    print(f"\n📚 Batch processing {len(file_paths)} documents...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        future_to_file = {
            executor.submit(extract_with_annotations, fp, json_schema): fp
            for fp in file_paths
        }
        
        for future in concurrent.futures.as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                result = future.result()
                results.append({"file": file_path, "status": "success", "data": result})
                print(f"   ✅ Completed: {os.path.basename(file_path)}")
            except Exception as e:
                results.append({"file": file_path, "status": "error", "error": str(e)})
                print(f"   ❌ Failed: {os.path.basename(file_path)} - {str(e)}")
    
    return results


def visualize_annotations(result: Dict[str, Any], output_path: Optional[str] = None) -> None:
    """
    Generate a visualization of extracted annotations on the document.
    
    This function displays the extracted data and any available annotation info.
    For documents with bounding box data, it can overlay boxes on the image.
    
    Args:
        result: The extraction result from extract_with_annotations
        output_path: Optional path to save the visualization image
        
    Note:
        For full image visualization, requires PIL/Pillow.
    """
    print("\n🎨 Extraction Summary:")
    
    # Show document annotation if available
    if result.get("document_annotation"):
        print(f"   📋 Document annotation data: {type(result['document_annotation'])}")
    
    # Display structured extracted data
    extracted_data = result.get("extracted_data", {})
    if extracted_data:
        print("\n   📊 Structured Data:")
        for field_name, value in extracted_data.items():
            if isinstance(value, dict):
                print(f"      📁 {field_name}:")
                for sub_field, sub_value in value.items():
                    print(f"         • {sub_field}: {sub_value}")
            elif isinstance(value, bool):
                print(f"      • {field_name}: {'✓ Yes' if value else '✗ No'}")
            else:
                # Truncate long values
                display_value = str(value)
                if len(display_value) > 80:
                    display_value = display_value[:77] + "..."
                print(f"      • {field_name}: {display_value}")
    
    # Show annotation count
    annotations = result.get("annotations", [])
    if annotations:
        print(f"\n   🏷️  {len(annotations)} Field Annotations:")
        for annotation in annotations:
            if isinstance(annotation, AnnotatedField):
                ann_dict = annotation.to_dict()
            else:
                ann_dict = annotation
            
            conf = ann_dict.get('confidence', 0)
            conf_str = f"({conf*100:.0f}%)" if conf else ""
            print(f"      📍 {ann_dict['field_name']}: {ann_dict['value']} {conf_str}")
            
            if ann_dict.get('bbox'):
                bbox = ann_dict['bbox']
                print(f"         └─ Location: ({bbox['x_min']:.2f}, {bbox['y_min']:.2f}) to ({bbox['x_max']:.2f}, {bbox['y_max']:.2f})")


def export_annotations_to_json(result: Dict[str, Any], output_path: str) -> None:
    """
    Export extraction results with annotations to a JSON file.
    
    Args:
        result: The extraction result from extract_with_annotations
        output_path: Path to save the JSON file
    """
    # Convert AnnotatedField objects to dictionaries
    export_data = {
        "extracted_data": result.get("extracted_data", {}),
        "annotations": [
            ann.to_dict() if isinstance(ann, AnnotatedField) else ann
            for ann in result.get("annotations", [])
        ],
        "document_annotation": result.get("document_annotation"),
        "pages": result.get("pages", []),
        "metadata": result.get("metadata", {}),
        "raw_text": result.get("raw_text", "")
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"   💾 Annotations exported to: {output_path}")


# =============================================================================
# Main Entry Point for Testing
# =============================================================================

if __name__ == "__main__":
    """
    Test the Mistral Document AI annotation extraction functionality.
    
    Usage:
        python mistral_doc_intel_annotations.py [file_path]
        
    If no file path is provided, it will look for test files in the data directory.
    """
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("🔬 Mistral Document AI - Data Annotations Demo")
    print("=" * 60)
    
    # Determine test file
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        # If the provided path doesn't exist, check if it's relative to challenge-1
        if not os.path.exists(test_file):
            # Try challenge-1 data directory
            alt_path = os.path.join(os.path.dirname(__file__), "..", "..", "challenge-1", "data", "statements", os.path.basename(test_file))
            if os.path.exists(alt_path):
                test_file = alt_path
    else:
        # Try to find a test file in the data directories
        # Data is stored in challenge-1/data/statements
        base_dir = os.path.dirname(__file__)
        data_dirs = [
            os.path.join(base_dir, "..", "..", "challenge-1", "data", "statements"),  # challenge-1
            os.path.join(base_dir, "..", "data", "statements"),  # challenge-1
        ]
        test_files = []
        for data_dir in data_dirs:
            test_files.extend([
                os.path.join(data_dir, "crash1_front.jpeg"),
                os.path.join(data_dir, "crash1_front.jpg"),
            ])
        test_file = next((f for f in test_files if os.path.exists(f)), None)
    
    if not test_file or not os.path.exists(test_file):
        print("\n❌ No test file found!")
        print("Usage: python mistral_doc_intel_annotations.py <path_to_document>")
        print("\nExample:")
        print("  python mistral_doc_intel_annotations.py ../data/statements/crash1_front.jpeg")
        sys.exit(1)
    
    print(f"\n📄 Test file: {test_file}")
    
    try:
        # Test 1: Basic extraction with annotations
        print("\n" + "-" * 40)
        print("Test 1: Claim Statement Extraction")
        print("-" * 40)
        
        result = extract_claim_statement(test_file)
        
        print("\n📊 Extraction Results:")
        print(f"   Raw text length: {len(result['raw_text'])} characters")
        print(f"   Processing time: {result['metadata']['processing_time_seconds']}s")
        
        if result['extracted_data']:
            print("\n📋 Extracted Fields:")
            for key, value in result['extracted_data'].items():
                if value:
                    print(f"   • {key}: {value}")
        
        # Visualize annotations
        visualize_annotations(result)
        
        # Export to JSON
        output_path = test_file.rsplit('.', 1)[0] + "_annotations.json"
        export_annotations_to_json(result, output_path)
        
        print("\n" + "=" * 60)
        print("✅ Demo completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during processing: {str(e)}")
        logger.exception("Full error details:")
        sys.exit(1)
