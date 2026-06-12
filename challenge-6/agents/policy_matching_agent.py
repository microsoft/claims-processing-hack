#!/usr/bin/env python3
"""
Policy Matching Agent - Retrieves insurance policy documents from Azure AI Search
based on the policy number found in structured claim data.

Uses Azure AI Search (hybrid: keyword + vector + semantic) to find the matching
policy document, then GPT-4.1-mini to extract and summarize coverage details.

Usage:
    python policy_matching_agent.py <structured_claim.json>

Example:
    python policy_matching_agent.py ../sample_claims/crash1_structured.json
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

# Azure AI Search SDK
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ENDPOINT = os.environ.get("AI_FOUNDRY_PROJECT_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")
SEARCH_SERVICE_ENDPOINT = os.environ.get("SEARCH_SERVICE_ENDPOINT")
SEARCH_INDEX_NAME = os.environ.get("SEARCH_INDEX_NAME", "insurance-documents-index")

# Policy code to friendly name mapping (for validation)
KNOWN_POLICIES = {
    "LIAB-AUTO-001": "Liability Only Auto Insurance",
    "COMP-AUTO-001": "Comprehensive Auto Insurance",
    "COMM-AUTO-001": "Commercial Auto Insurance",
    "HV-AUTO-001": "High-Value Vehicle Insurance",
    "MOTO-001": "Motorcycle Insurance",
}


def search_policy_document(policy_number: str) -> str:
    """
    Search Azure AI Search for the policy document matching the given policy number.

    Args:
        policy_number: The policy code to search for (e.g., 'LIAB-AUTO-001')

    Returns:
        JSON string with the policy document content, or an error message
    """
    try:
        logger.info(f"Searching for policy: {policy_number}")

        if not SEARCH_SERVICE_ENDPOINT:
            return json.dumps({
                "status": "error",
                "error": "SEARCH_SERVICE_ENDPOINT not configured. Complete Challenge 1 first.",
                "policy_number": policy_number,
            })

        # Create search client using DefaultAzureCredential
        search_client = SearchClient(
            endpoint=SEARCH_SERVICE_ENDPOINT,
            index_name=SEARCH_INDEX_NAME,
            credential=DefaultAzureCredential(),
        )

        # Hybrid search: use the policy code as the primary query
        results = search_client.search(
            search_text=policy_number,
            top=3,
            query_type="semantic",
            semantic_configuration_name="default",
        )

        matched_docs = []
        for result in results:
            matched_docs.append({
                "score": result.get("@search.score", 0),
                "reranker_score": result.get("@search.reranker_score", 0),
                "content": result.get("content", result.get("chunk", "")),
                "title": result.get("title", ""),
                "source": result.get("source", result.get("filepath", "")),
            })

        if not matched_docs:
            return json.dumps({
                "status": "no_results",
                "error": f"No policy document found for '{policy_number}'. Ensure policies are indexed in AI Search.",
                "policy_number": policy_number,
            })

        logger.info(f"Found {len(matched_docs)} matching document(s) for {policy_number}")

        return json.dumps({
            "status": "success",
            "policy_number": policy_number,
            "documents": matched_docs,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Search error: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "policy_number": policy_number,
        })


def get_agent_instructions() -> str:
    """Return the system prompt for the policy matching agent."""
    return """You are an insurance policy analyst agent. Your job is to take a policy number from a structured insurance claim and retrieve the matching insurance policy document, then extract key coverage details.

**Your Task:**
Given a policy number and the retrieved policy document text, extract and return a structured JSON summary of the policy's coverage.

**JSON Output Structure:**
{
  "policy_match": {
    "policy_number": "The policy code (e.g., LIAB-AUTO-001)",
    "policy_name": "Human-readable policy name",
    "policy_type": "liability_only | comprehensive | commercial | high_value | motorcycle",
    "match_confidence": "high | medium | low"
  },
  "coverage_summary": {
    "covers_own_vehicle_collision": true/false,
    "covers_own_vehicle_comprehensive": true/false,
    "covers_liability_bodily_injury": true/false,
    "covers_liability_property_damage": true/false,
    "covers_medical_payments": true/false,
    "covers_uninsured_motorist": true/false,
    "covers_rental_car": true/false,
    "covers_roadside_assistance": true/false,
    "covers_towing": true/false
  },
  "limits": {
    "collision_limit": "Dollar amount or N/A",
    "comprehensive_limit": "Dollar amount or N/A",
    "bodily_injury_per_person": "Dollar amount",
    "bodily_injury_per_accident": "Dollar amount",
    "property_damage_per_accident": "Dollar amount",
    "medical_payments_per_person": "Dollar amount or N/A"
  },
  "deductibles": {
    "collision_deductible": "Dollar amount or N/A",
    "comprehensive_deductible": "Dollar amount or N/A"
  },
  "key_exclusions": [
    "List of important exclusions from the policy"
  ],
  "own_vehicle_damage_covered": true/false,
  "notes": "Any important observations about this policy's coverage"
}

