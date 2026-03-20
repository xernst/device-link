"""Candidate data model for DynamoDB."""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class CandidateStatus(str, Enum):
    NEW = "new"
    SCREENING_SCHEDULED = "screening_scheduled"
    SCREENING_IN_PROGRESS = "screening_in_progress"
    SCREENING_COMPLETE = "screening_complete"
    PASSED = "passed"
    REJECTED = "rejected"
    HIRED = "hired"
    WITHDRAWN = "withdrawn"


class ResponseStatus(str, Enum):
    NOT_CONTACTED = "not_contacted"
    AWAITING_RESPONSE = "awaiting_response"
    RESPONSIVE = "responsive"
    UNRESPONSIVE = "unresponsive"


class Candidate:
    """Represents a candidate in the recruiting pipeline."""

    TABLE_NAME = "recruiting-candidates"

    def __init__(
        self,
        candidate_id: Optional[str] = None,
        job_id: Optional[str] = None,
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        phone: str = "",
        location: str = "",
        status: CandidateStatus = CandidateStatus.NEW,
        source: str = "",
        resume_s3_key: Optional[str] = None,
        notes: str = "",
        # New fields
        certifications: Optional[list] = None,
        availability: Optional[dict] = None,
        years_experience: Optional[int] = None,
        last_contacted: Optional[str] = None,
        response_status: ResponseStatus = ResponseStatus.NOT_CONTACTED,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        self.candidate_id = candidate_id or str(uuid.uuid4())
        self.job_id = job_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.location = location
        self.status = status
        self.source = source
        self.resume_s3_key = resume_s3_key
        self.notes = notes
        self.certifications = certifications or []
        self.availability = availability or {}
        self.years_experience = years_experience
        self.last_contacted = last_contacted
        self.response_status = response_status
        now = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now
        self.updated_at = updated_at or now

    def to_dynamo(self) -> dict:
        """Serialize to DynamoDB item."""
        item = {
            "PK": {"S": f"CANDIDATE#{self.candidate_id}"},
            "SK": {"S": "PROFILE"},
            "GSI1PK": {"S": f"JOB#{self.job_id}"} if self.job_id else {"S": "JOB#UNASSIGNED"},
            "GSI1SK": {"S": f"STATUS#{self.status.value}#{self.candidate_id}"},
            "candidate_id": {"S": self.candidate_id},
            "job_id": {"S": self.job_id or ""},
            "first_name": {"S": self.first_name},
            "last_name": {"S": self.last_name},
            "email": {"S": self.email},
            "phone": {"S": self.phone},
            "location": {"S": self.location},
            "status": {"S": self.status.value},
            "source": {"S": self.source},
            "notes": {"S": self.notes},
            "response_status": {"S": self.response_status.value},
            "created_at": {"S": self.created_at},
            "updated_at": {"S": self.updated_at},
        }
        if self.resume_s3_key:
            item["resume_s3_key"] = {"S": self.resume_s3_key}
        if self.certifications:
            item["certifications"] = {"L": [{"S": c} for c in self.certifications]}
        if self.availability:
            item["availability"] = {"S": json.dumps(self.availability)}
        if self.years_experience is not None:
            item["years_experience"] = {"N": str(self.years_experience)}
        if self.last_contacted:
            item["last_contacted"] = {"S": self.last_contacted}
        return item

    @classmethod
    def from_dynamo(cls, item: dict) -> "Candidate":
        """Deserialize from DynamoDB item."""
        certs = []
        if "certifications" in item:
            certs = [c["S"] for c in item["certifications"]["L"]]

        availability = {}
        if "availability" in item:
            try:
                availability = json.loads(item["availability"]["S"])
            except (json.JSONDecodeError, KeyError):
                availability = {}

        years_exp = None
        if "years_experience" in item:
            years_exp = int(item["years_experience"]["N"])

        return cls(
            candidate_id=item["candidate_id"]["S"],
            job_id=item.get("job_id", {}).get("S") or None,
            first_name=item["first_name"]["S"],
            last_name=item["last_name"]["S"],
            email=item["email"]["S"],
            phone=item["phone"]["S"],
            location=item.get("location", {}).get("S", ""),
            status=CandidateStatus(item["status"]["S"]),
            source=item.get("source", {}).get("S", ""),
            resume_s3_key=item.get("resume_s3_key", {}).get("S"),
            notes=item.get("notes", {}).get("S", ""),
            certifications=certs,
            availability=availability,
            years_experience=years_exp,
            last_contacted=item.get("last_contacted", {}).get("S"),
            response_status=ResponseStatus(
                item.get("response_status", {}).get("S", "not_contacted")
            ),
            created_at=item["created_at"]["S"],
            updated_at=item["updated_at"]["S"],
        )

    def to_api(self) -> dict:
        """Serialize for API response."""
        result = {
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "status": self.status.value,
            "source": self.source,
            "notes": self.notes,
            "certifications": self.certifications,
            "availability": self.availability,
            "years_experience": self.years_experience,
            "last_contacted": self.last_contacted,
            "response_status": self.response_status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.resume_s3_key:
            result["resume_s3_key"] = self.resume_s3_key
        return result

    @classmethod
    def from_api(cls, data: dict) -> "Candidate":
        """Deserialize from API request body."""
        return cls(
            candidate_id=data.get("candidate_id"),
            job_id=data.get("job_id"),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            location=data.get("location", ""),
            status=CandidateStatus(data.get("status", "new")),
            source=data.get("source", ""),
            resume_s3_key=data.get("resume_s3_key"),
            notes=data.get("notes", ""),
            certifications=data.get("certifications", []),
            availability=data.get("availability", {}),
            years_experience=data.get("years_experience"),
            last_contacted=data.get("last_contacted"),
            response_status=ResponseStatus(
                data.get("response_status", "not_contacted")
            ),
        )
