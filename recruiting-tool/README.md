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

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pip install -r requirements-dev.txt
pytest

# Deploy
sam build
sam deploy --guided
```

## Data Model (Single-Table DynamoDB)

| Entity | PK | SK | GSI1PK | GSI1SK |
|--------|----|----|--------|--------|
| Job | JOB#{id} | METADATA | JOBS | STATUS#{status}#{id} |
| Candidate | CANDIDATE#{id} | PROFILE | JOB#{job_id} | STATUS#{status}#{id} |
| Screening | CANDIDATE#{id} | SCREENING#{id} | JOB#{job_id} | SCREENING#{status}#{id} |
