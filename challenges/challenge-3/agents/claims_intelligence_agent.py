#!/usr/bin/env python3
"""
Claims Intelligence Agent - Enterprise Edition

Combines Policy Matching + Coverage Validation into single decision agent.
Handles policy lookup, coverage analysis, and compliance checking.

Key Enterprise Features:
- Policy document caching
- Multi-factor coverage analysis
- Compliance rules engine
- Exception handling & escalation
- Detailed reasoning and audit trail
"""

import os
import json
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional
from functools import lru_cache

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

from enterprise_models import (
    ClaimProcessingState, PolicyInfo, CoverageDecision, ErrorInfo,
    SeverityLevel, ClaimStatus, StructuredClaim
)

load_dotenv(override=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ENDPOINT = os.environ.get("AI_FOUNDRY_PROJECT_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-5.4")

# Mock policy database - in production, this would be Azure AI Search
MOCK_POLICIES = {
    "LIAB-AUTO-001": {
        "policy_id": "liab-001",
        "policy_type": "Liability Only",
        "coverage_types": ["third_party_liability"],
        "limits": {"third_party_liability": 100000},
        "deductibles": {"third_party_liability": 500},
        "exclusions": ["own_vehicle_damage", "collision", "comprehensive"],
        "effective_date": "2026-01-01",
        "expiry_date": "2027-01-01"
    },
    "COMM-AUTO-001": {
        "policy_id": "comm-001",
        "policy_type": "Commercial Auto",
        "coverage_types": ["collision", "comprehensive", "liability"],
        "limits": {"collision": 50000, "comprehensive": 25000, "liability": 150000},
        "deductibles": {"collision": 1000, "comprehensive": 500, "liability": 250},
        "exclusions": [],
        "effective_date": "2026-01-01",
        "expiry_date": "2027-01-01"
    },
    "COMP-AUTO-001": {
        "policy_id": "comp-001",
        "policy_type": "Comprehensive Auto",
        "coverage_types": ["collision", "comprehensive", "liability"],
        "limits": {"collision": 35000, "comprehensive": 15000, "liability": 100000},
        "deductibles": {"collision": 750, "comprehensive": 250, "liability": 100},
        "exclusions": [],
        "effective_date": "2026-01-01",
        "expiry_date": "2027-01-01"
    }
}


class ClaimsIntelligenceAgent:
    """Enterprise claims decision making with policy matching and coverage validation"""
    
    def __init__(self):
        self.client = AIProjectClient.from_config(
            credential=DefaultAzureCredential()
        )
        self.model = MODEL_DEPLOYMENT_NAME
        self.policy_cache = {}
    
    def get_intelligence_instructions(self) -> str:
        """System prompt for intelligence agent"""
        return """You are an enterprise insurance claims adjudicator. Your role is to:
1. Analyze whether a claim is covered under the insurance policy
2. Determine the approved payment amount
3. Identify any exclusions or limitations that apply
4. Flag edge cases requiring escalation

**Decision Framework:**
- Compare claim type against policy coverage types
- Check if claim amount exceeds policy limits
- Calculate applicable deductibles
- Identify matching exclusions
- Assess risk factors

**Output JSON:**
{
  "is_covered": true|false,
  "coverage_percentage": 100,
  "applicable_deductible": 500.00,
  "approved_amount": 14500.00,
  "exclusions_matched": [],
  "reasoning": "Claim is covered under collision coverage with standard deductible.",
  "risk_flags": [],
  "confidence_score": 0.95,
  "requires_escalation": false,
  "escalation_reason": null
}"""
    
    def _get_policy(self, policy_number: str) -> Optional[PolicyInfo]:
        """Retrieve policy (cached)"""
        if policy_number in self.policy_cache:
            logger.info(f"Policy {policy_number} retrieved from cache")
            return self.policy_cache[policy_number]
        
        # Check mock database
        if policy_number in MOCK_POLICIES:
            policy_data = MOCK_POLICIES[policy_number]
            policy = PolicyInfo(
                policy_id=policy_data["policy_id"],
                policy_number=policy_number,
                policy_type=policy_data["policy_type"],
                coverage_types=policy_data["coverage_types"],
                limits=policy_data["limits"],
                deductibles=policy_data["deductibles"],
                exclusions=policy_data["exclusions"],
                effective_date=policy_data["effective_date"],
                expiry_date=policy_data["expiry_date"],
                retrieval_score=0.95
            )
            self.policy_cache[policy_number] = policy
            return policy
        
        logger.warning(f"Policy {policy_number} not found")
        return None
    
    def validate_coverage(self, state: ClaimProcessingState) -> ClaimProcessingState:
        """
        Validate claim coverage using policy matching and decision logic
        
        Args:
            state: Claim state with structured claim data
        
        Returns:
            Updated state with coverage decision
        """
        if not state.structured_claim:
            raise ValueError("Structured claim required for coverage validation")
        
        start_time = time.time()
        state.update_status(ClaimStatus.POLICY_RETRIEVED)
        
        try:
            claim = state.structured_claim
            
            # Step 1: Retrieve policy
            logger.info(f"[{state.claim_id}] Retrieving policy {claim.policy_number}")
            policy = self._get_policy(claim.policy_number)
            
            if not policy:
                raise Exception(f"Policy {claim.policy_number} not found")
            
            state.policy_info = policy
            state.add_audit_entry(
                agent_name="claims-intelligence-agent",
                action="retrieve_policy",
                status="completed",
                message=f"Retrieved policy {policy.policy_type}",
                metadata={"retrieval_score": policy.retrieval_score}
            )
            
            # Step 2: Run coverage decision
            logger.info(f"[{state.claim_id}] Validating coverage")
            decision_prompt = self._build_decision_prompt(claim, policy)
            
            agent = PromptAgentDefinition(
                name="coverage-decision-agent",
                model=self.model,
                instructions=self.get_intelligence_instructions()
            )
            
            result = self.client.agents.run_sync(
                agent=agent,
                user_message=decision_prompt
            )
            
            response_text = result.messages[-1].content[0].text
            decision_json = json.loads(response_text)
            
            # Extract decision
            state.coverage_decision = CoverageDecision(
                is_covered=decision_json.get("is_covered", False),
                coverage_percentage=decision_json.get("coverage_percentage", 0),
                applicable_deductible=float(decision_json.get("applicable_deductible", 0)),
                approved_amount=float(decision_json.get("approved_amount", 0)),
                exclusions_matched=decision_json.get("exclusions_matched", []),
                reasoning=decision_json.get("reasoning", ""),
                risk_flags=decision_json.get("risk_flags", []),
                confidence_score=decision_json.get("confidence_score", 0.85)
            )
            
            # Check for escalation flags
            if decision_json.get("requires_escalation", False):
                state.update_status(ClaimStatus.ESCALATED)
                state.add_error(ErrorInfo(
                    error_code="ESCALATION_REQUIRED",
                    error_message=decision_json.get("escalation_reason", "Manual review needed"),
                    severity=SeverityLevel.WARN,
                    retry_eligible=False,
                    recommendation="Escalate to claims adjuster for manual review",
                    agent_name="claims-intelligence-agent"
                ))
            else:
                state.update_status(
                    ClaimStatus.APPROVED if state.coverage_decision.is_covered 
                    else ClaimStatus.DENIED
                )
            
            state.add_audit_entry(
                agent_name="claims-intelligence-agent",
                action="validate_coverage",
                status="completed",
                message=f"Coverage decision: {'APPROVED' if state.coverage_decision.is_covered else 'DENIED'}",
                metadata={
                    "approved_amount": state.coverage_decision.approved_amount,
                    "confidence_score": state.coverage_decision.confidence_score,
                    "risk_flags": state.coverage_decision.risk_flags
                }
            )
            
            state.intelligence_duration_ms = (time.time() - start_time) * 1000
            logger.info(f"[{state.claim_id}] Coverage validation completed in {state.intelligence_duration_ms:.0f}ms")
            
            return state
            
        except Exception as e:
            logger.error(f"[{state.claim_id}] Coverage validation failed: {str(e)}")
            state.add_error(ErrorInfo(
                error_code="COVERAGE_VALIDATION_FAILED",
                error_message=str(e),
                severity=SeverityLevel.ERROR,
                retry_eligible=False,
                recommendation="Manual review required",
                agent_name="claims-intelligence-agent"
            ))
            state.update_status(ClaimStatus.COVERAGE_VALIDATION_FAILED)
            raise
    
    def _build_decision_prompt(self, claim: StructuredClaim, 
                              policy: PolicyInfo) -> str:
        """Build contextualized decision prompt"""
        return f"""
**CLAIM INFORMATION:**
- Policy Number: {claim.policy_number}
- Claim Amount: ${claim.claim_amount:,.2f}
- Damage Description: {claim.damage_description}
- Incident Date: {claim.incident_date}
- Claim Type: {claim.claim_type}
- Vehicle: {claim.vehicle_info}
- Extraction Confidence: {claim.extraction_confidence * 100:.0f}%

**POLICY INFORMATION:**
- Policy Type: {policy.policy_type}
- Coverage Types: {', '.join(policy.coverage_types)}
- Limits: {json.dumps(policy.limits)}
- Deductibles: {json.dumps(policy.deductibles)}
- Exclusions: {', '.join(policy.exclusions) if policy.exclusions else 'None'}

Determine if this claim is covered under the policy and calculate the approved payment amount.
Consider the claim type against policy coverage types, check limits, apply deductible, and identify any exclusions."""
