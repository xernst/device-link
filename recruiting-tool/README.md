# AI Screening Assistant

Cloud-based recruiting tool for Naples/Xwell salon & spa locations. Uses voice AI for 5-10 minute phone screens with Slack integration for recruiters.

## Architecture

- **API**: AWS API Gateway + Lambda (Python 3.12)
- **Database**: DynamoDB (single-table design)
- **Storage**: S3 (resumes, call recordings)
- **Voice**: AWS Connect / Twilio (planned)
- **Notifications**: Slack webhooks
- **IaC**: AWS SAM

## API Endpoints

### Jobs
| Method | Path | Description |
|--------|------|-------------|
| POST | /jobs | Create job posting |
| GET | /jobs | List all jobs |
| GET | /jobs/{id} | Get job details |
| PUT | /jobs/{id} | Update job |
| DELETE | /jobs/{id} | Delete job |

### Candidates
| Method | Path | Description |
|--------|------|-------------|
| POST | /candidates | Create candidate |
| GET | /candidates/{id} | Get candidate |
| GET | /jobs/{id}/candidates | List candidates for job |
| PATCH | /candidates/{id}/status | Update status |
| DELETE | /candidates/{id} | Delete candidate |

### Screenings
| Method | Path | Description |
|--------|------|-------------|
| POST | /screenings | Schedule screening |
| GET | /screenings/{candidate_id}/{screening_id} | Get screening |
| GET | /candidates/{id}/screenings | List screenings |
| POST | /screenings/{candidate_id}/{screening_id}/complete | Record results |

### Utility
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | None | Health check (no API key needed) |
| POST | /uploads/presign | API Key | Get presigned S3 upload URL |

## Prerequisites

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configured with credentials
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Python 3.12+

## Deploy

```bash
# First time — install deps and run tests
pip install -r requirements-dev.txt
make test

# Deploy to production
make deploy

# Deploy to dev (no changeset confirmation)
make deploy-dev

# Or use the deploy script directly
./scripts/deploy.sh prod    # production
./scripts/deploy.sh dev     # dev environment
```

After deploy, grab your API URL and key:
```bash
make outputs    # show API URL, table name, bucket
make api-key    # print the API key value
```

## Usage

```bash
API_URL="https://xxx.execute-api.us-east-1.amazonaws.com/prod"
API_KEY="your-api-key-here"

# Create a job
curl -X POST "$API_URL/jobs" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "Stylist", "location": "Naples, FL", "status": "open"}'

# Create a candidate
curl -X POST "$API_URL/candidates" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com", "job_id": "JOB_ID"}'

# Upload a resume
curl -X POST "$API_URL/uploads/presign" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prefix": "resumes", "filename": "jane-doe.pdf", "content_type": "application/pdf"}'
# Then PUT to the returned upload_url

# Health check (no API key needed)
curl "$API_URL/health"
```

## Local Development

```bash
make local      # Start local API on port 3000
make logs-CreateJob  # Tail logs for a function
```

## Data Model (Single-Table DynamoDB)

| Entity | PK | SK | GSI1PK | GSI1SK |
|--------|----|----|--------|--------|
| Job | JOB#{id} | METADATA | JOBS | STATUS#{status}#{id} |
| Candidate | CANDIDATE#{id} | PROFILE | JOB#{job_id} | STATUS#{status}#{id} |
| Screening | CANDIDATE#{id} | SCREENING#{id} | JOB#{job_id} | SCREENING#{status}#{id} |
