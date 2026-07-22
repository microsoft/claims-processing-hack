#!/usr/bin/env python3
"""
Coverage Validation Agent - Determines whether a claim is covered by the matched policy.

Takes structured claim data and matched policy details, then produces a coverage
determination with reasoning, applicable deductibles, and exclusion analysis.

Usage:
    python coverage_validation_agent.py <structured_claim.json>

Example:
    python coverage_validation_agent.py ../sample_claims/crash1_structured.json
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

# Import the policy matching agent
sys.path.insert(0, os.path.dirname(__file__))
from policy_matching_agent import match_policy

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ENDPOINT = os.environ.get("AI_FOUNDRY_PROJECT_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")


def get_agent_instructions() -> str:
    """Return the system prompt for the coverage validation agent."""
    return """You are an insurance coverage validation specialist. Your job is to determine whether an insurance claim is covered by the policyholder's insurance policy.

**Your Task:**
Given structured claim data and the matched policy's coverage details, produce a coverage determination.

**JSON Output Structure:**
{
  "coverage_decision": "APPROVED | DENIED | PARTIAL_COVERAGE",
  "policy_type": "Human-readable policy name",
  "policy_number": "Policy code",
  "applicable_coverage": "Which coverage section applies (or 'None' if denied)",
  "deductible": "Dollar amount the policyholder must pay, or 'N/A'",
  "coverage_limit": "Maximum payout for this type of claim, or 'N/A'",
  "reasoning": "Detailed explanation of why the claim is approved or denied, referencing specific policy sections",
  "exclusions_checked": ["List of exclusions that were evaluated"],
  "exclusions_triggered": ["List of exclusions that apply to deny or limit coverage"],
  "recommendations": "Next steps for the claimant or adjuster",
  "confidence": "high | medium | low"
}

**Decision Rules:**
1. **APPROVED**: The claim type is explicitly covered by the policy, no exclusions apply, and the claim amount appears within coverage limits
2. **DENIED**: The policy explicitly does not cover this type of claim (e.g., liability-only policy for own-vehicle damage), or an exclusion applies
3. **PARTIAL_COVERAGE**: The claim is partially covered — some aspects are covered but others are excluded, or the claim likely exceeds coverage limits

**Critical Validation Logic:**
- If the policy is liability-only AND the claim is for damage to the policyholder's OWN vehicle → DENIED
- If the policy does not include collision coverage AND the claim is for collision damage to own vehicle → DENIED
- If the claim involves business use AND the policy excludes commercial use → DENIED
- If the claim involves racing, DUI, or intentional damage → DENIED regardless of policy type
- If the policy covers the claim type but the estimated damage may exceed limits → PARTIAL_COVERAGE

**Processing Rules:**
1. Base your decision ONLY on the policy coverage details provided — do not assume coverage exists if not stated
2. Always explain your reasoning with specific references to coverage types and exclusions
3. For denied claims, clearly state WHICH section or exclusion causes the denial
4. Return ONLY valid JSON, no additional commentary
5. Be conservative — when uncertain, note the uncertainty in recommendations"""


def validate_coverage(claim_data: dict, policy_data: dict = None, project_client=None) -> dict:
    """
    Validate whether a claim is covered by the matched policy.

    Args:
        claim_data: Structured claim dictionary
        policy_data: Optional pre-fetched policy match result. If None, will run policy matching first.
        project_client: Optional existing AIProjectClient

    Returns:
        Coverage determination dictionary
    """
    try:
        # Step 1: Get the policy match if not provided
        if policy_data is None:
            logger.info("No policy data provided, running policy matching agent first...")
            policy_data = match_policy(claim_data, project_client=project_client)

        if policy_data.get("status") == "error":
            return {
                "coverage_decision": "ERROR",
                "error": f"Policy matching failed: {policy_data.get('error')}",
                "reasoning": "Cannot determine coverage without a matched policy.",
            }

        # Step 2: Build context for the validation agent
        claim_summary = _extract_claim_summary(claim_data)

        # Step 3: Use GPT to make the coverage determination
        should_close = False
        if project_client is None:
            project_client = AIProjectClient(
                endpoint=PROJECT_ENDPOINT,
                credential=DefaultAzureCredential(),
            )
            should_close = True

        try:
            agent = project_client.agents.create_version(
                agent_name="CoverageValidationAgent",
                definition=PromptAgentDefinition(
                    model=MODEL_DEPLOYMENT_NAME,
                    instructions=get_agent_instructions(),
                    temperature=0.1,
                ),
            )

            logger.info(f"Created Coverage Validation Agent: {agent.name} (version {agent.version})")

            openai_client = project_client.get_openai_client()

            user_query = f"""Determine whether the following insurance claim is covered by the policyholder's insurance policy.

