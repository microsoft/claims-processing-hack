#!/usr/bin/env python3
"""
Enterprise Claims Orchestrator

Coordinates the two-agent workflow with proper error handling, 
state management, and observability.

Usage:
    python orchestrator_enterprise.py <image_path>
    
Example:
    python orchestrator_enterprise.py ../challenge-3/ocr_results/crash1_front.png
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from enterprise_models import ClaimProcessingState
from claims_intake_agent import ClaimsIntakeAgent
from claims_intelligence_agent import ClaimsIntelligenceAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class ClaimsOrchestrator:
    """Orchestrates 2-agent claims processing pipeline"""
    
    def __init__(self):
        self.intake_agent = ClaimsIntakeAgent()
        self.intelligence_agent = ClaimsIntelligenceAgent()
    
    def process_claim(self, image_path: str, 
                      customer_segment: str = "standard",
                      region: str = "US-EAST") -> ClaimProcessingState:
        """
        End-to-end claims processing
        
        Args:
            image_path: Path to claim image
            customer_segment: Customer classification
            region: Geographic region
        
        Returns:
            Complete claim processing state with audit trail
        """
        # Initialize state
        state = ClaimProcessingState(
            image_path=image_path,
            customer_segment=customer_segment,
            region=region
        )
        
        logger.info(f"========================================")
        logger.info(f"Starting claims processing: {state.claim_id}")
        logger.info(f"Image: {image_path}")
        logger.info(f"Customer Segment: {customer_segment}")
        logger.info(f"========================================")
        
        try:
            # Phase 1: Claims Intake
            logger.info(f"\n📋 PHASE 1: Claims Intake")
            logger.info(f"  Processing image with OCR and structuring...")
            
            state = self.intake_agent.process_claim_image(state, image_path)
            
            if state.structured_claim is None:
                raise Exception("Intake agent failed to extract structured claim")
            
            logger.info(f"✅ Intake completed")
            logger.info(f"  - Policy: {state.structured_claim.policy_number}")
            logger.info(f"  - Claim Amount: ${state.structured_claim.claim_amount:,.2f}")
            logger.info(f"  - Confidence: {state.structured_claim.extraction_confidence * 100:.0f}%")
            
            # Phase 2: Claims Intelligence (Policy + Coverage)
            logger.info(f"\n🧠 PHASE 2: Claims Intelligence")
            logger.info(f"  Retrieving policy and validating coverage...")
            
            state = self.intelligence_agent.validate_coverage(state)
            
            logger.info(f"✅ Coverage validation completed")
            logger.info(f"  - Status: {state.status.value}")
            logger.info(f"  - Covered: {state.coverage_decision.is_covered if state.coverage_decision else 'N/A'}")
            
            if state.coverage_decision:
                logger.info(f"  - Approved Amount: ${state.coverage_decision.approved_amount:,.2f}")
                logger.info(f"  - Deductible: ${state.coverage_decision.applicable_deductible:,.2f}")
            
            # Summary
            logger.info(f"\n📊 PROCESSING SUMMARY")
            logger.info(f"  - Claim ID: {state.claim_id}")
            logger.info(f"  - Status: {state.status.value.upper()}")
            logger.info(f"  - Intake Duration: {state.intake_duration_ms:.0f}ms")
            logger.info(f"  - Intelligence Duration: {state.intelligence_duration_ms:.0f}ms")
            logger.info(f"  - Total Duration: {state.intake_duration_ms + state.intelligence_duration_ms:.0f}ms")
            logger.info(f"  - Audit Entries: {len(state.audit_trail)}")
            logger.info(f"  - Errors: {len(state.errors)}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Claims processing failed: {str(e)}")
            logger.error(f"  Claim Status: {state.status.value}")
            logger.error(f"  Errors: {[e.error_code for e in state.errors]}")
            raise
    
    def process_batch(self, image_paths: list[str]) -> list[ClaimProcessingState]:
        """Process multiple claims"""
        states = []
        results_summary = {
            "total": len(image_paths),
            "successful": 0,
            "failed": 0,
            "approved": 0,
            "denied": 0,
            "escalated": 0
        }
        
        for idx, image_path in enumerate(image_paths, 1):
            logger.info(f"\n\n{'='*60}")
            logger.info(f"Processing claim {idx}/{len(image_paths)}")
            logger.info(f"{'='*60}")
            
            try:
                state = self.process_claim(image_path)
                states.append(state)
                results_summary["successful"] += 1
                
                # Count by status
                if state.status.value == "approved":
                    results_summary["approved"] += 1
                elif state.status.value == "denied":
                    results_summary["denied"] += 1
                elif state.status.value == "escalated":
                    results_summary["escalated"] += 1
                
                # Export state for audit
                output_path = f"claim_{state.claim_id}_audit.json"
                with open(output_path, 'w') as f:
                    f.write(state.to_json())
                logger.info(f"\n📁 Audit trail exported to: {output_path}")
                
            except Exception as e:
                logger.error(f"❌ Failed to process {image_path}: {str(e)}")
                results_summary["failed"] += 1
        
        # Batch summary
        logger.info(f"\n\n{'='*60}")
        logger.info(f"BATCH PROCESSING COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total Claims: {results_summary['total']}")
        logger.info(f"Successful: {results_summary['successful']}")
        logger.info(f"Failed: {results_summary['failed']}")
        logger.info(f"Approved: {results_summary['approved']}")
        logger.info(f"Denied: {results_summary['denied']}")
        logger.info(f"Escalated: {results_summary['escalated']}")
        
        return states


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python orchestrator_enterprise.py <image_path> [image_path2] ...")
        print("\nExample:")
        print("  python orchestrator_enterprise.py ../challenge-3/ocr_results/crash1_front.png")
        sys.exit(1)
    
    image_paths = sys.argv[1:]
    
    # Validate files exist
    for image_path in image_paths:
        if not Path(image_path).exists():
            logger.error(f"Image not found: {image_path}")
            sys.exit(1)
    
    # Process claims
    orchestrator = ClaimsOrchestrator()
    
    try:
        if len(image_paths) == 1:
            state = orchestrator.process_claim(image_paths[0])
            print("\n" + state.to_json())
        else:
            states = orchestrator.process_batch(image_paths)
            print(f"\nProcessed {len(states)} claims successfully")
    
    except Exception as e:
        logger.error(f"Orchestrator failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