**Processing Rules:**
1. Base your answer ONLY on the retrieved policy document text — do not invent coverage terms
2. If the policy does not mention a coverage type, mark it as false/N/A
3. Pay special attention to what is explicitly NOT covered (exclusions sections)
4. For liability-only policies, own_vehicle_damage_covered MUST be false
5. Return ONLY valid JSON, no additional commentary
6. Set match_confidence based on how clearly the policy code matches the document"""


def match_policy(claim_data: dict, project_client=None) -> dict:
    """
    Match a structured claim to its insurance policy and extract coverage details.

    Args:
        claim_data: Structured claim dictionary containing at least a policy_number field
        project_client: Optional existing AIProjectClient

    Returns:
        Dictionary with matched policy details and coverage summary
    """
    try:
        # Extract policy number from claim data
        policy_number = claim_data.get("policy_number", "")
        if not policy_number:
            # Try nested structures
            for key in ["structured_fields", "extracted_text"]:
                nested = claim_data.get(key, {})
                if isinstance(nested, dict):
                    policy_number = nested.get("policy_number", "")
                    if not policy_number:
                        refs = nested.get("reference_numbers", [])
                        if isinstance(refs, list):
                            for ref in refs:
                                if any(code in str(ref) for code in KNOWN_POLICIES):
                                    policy_number = ref
                                    break
                if policy_number:
                    break

        if not policy_number:
            return {
                "status": "error",
                "error": "No policy_number found in claim data",
                "claim_data_keys": list(claim_data.keys()),
            }

        logger.info(f"Matching policy: {policy_number}")

        # Step 1: Search for the policy document
        search_result_json = search_policy_document(policy_number)
        search_result = json.loads(search_result_json)

        if search_result.get("status") != "success":
            # If search fails, fall back to known policy mapping
            if policy_number in KNOWN_POLICIES:
                logger.info(f"Search unavailable, using known policy mapping for {policy_number}")
                return _fallback_policy_match(policy_number)
            return search_result

        # Step 2: Use GPT to extract structured coverage from the policy document
        policy_text = "\n\n".join(
            doc.get("content", "") for doc in search_result.get("documents", [])
        )

        should_close = False
        if project_client is None:
            project_client = AIProjectClient(
                endpoint=PROJECT_ENDPOINT,
                credential=DefaultAzureCredential(),
            )
            should_close = True

        try:
            agent = project_client.agents.create_version(
                agent_name="PolicyMatchingAgent",
                definition=PromptAgentDefinition(
                    model=MODEL_DEPLOYMENT_NAME,
                    instructions=get_agent_instructions(),
                    temperature=0.1,
                ),
            )

            logger.info(f"Created Policy Matching Agent: {agent.name} (version {agent.version})")

            openai_client = project_client.get_openai_client()

            user_query = f"""Analyze the following insurance policy document and extract structured coverage details.

**Policy Number from Claim:** {policy_number}

---POLICY DOCUMENT START---
{policy_text}
---POLICY DOCUMENT END---