**CLAIM DATA:**
{json.dumps(claim_summary, indent=2)}

**MATCHED POLICY COVERAGE:**
{json.dumps(policy_data, indent=2)}

Analyze the claim against the policy coverage and produce the coverage determination JSON."""

            response = openai_client.responses.create(
                input=user_query,
                extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
            )

            response_text = response.output_text.strip()
            if response_text.startswith("```"):
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start != -1 and end > start:
                    response_text = response_text[start:end]

            result = json.loads(response_text)
            result["status"] = "success"
            result["timestamp"] = datetime.now().isoformat()
            result["claim_summary"] = claim_summary
            return result

        finally:
            if should_close:
                project_client.close()

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse agent response as JSON: {e}")
        return {
            "coverage_decision": "ERROR",
            "error": f"JSON parsing failed: {e}",
            "raw_response": response_text if "response_text" in dir() else "No response",
        }
    except Exception as e:
        logger.error(f"Coverage validation error: {e}")
        return {
            "coverage_decision": "ERROR",
            "error": str(e),
        }


def _extract_claim_summary(claim_data: dict) -> dict:
    """
    Extract the key fields from structured claim data into a concise summary
    for the validation agent.
    """
    summary = {}

    # Direct fields (from ground truth format)
    direct_fields = [
        "policy_number", "policy_holder_name", "vehicle_year_make_model",
        "vehicle_color", "vehicle_vin", "incident_date", "incident_time",
        "incident_location", "incident_description", "damage_description",
        "claim_request", "weather_conditions",
    ]
    for field in direct_fields:
        if field in claim_data:
            summary[field] = claim_data[field]

    # Try nested structured_fields (from JSON structuring agent output)
    structured = claim_data.get("extracted_text", {}).get("structured_fields", {})
    if structured:
        summary["extracted_names"] = structured.get("names", [])
        summary["extracted_dates"] = structured.get("dates", [])
        summary["extracted_references"] = structured.get("reference_numbers", [])

    # Try vehicle_info (from JSON structuring agent output)
    vehicle_info = claim_data.get("vehicle_info", {})
    if vehicle_info:
        summary["vehicle_info"] = vehicle_info

    # Try damage_assessment
    damage = claim_data.get("damage_assessment", claim_data.get("front_specific", claim_data.get("rear_specific", {})))
    if damage:
        summary["damage_assessment"] = damage

    # Incident info
    incident = claim_data.get("incident_details", claim_data.get("incident_info", {}))
    if incident:
        summary["incident_details"] = incident

    # If summary is still sparse, include all top-level string/list fields
    if len(summary) < 3:
        for key, value in claim_data.items():
            if isinstance(value, (str, list)) and key not in ("metadata", "text_blocks"):
                summary[key] = value

    return summary


def main():
    """CLI entry point for the coverage validation agent."""
    if len(sys.argv) < 2:
        print("Usage: python coverage_validation_agent.py <structured_claim.json>")
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

    # Run the coverage validation agent (will also run policy matching)
    result = validate_coverage(claim_data)

    # Output
    decision = result.get("coverage_decision", "UNKNOWN")
    icon = {"APPROVED": "✅", "DENIED": "❌", "PARTIAL_COVERAGE": "⚠️"}.get(decision, "❓")

    print("\n" + "=" * 60)
    print(f"  {icon} COVERAGE DETERMINATION: {decision}")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    print("=" * 60)

    # Save result
    output_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_coverage_validation.json")
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResult saved to: {output_path}")


if __name__ == "__main__":
    main()
