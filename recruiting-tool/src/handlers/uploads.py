"""S3 presigned URL handler for file uploads."""

import os
import uuid

import boto3
from src.utils.response import success, error, parse_body

ASSETS_BUCKET = os.environ.get("ASSETS_BUCKET", "")
ALLOWED_PREFIXES = {"resumes", "recordings"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def get_presigned_url(event, context):
    """POST /uploads/presign — Generate a presigned S3 upload URL.

    Body: {"prefix": "resumes|recordings", "filename": "resume.pdf", "content_type": "application/pdf"}
    """
    try:
        data = parse_body(event)
        prefix = data.get("prefix", "")
        filename = data.get("filename", "")
        content_type = data.get("content_type", "application/octet-stream")

        if not prefix or prefix not in ALLOWED_PREFIXES:
            return error(f"prefix must be one of: {sorted(ALLOWED_PREFIXES)}")
        if not filename:
            return error("filename is required")

        # Sanitize: strip path separators from filename
        safe_name = filename.replace("/", "_").replace("\\", "_")
        key = f"{prefix}/{uuid.uuid4()}/{safe_name}"

        s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": ASSETS_BUCKET,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=900,  # 15 minutes
        )

        return success({
            "upload_url": url,
            "s3_key": key,
            "expires_in": 900,
        })
    except Exception as e:
        return error(str(e), status_code=500)
