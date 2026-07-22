#!/usr/bin/env python3
"""
Enterprise State Models and Data Structures

Provides strongly-typed models for claims processing workflow with audit trails,
observability hooks, and compliance tracking.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4
import json


class ClaimStatus(str, Enum):
    """Claim processing status"""
    INTAKE_STARTED = "intake_started"
    INTAKE_COMPLETED = "intake_completed"
    INTAKE_FAILED = "intake_failed"
    POLICY_RETRIEVED = "policy_retrieved"
    POLICY_RETRIEVAL_FAILED = "policy_retrieval_failed"
    COVERAGE_VALIDATED = "coverage_validated"
    COVERAGE_VALIDATION_FAILED = "coverage_validation_failed"
    APPROVED = "approved"
    DENIED = "denied"
    ESCALATED = "escalated"


class SeverityLevel(str, Enum):
    """Error/Alert severity levels"""
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """Immutable audit trail entry"""
    timestamp: datetime
    agent_name: str
    action: str
    status: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent_name": self.agent_name,
            "action": self.action,
            "status": self.status,
            "message": self.message,
            "metadata": self.metadata
        }


@dataclass
class ErrorInfo:
    """Structured error information"""
    error_code: str
    error_message: str
    severity: SeverityLevel
    retry_eligible: bool
    recommendation: str
    agent_name: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self):
        return {
            "error_code": self.error_code,
            "error_message": self.error_message,
            "severity": self.severity.value,
            "retry_eligible": self.retry_eligible,
            "recommendation": self.recommendation,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class OCRResult:
    """OCR processing result with confidence scores"""
    raw_text: str
    confidence_score: float
    image_quality: str
    processing_time_ms: float
    fields_detected: Dict[str, float]
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self):
        return asdict(self)


@dataclass
class StructuredClaim:
    """Structured claim data"""
    policy_number: str
    claim_amount: float
    damage_description: str
    incident_date: str
    vehicle_info: Dict[str, str]
    claim_type: str
    extraction_confidence: float
    
    def to_dict(self):
        return asdict(self)


@dataclass
class PolicyInfo:
    """Retrieved policy information"""
    policy_id: str
    policy_number: str
    policy_type: str
    coverage_types: List[str]
    limits: Dict[str, float]
    deductibles: Dict[str, float]
    exclusions: List[str]
    effective_date: str
    expiry_date: str
    retrieval_score: float
    
    def to_dict(self):
        return asdict(self)


@dataclass
class CoverageDecision:
    """Coverage determination result"""
    is_covered: bool
    coverage_percentage: float
    applicable_deductible: float
    approved_amount: float
    exclusions_matched: List[str]
    reasoning: str
    risk_flags: List[str] = field(default_factory=list)
    confidence_score: float = 0.95
    
    def to_dict(self):
        return asdict(self)


@dataclass
class ClaimProcessingState:
    """Complete claim processing state with audit trail"""
    claim_id: str = field(default_factory=lambda: str(uuid4()))
    version: int = 1
    status: ClaimStatus = ClaimStatus.INTAKE_STARTED
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    image_path: Optional[str] = None
    customer_segment: str = "standard"
    region: str = "US-EAST"
    
    ocr_result: Optional[OCRResult] = None
    structured_claim: Optional[StructuredClaim] = None
    policy_info: Optional[PolicyInfo] = None
    coverage_decision: Optional[CoverageDecision] = None
    
    audit_trail: List[AuditEntry] = field(default_factory=list)
    errors: List[ErrorInfo] = field(default_factory=list)
    
    intake_duration_ms: float = 0.0
    intelligence_duration_ms: float = 0.0
    total_tokens_used: int = 0
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_audit_entry(self, agent_name: str, action: str, status: str, 
                       message: str, metadata: Optional[Dict] = None):
        """Add audit trail entry"""
        self.audit_trail.append(AuditEntry(
            timestamp=datetime.utcnow(),
            agent_name=agent_name,
            action=action,
            status=status,
            message=message,
            metadata=metadata or {}
        ))
        self.updated_at = datetime.utcnow()
    
    def add_error(self, error_info: ErrorInfo):
        """Add error to tracking"""
        self.errors.append(error_info)
        self.updated_at = datetime.utcnow()
    
    def update_status(self, new_status: ClaimStatus):
        """Update processing status"""
        self.status = new_status
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "claim_id": self.claim_id,
            "version": self.version,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "image_path": self.image_path,
            "customer_segment": self.customer_segment,
            "region": self.region,
            "ocr_result": self.ocr_result.to_dict() if self.ocr_result else None,
            "structured_claim": self.structured_claim.to_dict() if self.structured_claim else None,
            "policy_info": self.policy_info.to_dict() if self.policy_info else None,
            "coverage_decision": self.coverage_decision.to_dict() if self.coverage_decision else None,
            "audit_trail": [entry.to_dict() for entry in self.audit_trail],
            "errors": [error.to_dict() for error in self.errors],
            "metrics": {
                "intake_duration_ms": self.intake_duration_ms,
                "intelligence_duration_ms": self.intelligence_duration_ms,
                "total_tokens_used": self.total_tokens_used
            }
        }
    
    def to_json(self) -> str:
        """Export as JSON string"""
        return json.dumps(self.to_dict(), indent=2)