Return the structured JSON coverage summary."""

            response = openai_client.responses.create(
                input=user_query,
                extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            )

            response_text = response.output_text.strip()
            if response_text.startswith("```"):
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start != -1 and end > start:
                    response_text = response_text[start:end]

            result = json.loads(response_text)
            result["status"] = "success"
            result["raw_policy_text_length"] = len(policy_text)
            result["timestamp"] = datetime.now().isoformat()
            return result

        finally:
            if should_close:
                project_client.close()

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse agent response as JSON: {e}")
        return {
            "status": "error",
            "error": f"JSON parsing failed: {e}",
            "raw_response": response_text if "response_text" in dir() else "No response",
        }
    except Exception as e:
        logger.error(f"Policy matching error: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


def _fallback_policy_match(policy_number: str) -> dict:
    """
    Provide a basic policy match when Azure AI Search is unavailable.
    Uses the known policy code mapping and hardcoded coverage summaries.
    """
    fallback_coverage = {
        "LIAB-AUTO-001": {
            "policy_match": {
                "policy_number": "LIAB-AUTO-001",
                "policy_name": "Liability Only Auto Insurance",
                "policy_type": "liability_only",
                "match_confidence": "high",
            },
            "coverage_summary": {
                "covers_own_vehicle_collision": False,
                "covers_own_vehicle_comprehensive": False,
                "covers_liability_bodily_injury": True,
                "covers_liability_property_damage": True,
                "covers_medical_payments": False,
                "covers_uninsured_motorist": False,
                "covers_rental_car": False,
                "covers_roadside_assistance": False,
                "covers_towing": False,
            },
            "limits": {
                "collision_limit": "N/A",
                "comprehensive_limit": "N/A",
                "bodily_injury_per_person": "$25,000",
                "bodily_injury_per_accident": "$50,000",
                "property_damage_per_accident": "$25,000",
                "medical_payments_per_person": "N/A",
            },
            "deductibles": {
                "collision_deductible": "N/A",
                "comprehensive_deductible": "N/A",
            },
            "key_exclusions": [
                "Collision damage to your vehicle",
                "Comprehensive damage (theft, vandalism, weather)",
                "Medical expenses for you or your passengers",
                "Damage while racing or in competitions",
                "Intentional damage caused by you",
                "Damage while using vehicle for business purposes",
                "Damage while driving under the influence",
            ],
            "own_vehicle_damage_covered": False,
            "notes": "Liability-only policy: covers only damage/injury you cause to OTHERS. Does NOT cover any damage to the policyholder's own vehicle.",
        },
        "COMM-AUTO-001": {
            "policy_match": {
                "policy_number": "COMM-AUTO-001",
                "policy_name": "Commercial Auto Insurance",
                "policy_type": "commercial",
                "match_confidence": "high",
            },
            "coverage_summary": {
                "covers_own_vehicle_collision": True,
                "covers_own_vehicle_comprehensive": True,
                "covers_liability_bodily_injury": True,
                "covers_liability_property_damage": True,
                "covers_medical_payments": True,
                "covers_uninsured_motorist": True,
                "covers_rental_car": False,
                "covers_roadside_assistance": False,
                "covers_towing": True,
            },
            "limits": {
                "collision_limit": "$50,000 per incident",
                "comprehensive_limit": "$50,000 per incident",
                "bodily_injury_per_person": "$100,000",
                "bodily_injury_per_accident": "$300,000",
                "property_damage_per_accident": "$100,000",
                "medical_payments_per_person": "$10,000",
            },
            "deductibles": {
                "collision_deductible": "$500",
                "comprehensive_deductible": "$250",
            },
            "key_exclusions": [
                "Racing or competitive driving events",
                "Personal use outside business operations",
                "Intentional damage",
                "Damage while driving under the influence",
            ],
            "own_vehicle_damage_covered": True,
            "notes": "Commercial auto policy with collision and comprehensive coverage for business vehicles.",
        },
        "COMP-AUTO-001": {
            "policy_match": {
                "policy_number": "COMP-AUTO-001",
                "policy_name": "Comprehensive Auto Insurance",
                "policy_type": "comprehensive",
                "match_confidence": "high",
            },
            "coverage_summary": {
                "covers_own_vehicle_collision": True,
                "covers_own_vehicle_comprehensive": True,
                "covers_liability_bodily_injury": True,
                "covers_liability_property_damage": True,
                "covers_medical_payments": True,
                "covers_uninsured_motorist": True,
                "covers_rental_car": True,
                "covers_roadside_assistance": True,
                "covers_towing": True,
            },
            "limits": {
                "collision_limit": "$50,000 per incident",
                "comprehensive_limit": "$50,000 per incident",
                "bodily_injury_per_person": "$100,000",
                "bodily_injury_per_accident": "$300,000",
                "property_damage_per_accident": "$100,000",
                "medical_payments_per_person": "$10,000",
            },
            "deductibles": {
                "collision_deductible": "$500",
                "comprehensive_deductible": "$250",
            },
            "key_exclusions": [
                "Racing or competitive driving events",
                "Commercial use of personal vehicles",
                "Intentional damage by the policyholder",
                "Wear and tear or mechanical breakdown",
                "Damage while driving under the influence",
            ],
            "own_vehicle_damage_covered": True,
            "notes": "Full coverage policy with collision, comprehensive, liability, medical, and uninsured motorist.",
        },
    }

    if policy_number in fallback_coverage:
        result = fallback_coverage[policy_number]
        result["status"] = "success"
        result["source"] = "fallback_mapping"
        result["timestamp"] = datetime.now().isoformat()
        return result

    return {
        "status": "error",
        "error": f"Unknown policy number: {policy_number}",
        "known_policies": list(KNOWN_POLICIES.keys()),
    }


def main():
    """CLI entry point for the policy matching agent."""
    if len(sys.argv) < 2:
        print("Usage: python policy_matching_agent.py <structured_claim.json>")
        print("\nProvide the path to a structured claim JSON file (output from Challenge 2)")
        sys.exit(1)

    input_path = sys.argv[1]

    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    # Load claim data
    with open(input_path, "r") as f:
        claim_data = json.load(f)

    logger.info(f"Loaded claim data from: {input_path}")

    # Run the policy matching agent
    result = match_policy(claim_data)

    # Output
    print("\n" + "=" * 60)
    print("POLICY MATCHING RESULT")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    print("=" * 60)

    # Save result
    output_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_policy_match.json")
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResult saved to: {output_path}")


if __name__ == "__main__":
    main()
