"""Job posting data model for DynamoDB."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"


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
        now = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now
        self.updated_at = updated_at or now

    def to_dynamo(self) -> dict:
        """Serialize to DynamoDB item."""
        item = {
            "PK": {"S": f"JOB#{self.job_id}"},
            "SK": {"S": "METADATA"},
            "GSI1PK": {"S": f"JOBS"},
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
        return item

    @classmethod
    def from_dynamo(cls, item: dict) -> "Job":
        """Deserialize from DynamoDB item."""
        questions = []
        if "screening_questions" in item:
            questions = [q["S"] for q in item["screening_questions"]["L"]]
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
        )
