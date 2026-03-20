"""Job posting data model for DynamoDB."""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"


class RoleCategory(str, Enum):
    SPA = "spa"
    MANAGEMENT = "management"
    BIOSECURITY = "biosecurity"
    GUEST_SERVICES = "guest_services"


class Job:
    """Represents a job posting."""

    TABLE_NAME = "recruiting-candidates"

    def __init__(
        self,
        job_id: Optional[str] = None,
        title: str = "",
        location: str = "",
        department: str = "",
        description: str = "",
        requirements: str = "",
        status: JobStatus = JobStatus.DRAFT,
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None,
        screening_questions: Optional[list] = None,
        # New fields
        required_certifications: Optional[list] = None,
        preferred_certifications: Optional[list] = None,
        shift_schedule: Optional[list] = None,
        role_category: Optional[RoleCategory] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        self.job_id = job_id or str(uuid.uuid4())
        self.title = title
        self.location = location
        self.department = department
        self.description = description
        self.requirements = requirements
        self.status = status
        self.salary_min = salary_min
        self.salary_max = salary_max
        self.screening_questions = screening_questions or []
        self.required_certifications = required_certifications or []
        self.preferred_certifications = preferred_certifications or []
        self.shift_schedule = shift_schedule or []
        self.role_category = role_category
        now = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now
        self.updated_at = updated_at or now

    def to_dynamo(self) -> dict:
        """Serialize to DynamoDB item."""
        item = {
            "PK": {"S": f"JOB#{self.job_id}"},
            "SK": {"S": "METADATA"},
            "GSI1PK": {"S": "JOBS"},
            "GSI1SK": {"S": f"STATUS#{self.status.value}#{self.job_id}"},
            "job_id": {"S": self.job_id},
            "title": {"S": self.title},
            "location": {"S": self.location},
            "department": {"S": self.department},
            "description": {"S": self.description},
            "requirements": {"S": self.requirements},
            "status": {"S": self.status.value},
            "created_at": {"S": self.created_at},
            "updated_at": {"S": self.updated_at},
        }
        if self.salary_min is not None:
            item["salary_min"] = {"N": str(self.salary_min)}
        if self.salary_max is not None:
            item["salary_max"] = {"N": str(self.salary_max)}
        if self.screening_questions:
            item["screening_questions"] = {
                "L": [{"S": q} for q in self.screening_questions]
            }
        if self.required_certifications:
            item["required_certifications"] = {
                "L": [{"S": c} for c in self.required_certifications]
            }
        if self.preferred_certifications:
            item["preferred_certifications"] = {
                "L": [{"S": c} for c in self.preferred_certifications]
            }
        if self.shift_schedule:
            item["shift_schedule"] = {
                "L": [{"S": s} for s in self.shift_schedule]
            }
        if self.role_category:
            rc = self.role_category
            item["role_category"] = {"S": rc.value if hasattr(rc, "value") else rc}
        return item

    @classmethod
    def from_dynamo(cls, item: dict) -> "Job":
        """Deserialize from DynamoDB item."""
        questions = []
        if "screening_questions" in item:
            questions = [q["S"] for q in item["screening_questions"]["L"]]

        required_certs = []
        if "required_certifications" in item:
            required_certs = [c["S"] for c in item["required_certifications"]["L"]]

        preferred_certs = []
        if "preferred_certifications" in item:
            preferred_certs = [c["S"] for c in item["preferred_certifications"]["L"]]

        shift_schedule = []
        if "shift_schedule" in item:
            shift_schedule = [s["S"] for s in item["shift_schedule"]["L"]]

        role_category = None
        if "role_category" in item:
            try:
                role_category = RoleCategory(item["role_category"]["S"])
            except ValueError:
                role_category = None

        return cls(
            job_id=item["job_id"]["S"],
            title=item["title"]["S"],
            location=item.get("location", {}).get("S", ""),
            department=item.get("department", {}).get("S", ""),
            description=item.get("description", {}).get("S", ""),
            requirements=item.get("requirements", {}).get("S", ""),
            status=JobStatus(item["status"]["S"]),
            salary_min=int(item["salary_min"]["N"]) if "salary_min" in item else None,
            salary_max=int(item["salary_max"]["N"]) if "salary_max" in item else None,
            screening_questions=questions,
            required_certifications=required_certs,
            preferred_certifications=preferred_certs,
            shift_schedule=shift_schedule,
            role_category=role_category,
            created_at=item["created_at"]["S"],
            updated_at=item["updated_at"]["S"],
        )

    def to_api(self) -> dict:
        """Serialize for API response."""
        result = {
            "job_id": self.job_id,
            "title": self.title,
            "location": self.location,
            "department": self.department,
            "description": self.description,
            "requirements": self.requirements,
            "status": self.status.value,
            "screening_questions": self.screening_questions,
            "required_certifications": self.required_certifications,
            "preferred_certifications": self.preferred_certifications,
            "shift_schedule": self.shift_schedule,
            "role_category": self.role_category.value if self.role_category else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.salary_min is not None:
            result["salary_min"] = self.salary_min
        if self.salary_max is not None:
            result["salary_max"] = self.salary_max
        return result

    @classmethod
    def from_api(cls, data: dict) -> "Job":
        """Deserialize from API request body."""
        role_category = None
        if data.get("role_category"):
            try:
                role_category = RoleCategory(data["role_category"])
            except ValueError:
                role_category = None

        return cls(
            job_id=data.get("job_id"),
            title=data.get("title", ""),
            location=data.get("location", ""),
            department=data.get("department", ""),
            description=data.get("description", ""),
            requirements=data.get("requirements", ""),
            status=JobStatus(data.get("status", "draft")),
            salary_min=data.get("salary_min"),
            salary_max=data.get("salary_max"),
            screening_questions=data.get("screening_questions", []),
            required_certifications=data.get("required_certifications", []),
            preferred_certifications=data.get("preferred_certifications", []),
            shift_schedule=data.get("shift_schedule", []),
            role_category=role_category,
        )
