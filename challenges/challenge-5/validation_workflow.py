#!/usr/bin/env python3
"""
Policy Validation Workflow - Orchestrates the Policy Matching and Coverage
Validation agents to determine whether insurance claims are covered.

Can process individual claims or batch-process all sample claims, with optional
evaluation against ground truth.

Usage:
    python validation_workflow.py <structured_claim.json>
    python validation_workflow.py --all
    python validation_workflow.py --all --evaluate

Example:
    python validation_workflow.py sample_claims/crash1_structured.json
    python validation_workflow.py --all --evaluate
"""
import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Azure AI Foundry SDK
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Import agents
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))
from policy_matching_agent import match_policy
from coverage_validation_agent import validate_coverage

# Load environment
load_dotenv(override=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ENDPOINT = os.environ.get("AI_FOUNDRY_PROJECT_ENDPOINT")
SAMPLE_CLAIMS_DIR = os.path.join(os.path.dirname(__file__), "sample_claims")
GROUND_TRUTH_PATH = os.path.join(os.path.dirname(__file__), "coverage_ground_truth.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


async def validate_claim_coverage(claim_path: str) -> dict:
    """
    Full validation workflow for a single claim.

    Steps:
      1. Load structured claim data
      2. Policy Matching Agent → Retrieve and parse the matching policy
      3. Coverage Validation Agent → Determine coverage based on claim + policy
      4. Return complete coverage determination report

    Args:
        claim_path: Path to structured claim JSON file

    Returns:
        Coverage determination dictionary
    """
    logger.info(f"Starting coverage validation workflow for: {claim_path}")

    # Step 1: Load claim data
    if not os.path.exists(claim_path):
        return {"error": f"File not found: {claim_path}"}

    with open(claim_path, "r") as f:
        claim_data = json.load(f)

    logger.info(f"Loaded claim data ({len(claim_data)} fields)")

    # Create a shared project client for both agents
    with AIProjectClient(
        endpoint=ENDPOINT,
        credential=DefaultAzureCredential(),
    ) as project_client:

        # Step 2: Policy Matching Agent
        logger.info("Step 1/2: Running Policy Matching Agent...")
        policy_result = match_policy(claim_data, project_client=project_client)

        if policy_result.get("status") == "error":
            logger.error(f"Policy matching failed: {policy_result.get('error')}")
            return {
                "error": "Policy matching failed",
                "details": policy_result,
                "claim_file": claim_path,
            }

        policy_name = policy_result.get("policy_match", {}).get("policy_name", "Unknown")
        logger.info(f"Matched policy: {policy_name}")

        # Step 3: Coverage Validation Agent
        logger.info("Step 2/2: Running Coverage Validation Agent...")
        validation_result = validate_coverage(
            claim_data,
            policy_data=policy_result,
            project_client=project_client,
        )

    # Step 4: Build the final report
    report = {
        "claim_file": os.path.basename(claim_path),
        "policy_match": policy_result.get("policy_match", {}),
        "coverage_determination": {
            "decision": validation_result.get("coverage_decision", "UNKNOWN"),
            "applicable_coverage": validation_result.get("applicable_coverage", ""),
            "deductible": validation_result.get("deductible", "N/A"),
            "coverage_limit": validation_result.get("coverage_limit", "N/A"),
            "reasoning": validation_result.get("reasoning", ""),
            "exclusions_triggered": validation_result.get("exclusions_triggered", []),
            "recommendations": validation_result.get("recommendations", ""),
        },
        "full_policy_result": policy_result,
        "full_validation_result": validation_result,
        "workflow_timestamp": datetime.now().isoformat(),
    }

    decision = report["coverage_determination"]["decision"]
    icon = {"APPROVED": "✅", "DENIED": "❌", "PARTIAL_COVERAGE": "⚠️"}.get(decision, "❓")
    logger.info(f"{icon} Coverage decision for {os.path.basename(claim_path)}: {decision}")

    return report


async def process_all_claims() -> list:
    """Process all sample claims in the sample_claims directory."""
    if not os.path.exists(SAMPLE_CLAIMS_DIR):
        logger.error(f"Sample claims directory not found: {SAMPLE_CLAIMS_DIR}")
        return []

    claim_files = sorted(
        f for f in os.listdir(SAMPLE_CLAIMS_DIR)
        if f.endswith(".json")
    )

    if not claim_files:
        logger.error("No JSON claim files found in sample_claims/")
        return []

    logger.info(f"Processing {len(claim_files)} claims...")

    results = []
    for claim_file in claim_files:
        claim_path = os.path.join(SAMPLE_CLAIMS_DIR, claim_file)
        result = await validate_claim_coverage(claim_path)
        results.append(result)

    return results


def evaluate_results(results: list) -> dict:
    """Compare validation results against ground truth."""
    if not os.path.exists(GROUND_TRUTH_PATH):
        logger.error(f"Ground truth file not found: {GROUND_TRUTH_PATH}")
        return {"error": "Ground truth file not found"}

    with open(GROUND_TRUTH_PATH, "r") as f:
        ground_truth = json.load(f)

    evaluation = {
        "total_claims": len(results),
        "correct": 0,
        "incorrect": 0,
        "errors": 0,
        "details": [],
    }

    for result in results:
        claim_file = result.get("claim_file", "")
        # Extract crash ID from filename (e.g., "crash1_structured.json" -> "crash1")
        crash_id = claim_file.split("_")[0] if "_" in claim_file else claim_file.replace(".json", "")

        gt = ground_truth.get(crash_id, {})
        if not gt:
            evaluation["errors"] += 1
            evaluation["details"].append({
                "claim": crash_id,
                "status": "NO_GROUND_TRUTH",
                "message": f"No ground truth entry for {crash_id}",
            })
            continue

        actual_decision = result.get("coverage_determination", {}).get("decision", "UNKNOWN")
        expected_decision = gt.get("expected_decision", "UNKNOWN")

        is_correct = actual_decision == expected_decision

        if is_correct:
            evaluation["correct"] += 1
        else:
            evaluation["incorrect"] += 1

        evaluation["details"].append({
            "claim": crash_id,
            "expected": expected_decision,
            "actual": actual_decision,
            "correct": is_correct,
            "expected_reason": gt.get("reasoning_summary", ""),
            "actual_reason": result.get("coverage_determination", {}).get("reasoning", ""),
        })

    evaluated = evaluation["correct"] + evaluation["incorrect"]
    evaluation["accuracy"] = (
        evaluation["correct"] / evaluated if evaluated > 0 else 0
    )

    return evaluation


async def main():
    """CLI entry point."""
    args = sys.argv[1:]

    if not args:
        print("Usage:")
        print("  python validation_workflow.py <structured_claim.json>")
        print("  python validation_workflow.py --all")
        print("  python validation_workflow.py --all --evaluate")
        sys.exit(1)

    process_all = "--all" in args
    evaluate = "--evaluate" in args

    os.makedirs(RESULTS_DIR, exist_ok=True)

    if process_all:
        # Process all sample claims
        results = await process_all_claims()

        if not results:
            print("No claims processed.")
            sys.exit(1)

        # Print summary
        print("\n" + "=" * 70)
        print("  COVERAGE VALIDATION SUMMARY")
        print("=" * 70)
        for r in results:
            claim = r.get("claim_file", "unknown")
            decision = r.get("coverage_determination", {}).get("decision", "ERROR")
            policy = r.get("policy_match", {}).get("policy_name", "Unknown")
            icon = {"APPROVED": "✅", "DENIED": "❌", "PARTIAL_COVERAGE": "⚠️"}.get(decision, "❓")
            print(f"  {icon} {claim:<35} {decision:<20} ({policy})")
        print("=" * 70)

        # Save all results
        output_path = os.path.join(RESULTS_DIR, "all_validations.json")
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nAll results saved to: {output_path}")

        # Evaluate if requested
        if evaluate:
            print("\n" + "=" * 70)
            print("  EVALUATION AGAINST GROUND TRUTH")
            print("=" * 70)
            eval_result = evaluate_results(results)

            for detail in eval_result.get("details", []):
                status = "✅" if detail.get("correct") else "❌"
                print(f"  {status} {detail['claim']}: expected={detail.get('expected', '?')}, actual={detail.get('actual', '?')}")

            accuracy = eval_result.get("accuracy", 0)
            correct = eval_result.get("correct", 0)
            total = eval_result.get("total_claims", 0)
            print(f"\n  Accuracy: {correct}/{total} ({accuracy:.0%})")
            print("=" * 70)

            eval_path = os.path.join(RESULTS_DIR, "evaluation.json")
            with open(eval_path, "w") as f:
                json.dump(eval_result, f, indent=2)
            print(f"\nEvaluation saved to: {eval_path}")

    else:
        # Process a single claim
        claim_path = [a for a in args if not a.startswith("--")][0]
        result = await validate_claim_coverage(claim_path)

        decision = result.get("coverage_determination", {}).get("decision", "ERROR")
        icon = {"APPROVED": "✅", "DENIED": "❌", "PARTIAL_COVERAGE": "⚠️"}.get(decision, "❓")

        print("\n" + "=" * 60)
        print(f"  {icon} COVERAGE DETERMINATION: {decision}")
        print("=" * 60)
        print(json.dumps(result, indent=2))
        print("=" * 60)

        # Save result
        base_name = os.path.splitext(os.path.basename(claim_path))[0]
        output_path = os.path.join(RESULTS_DIR, f"{base_name}_validation.json")
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nResult saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
