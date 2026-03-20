"""Voice screening session data model for DynamoDB."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ScreeningStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NO_ANSWER = "no_answer"
    CANCELLED = "cancelled"


class ScreeningResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"


class Screening:
    """Represents a voice screening session."""

    TABLE_NAME = "recruiting-candidates"

    def __init__(
        self,
        screening_id: Optional[str] = None,
        candidate_id: str = "",
        job_id: str = "",
        status: ScreeningStatus = ScreeningStatus.SCHEDULED,
        result: Optional[ScreeningResult] = None,
        scheduled_at: Optional[str] = None,
        started_at: Optional[str] = None,
        ended_at: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        recording_s3_key: Optional[str] = None,
        transcript: Optional[str] = None,
        ai_summary: Optional[str] = None,
        ai_score: Optional[int] = None,
        questions_asked: Optional[list] = None,
        responses: Optional[list] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        self.screening_id = screening_id or str(uuid.uuid4())
        self.candidate_id = candidate_id
        self.job_id = job_id
        self.status = status
        self.result = result
        self.scheduled_at = scheduled_at
        self.started_at = started_at
        self.ended_at = ended_at
        self.duration_seconds = duration_seconds
        self.recording_s3_key = recording_s3_key
        self.transcript = transcript
        self.ai_summary = ai_summary
        self.ai_score = ai_score
        self.questions_asked = questions_asked or []
        self.responses = responses or []
        now = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now
        self.updated_at = updated_at or now

    def to_dynamo(self) -> dict:
        """Serialize to DynamoDB item."""
        item = {
            "PK": {"S": f"CANDIDATE#{self.candidate_id}"},
            "SK": {"S": f"SCREENING#{self.screening_id}"},
            "GSI1PK": {"S": f"JOB#{self.job_id}"},
            "GSI1SK": {"S": f"SCREENING#{self.status.value}#{self.screening_id}"},
            "screening_id": {"S": self.screening_id},
            "candidate_id": {"S": self.candidate_id},
            "job_id": {"S": self.job_id},
            "status": {"S": self.status.value},
            "created_at": {"S": self.created_at},
            "updated_at": {"S": self.updated_at},
        }
        if self.result:
            item["result"] = {"S": self.result.value}
        if self.scheduled_at:
            item["scheduled_at"] = {"S": self.scheduled_at}
        if self.started_at:
            item["started_at"] = {"S": self.started_at}
        if self.ended_at:
            item["ended_at"] = {"S": self.ended_at}
        if self.duration_seconds is not None:
            item["duration_seconds"] = {"N": str(self.duration_seconds)}
        if self.recording_s3_key:
            item["recording_s3_key"] = {"S": self.recording_s3_key}
        if self.transcript:
            item["transcript"] = {"S": self.transcript}
        if self.ai_summary:
            item["ai_summary"] = {"S": self.ai_summary}
        if self.ai_score is not None:
            item["ai_score"] = {"N": str(self.ai_score)}
        if self.questions_asked:
            item["questions_asked"] = {"L": [{"S": q} for q in self.questions_asked]}
        if self.responses:
            item["responses"] = {"L": [{"S": r} for r in self.responses]}
        return item

    @classmethod
    def from_dynamo(cls, item: dict) -> "Screening":
        """Deserialize from DynamoDB item."""
        questions = []
        if "questions_asked" in item:
            questions = [q["S"] for q in item["questions_asked"]["L"]]
        responses = []
        if "responses" in item:
            responses = [r["S"] for r in item["responses"]["L"]]
        return cls(
            screening_id=item["screening_id"]["S"],
            candidate_id=item["candidate_id"]["S"],
            job_id=item["job_id"]["S"],
            status=ScreeningStatus(item["status"]["S"]),
            result=ScreeningResult(item["result"]["S"]) if "result" in item else None,
            scheduled_at=item.get("scheduled_at", {}).get("S"),
            started_at=item.get("started_at", {}).get("S"),
            ended_at=item.get("ended_at", {}).get("S"),
            duration_seconds=int(item["duration_seconds"]["N"]) if "duration_seconds" in item else None,
            recording_s3_key=item.get("recording_s3_key", {}).get("S"),
            transcript=item.get("transcript", {}).get("S"),
            ai_summary=item.get("ai_summary", {}).get("S"),
            ai_score=int(item["ai_score"]["N"]) if "ai_score" in item else None,
            questions_asked=questions,
            responses=responses,
            created_at=item["created_at"]["S"],
            updated_at=item["updated_at"]["S"],
        )

    def to_api(self) -> dict:
        """Serialize for API response."""
        result = {
            "screening_id": self.screening_id,
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "status": self.status.value,
            "result": self.result.value if self.result else None,
            "scheduled_at": self.scheduled_at,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
            "ai_summary": self.ai_summary,
            "ai_score": self.ai_score,
            "questions_asked": self.questions_asked,
            "responses": self.responses,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        return result
