"""Generate a 10-page project overview PDF for the Recruiting Tool."""

from fpdf import FPDF


class RecruitingPDF(FPDF):
    BLUE = (41, 98, 168)
    DARK = (33, 33, 33)
    GRAY = (100, 100, 100)
    LIGHT_BG = (245, 247, 250)
    WHITE = (255, 255, 255)
    ACCENT = (52, 152, 219)
    GREEN = (39, 174, 96)
    RED = (231, 76, 60)
    ORANGE = (243, 156, 18)

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*self.GRAY)
        self.cell(0, 8, "Recruiting Tool - Project Overview", align="L")
        self.cell(0, 8, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*self.BLUE)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        if self.page_no() == 1:
            self.set_y(-15)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(*self.GRAY)
            self.cell(0, 10, "Confidential - XWell Recruiting", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*self.BLUE)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*self.BLUE)
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(4)

    def sub_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*self.DARK)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*self.DARK)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet(self, text, indent=15):
        x = self.get_x()
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*self.DARK)
        self.cell(indent, 5.5, "-", new_x="END")
        self.multi_cell(0, 5.5, f" {text}", new_x="LMARGIN")
        self.ln(1)

    def key_value(self, key, value):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self.BLUE)
        self.cell(50, 5.5, key, new_x="END")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*self.DARK)
        self.multi_cell(0, 5.5, value, new_x="LMARGIN")
        self.ln(1)

    def info_box(self, text):
        self.set_fill_color(*self.LIGHT_BG)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*self.DARK)
        x = self.get_x()
        y = self.get_y()
        self.rect(x, y, 190, 18, style="F")
        self.set_xy(x + 4, y + 3)
        self.multi_cell(182, 4.5, text, new_x="LMARGIN")
        self.set_y(y + 20)

    def table_header(self, cols, widths):
        self.set_fill_color(*self.BLUE)
        self.set_text_color(*self.WHITE)
        self.set_font("Helvetica", "B", 9)
        for i, col in enumerate(cols):
            self.cell(widths[i], 7, col, border=1, fill=True, align="C", new_x="END")
        self.ln()

    def table_row(self, cols, widths, fill=False):
        if fill:
            self.set_fill_color(*self.LIGHT_BG)
        self.set_text_color(*self.DARK)
        self.set_font("Helvetica", "", 9)
        for i, col in enumerate(cols):
            self.cell(widths[i], 6.5, col, border=1, fill=fill, new_x="END")
        self.ln()


def build_pdf():
    pdf = RecruitingPDF()

    # ── PAGE 1: COVER ──
    pdf.add_page()
    pdf.ln(50)
    pdf.set_font("Helvetica", "B", 32)
    pdf.set_text_color(*RecruitingPDF.BLUE)
    pdf.cell(0, 15, "Recruiting Tool", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(*RecruitingPDF.GRAY)
    pdf.cell(0, 10, "AI-Powered Candidate Screening & Matching", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.set_draw_color(*RecruitingPDF.BLUE)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(10)

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*RecruitingPDF.DARK)
    pdf.cell(0, 8, "Project Overview & Roadmap", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "March 2026", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(15)

    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*RecruitingPDF.GRAY)
    pdf.cell(0, 6, "Built on AWS Lambda + DynamoDB + API Gateway", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Integrated with Indeed, Slack, and Voice Screening", align="C", new_x="LMARGIN", new_y="NEXT")

    # ── PAGE 2: EXECUTIVE SUMMARY ──
    pdf.add_page()
    pdf.section_title("1. Executive Summary")

    pdf.body_text(
        "The Recruiting Tool is a serverless application designed to streamline candidate screening "
        "and matching for salon and spa positions at XWell locations (Naples, FL). It automates the "
        "most time-consuming parts of recruiting: sourcing candidates from Indeed, scoring them "
        "against job requirements, conducting AI-assisted voice screenings, and delivering results "
        "to recruiters via Slack."
    )

    pdf.sub_title("The Problem")
    pdf.bullet("Recruiters spend excessive time on unqualified candidates who lack required certifications")
    pdf.bullet("Candidate responsiveness is a major blocker - no tracking of outreach status")
    pdf.bullet("Manual screening calls are time-intensive and inconsistent")
    pdf.bullet("No systematic way to match candidates to open roles based on availability and qualifications")

    pdf.sub_title("The Solution")
    pdf.bullet("Automated candidate sourcing from Indeed with role-specific search presets")
    pdf.bullet("Deterministic scoring engine that ranks candidates by fit (certifications, availability, experience)")
    pdf.bullet("AI voice screening with structured questions, transcripts, and scoring")
    pdf.bullet("Slack notifications keep recruiters informed without requiring them to check a dashboard")
    pdf.bullet("Recommendation engine suggests next steps (interview, review, pass) while keeping recruiter in control")

    pdf.ln(3)
    pdf.info_box(
        "KEY METRIC: The tool processes candidates through a full pipeline - from Indeed import to "
        "ranked recommendations - in under 30 seconds per candidate, compared to 15-20 minutes of manual review."
    )

    # ── PAGE 3: ARCHITECTURE ──
    pdf.add_page()
    pdf.section_title("2. Architecture & Tech Stack")

    pdf.sub_title("Infrastructure (AWS Serverless)")
    pdf.bullet("17 Lambda functions (Python 3.12, 256MB, 30s timeout)")
    pdf.bullet("DynamoDB single-table design with GSI for secondary access patterns")
    pdf.bullet("S3 for resume and call recording storage (private, presigned URLs)")
    pdf.bullet("API Gateway REST API with API key authentication")
    pdf.bullet("SAM (Serverless Application Model) for infrastructure-as-code")

    pdf.ln(2)
    pdf.sub_title("Single-Table DynamoDB Design")
    widths = [55, 55, 80]
    pdf.table_header(["Entity", "PK", "SK"], widths)
    pdf.table_row(["Job", "JOB#{job_id}", "METADATA"], widths, fill=True)
    pdf.table_row(["Candidate", "CANDIDATE#{id}", "PROFILE"], widths)
    pdf.table_row(["Screening", "CANDIDATE#{id}", "SCREENING#{scr_id}"], widths, fill=True)
    pdf.table_row(["GSI1 (Jobs)", "JOBS", "STATUS#{status}#{id}"], widths)
    pdf.table_row(["GSI1 (Candidates)", "JOB#{job_id}", "STATUS#{status}#{id}"], widths, fill=True)

    pdf.ln(4)
    pdf.sub_title("External Integrations")
    pdf.bullet("Indeed - Job board scraping via python-jobspy (search + bulk import)")
    pdf.bullet("Slack - Webhook notifications for new candidates and screening results")
    pdf.bullet("S3 - Presigned URL uploads for resumes and recordings")

    pdf.ln(2)
    pdf.sub_title("Deployment")
    pdf.bullet("Two environments: dev (auto-confirm) and prod (manual changeset review)")
    pdf.bullet("Deploy script runs full test suite before allowing deployment")
    pdf.bullet("Makefile targets for build, test, deploy, local development, and log tailing")

    # ── PAGE 4: API REFERENCE ──
    pdf.add_page()
    pdf.section_title("3. API Reference")
    pdf.body_text("All endpoints require x-api-key header except /health. Base URL from CloudFormation outputs.")

    pdf.sub_title("Jobs (5 Endpoints)")
    w = [25, 50, 115]
    pdf.table_header(["Method", "Path", "Description"], w)
    pdf.table_row(["POST", "/jobs", "Create job posting (title required)"], w, fill=True)
    pdf.table_row(["GET", "/jobs", "List all jobs (?status=open filter)"], w)
    pdf.table_row(["GET", "/jobs/{id}", "Get job details"], w, fill=True)
    pdf.table_row(["PUT", "/jobs/{id}", "Update job posting"], w)
    pdf.table_row(["DELETE", "/jobs/{id}", "Delete job posting"], w, fill=True)

    pdf.ln(3)
    pdf.sub_title("Candidates (5 Endpoints)")
    pdf.table_header(["Method", "Path", "Description"], w)
    pdf.table_row(["POST", "/candidates", "Create candidate (triggers Slack)"], w, fill=True)
    pdf.table_row(["GET", "/candidates/{id}", "Get candidate details"], w)
    pdf.table_row(["GET", "/jobs/{id}/candidates", "List candidates for job (?status=)"], w, fill=True)
    pdf.table_row(["PATCH", "/candidates/{id}/status", "Update candidate status"], w)
    pdf.table_row(["DELETE", "/candidates/{id}", "Delete candidate"], w, fill=True)

    pdf.ln(3)
    pdf.sub_title("Screenings (4 Endpoints)")
    pdf.table_header(["Method", "Path", "Description"], w)
    pdf.table_row(["POST", "/screenings", "Schedule screening (sets status)"], w, fill=True)
    pdf.table_row(["GET", "/screenings/{c_id}/{s_id}", "Get screening details"], w)
    pdf.table_row(["GET", "/candidates/{id}/screenings", "List screenings for candidate"], w, fill=True)
    pdf.table_row(["POST", "/screenings/{c}/{s}/complete", "Complete with AI score + result"], w)

    pdf.ln(3)
    pdf.sub_title("Filtering & Scraping (5 Endpoints)")
    pdf.table_header(["Method", "Path", "Description"], w)
    pdf.table_row(["GET", "/jobs/{id}/candidates/rank", "Rank candidates for job (?min_score=)"], w, fill=True)
    pdf.table_row(["GET", "/candidates/{id}/match", "Find best jobs for candidate"], w)
    pdf.table_row(["POST", "/candidates/score", "Score candidate vs specific job"], w, fill=True)
    pdf.table_row(["POST", "/scrape/search", "Search Indeed (no save)"], w)
    pdf.table_row(["POST", "/scrape/import", "Scrape + import as DRAFT jobs"], w, fill=True)

    # ── PAGE 5: HOW TO ACCESS ──
    pdf.add_page()
    pdf.section_title("4. How to Access & Use")

    pdf.sub_title("Getting the API Key")
    pdf.body_text(
        "After deployment, the API key is available via CloudFormation outputs. "
        "Use 'make api-key' or check the AWS console under API Gateway > API Keys."
    )

    pdf.sub_title("Deploying")
    pdf.set_font("Courier", "", 9)
    pdf.set_fill_color(*RecruitingPDF.LIGHT_BG)
    code = (
        "# First time setup\n"
        "cd recruiting-tool\n"
        "pip install -r requirements.txt\n"
        "pip install -r requirements-dev.txt\n\n"
        "# Run tests\n"
        "make test\n\n"
        "# Deploy to dev\n"
        "make deploy-dev\n\n"
        "# Deploy to production\n"
        "make deploy\n\n"
        "# Get your API key\n"
        "make api-key\n\n"
        "# Run locally on port 3000\n"
        "make local"
    )
    pdf.multi_cell(190, 4.5, code, fill=True, new_x="LMARGIN")
    pdf.ln(4)

    pdf.sub_title("Making API Calls")
    pdf.set_font("Courier", "", 9)
    code2 = (
        '# Create a job\n'
        'curl -X POST $API_URL/jobs \\\n'
        '  -H "x-api-key: $API_KEY" \\\n'
        '  -H "Content-Type: application/json" \\\n'
        '  -d \'{"title": "Massage Therapist", "location": "Naples, FL",\n'
        '       "department": "Spa", "requirements": "Licensed massage therapist"}\'\n\n'
        '# Rank candidates for a job\n'
        'curl "$API_URL/jobs/{job_id}/candidates/rank?min_score=50" \\\n'
        '  -H "x-api-key: $API_KEY"\n\n'
        '# Search Indeed\n'
        'curl -X POST $API_URL/scrape/search \\\n'
        '  -H "x-api-key: $API_KEY" \\\n'
        '  -d \'{"search_term": "esthetician", "location": "Naples, FL"}\''
    )
    pdf.multi_cell(190, 4.5, code2, fill=True, new_x="LMARGIN")

    # ── PAGE 6: SCORING ENGINE ──
    pdf.add_page()
    pdf.section_title("5. Scoring Engine (Current)")

    pdf.body_text(
        "The current scoring engine uses deterministic keyword matching - no ML models. "
        "Candidates are scored 0-100 against job requirements using three weighted dimensions."
    )

    pdf.sub_title("Current Weights")
    w2 = [50, 30, 110]
    pdf.table_header(["Dimension", "Weight", "How It Works"], w2)
    pdf.table_row(["Skills", "60%", "Keyword overlap: candidate notes vs job requirements"], w2, fill=True)
    pdf.table_row(["Location", "20%", "Exact=100, Same state=75, Remote=70, None=20"], w2)
    pdf.table_row(["Experience", "20%", "Years extracted from text + seniority level matching"], w2, fill=True)

    pdf.ln(3)
    pdf.sub_title("Skill Categories Detected")
    pdf.bullet("Salon/Spa: cosmetology, esthetician, hair styling, color specialist, nail technician, massage therapy")
    pdf.bullet("Management: leadership, strategic planning, team management, budgeting")
    pdf.bullet("General: customer service, scheduling, inventory management, retail sales")
    pdf.bullet("PR/Comms: crisis management, public relations, brand management, media relations")

    pdf.ln(3)
    pdf.sub_title("Score Output (Example)")
    pdf.set_font("Courier", "", 9)
    pdf.set_fill_color(*RecruitingPDF.LIGHT_BG)
    example = (
        '{\n'
        '  "total_score": 78,\n'
        '  "breakdown": {\n'
        '    "skills": 85,\n'
        '    "location": 100,\n'
        '    "experience": 70\n'
        '  },\n'
        '  "matched_skills": ["cosmetology", "customer service"],\n'
        '  "missing_skills": ["color specialist"]\n'
        '}'
    )
    pdf.multi_cell(190, 4.5, example, fill=True, new_x="LMARGIN")

    pdf.ln(4)
    pdf.info_box(
        "LIMITATION: The current engine matches keywords but does not gate on hard requirements. "
        "A candidate missing a required cosmetology license still gets scored - just lower. "
        "The planned upgrade adds hard disqualification logic."
    )

    # ── PAGE 7: VOICE SCREENING ──
    pdf.add_page()
    pdf.section_title("6. Voice Screening Pipeline")

    pdf.body_text(
        "The screening system manages the full lifecycle of AI-assisted candidate phone screens. "
        "Each screening tracks questions asked, candidate responses, transcripts, and an AI-generated "
        "summary with a 0-100 score."
    )

    pdf.sub_title("Screening Workflow")
    pdf.bullet("1. SCHEDULE - POST /screenings creates a session, sets candidate status to screening_scheduled")
    pdf.bullet("2. CONDUCT - External voice service calls the candidate with structured screening questions")
    pdf.bullet("3. COMPLETE - POST /screenings/{id}/complete stores transcript, AI summary, score, and result")
    pdf.bullet("4. NOTIFY - Slack notification sent with pass/fail/review result and score")

    pdf.ln(2)
    pdf.sub_title("Screening Data Captured")
    w3 = [50, 140]
    pdf.table_header(["Field", "Description"], w3)
    pdf.table_row(["questions_asked", "List of questions posed to candidate"], w3, fill=True)
    pdf.table_row(["responses", "Candidate's answers (parallel list)"], w3)
    pdf.table_row(["transcript", "Full call transcript"], w3, fill=True)
    pdf.table_row(["ai_summary", "AI-generated 2-3 sentence assessment"], w3)
    pdf.table_row(["ai_score", "0-100 score based on response quality"], w3, fill=True)
    pdf.table_row(["result", "pass / fail / review"], w3)
    pdf.table_row(["duration_seconds", "Length of the screening call"], w3, fill=True)
    pdf.table_row(["recording_s3_key", "S3 path to call recording"], w3)

    pdf.ln(3)
    pdf.sub_title("Candidate Status Flow")
    pdf.body_text(
        "new -> screening_scheduled -> screening_in_progress -> screening_complete -> passed / rejected"
    )
    pdf.body_text(
        "On screening completion, the candidate status auto-updates based on the result: "
        "'pass' sets status to 'passed', 'fail' sets to 'rejected', 'review' sets to 'screening_complete' "
        "for manual recruiter review."
    )

    # ── PAGE 8: SURVEY RESULTS ──
    pdf.add_page()
    pdf.section_title("7. Team Survey Results")

    pdf.body_text(
        "A survey was conducted with the recruiting team (2 respondents: Morgan, who lives in the role daily, "
        "and one respondent with historical perspective). Results drive the planned refinements."
    )

    pdf.sub_title("Key Findings")

    pdf.ln(1)
    w4 = [95, 95]
    pdf.table_header(["Question", "Result"], w4)
    pdf.table_row(["#1 Blocker", "Unqualified candidates (50%) + Responsiveness (50%)"], w4, fill=True)
    pdf.table_row(["#1 Desired Bot Task", "Confirm certifications + Ask availability (100%)"], w4)
    pdf.table_row(["Sourcing Channel", "100% from Indeed"], w4, fill=True)
    pdf.table_row(["Recommendation Style", "50% suggest interview / 50% info only"], w4)
    pdf.table_row(["Locations", "Naples, FL (XWell / salon & spa)"], w4, fill=True)

    pdf.ln(4)
    pdf.sub_title("Role Categories & Requirements")
    w5 = [45, 70, 40, 35]
    pdf.table_header(["Category", "Positions", "Certs Required?", "Key Filter"], w5)
    pdf.table_row(["Spa", "Massage, Nail Tech, Esthetician", "Yes", "Certifications"], w5, fill=True)
    pdf.table_row(["Management", "Spa Mgr, Station Mgr, Exp Coord", "No", "Experience"], w5)
    pdf.table_row(["Biosecurity", "Bio-Security Specialist", "Yes", "Availability"], w5, fill=True)
    pdf.table_row(["Guest Svcs", "Guest Service Associate", "No", "Availability"], w5)

    pdf.ln(4)
    pdf.sub_title("What the Team Wants the Bot to Do")
    pdf.bullet("Confirm candidates hold required certifications/licenses BEFORE scheduling interviews")
    pdf.bullet("Ask about shift availability (morning, afternoon, evening, weekend)")
    pdf.bullet("Provide a recommendation (suggest interview vs. flag for review) but let recruiter decide")
    pdf.bullet("Track candidate responsiveness - stop wasting time on people who do not respond")
    pdf.bullet("Pre-filter aggressively so recruiters only see qualified candidates")

    # ── PAGE 9: PLANNED REFINEMENTS ──
    pdf.add_page()
    pdf.section_title("8. Planned Refinements")

    pdf.body_text(
        "Based on survey findings, 10 implementation steps are planned. The core theme: "
        "shift from generic skill matching to domain-specific qualification gating."
    )

    pdf.sub_title("Top 3 Changes")
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*RecruitingPDF.GREEN)
    pdf.cell(0, 6, "1. Certification Gating (Survey: 100% priority)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*RecruitingPDF.DARK)
    pdf.bullet("Add certifications list to Candidate model, required/preferred certs to Job model")
    pdf.bullet("Missing a required cert = hard disqualification (not just a low score)")
    pdf.bullet("Auto-generate screening questions: 'Do you hold a current cosmetology license?'")

    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*RecruitingPDF.GREEN)
    pdf.cell(0, 6, "2. Availability Matching (Survey: 100% priority)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*RecruitingPDF.DARK)
    pdf.bullet("Add availability dict to Candidate (day -> shifts), shift_schedule to Job")
    pdf.bullet("Score overlap between candidate availability and job shift requirements")
    pdf.bullet("Auto-generate: 'Are you available to work evening/weekend shifts?'")

    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*RecruitingPDF.GREEN)
    pdf.cell(0, 6, "3. Role-Specific Scoring Profiles", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*RecruitingPDF.DARK)

    w6 = [38, 38, 38, 38, 38]
    pdf.table_header(["Role", "Certs", "Availability", "Experience", "Location"], w6)
    pdf.table_row(["Spa", "40%", "25%", "20%", "15%"], w6, fill=True)
    pdf.table_row(["Management", "15%", "25%", "40%", "20%"], w6)
    pdf.table_row(["Biosecurity", "25%", "35%", "20%", "20%"], w6, fill=True)
    pdf.table_row(["Guest Svcs", "15%", "35%", "25%", "25%"], w6)

    pdf.ln(3)
    pdf.sub_title("Supporting Changes")
    pdf.bullet("Recommendation engine: suggest_interview (75+), flag_review (50-74), disqualified (missing cert)")
    pdf.bullet("Responsiveness tracking: last_contacted, response_status fields on Candidate")
    pdf.bullet("Indeed search presets: one-click import for spa therapists, management, biosecurity, guest services")
    pdf.bullet("Drop generic skill matching (Python, JavaScript, etc.) - irrelevant for this domain")

    # ── PAGE 10: TEST COVERAGE & NEXT STEPS ──
    pdf.add_page()
    pdf.section_title("9. Test Coverage")

    pdf.body_text("40+ tests across 4 test files. Deploy script gates on all tests passing.")

    w7 = [60, 25, 105]
    pdf.table_header(["Test File", "Cases", "Coverage"], w7)
    pdf.table_row(["test_models.py", "6", "Model serialization roundtrips (Dynamo + API)"], w7, fill=True)
    pdf.table_row(["test_filtering.py", "30+", "Skills, location, experience scoring + handlers"], w7)
    pdf.table_row(["test_bud_light_scenario.py", "10", "Full pipeline: VP Crisis role (Bud Light case)"], w7, fill=True)
    pdf.table_row(["test_sweeney_scenario.py", "8", "Full pipeline: Crisis Manager (Sweeney case)"], w7)

    pdf.ln(2)
    pdf.body_text(
        "Integration tests create realistic scenarios with real job postings, multiple candidates "
        "of varying quality, and validate the full pipeline from creation through screening completion."
    )

    pdf.ln(3)
    pdf.section_title("10. Roadmap & Next Steps")

    pdf.sub_title("Immediate (Next Sprint)")
    pdf.bullet("Implement certification gating and availability matching (Steps 1-4 from plan)")
    pdf.bullet("Add recommendation engine with configurable thresholds")
    pdf.bullet("Update all tests for new fields and scoring logic")

    pdf.sub_title("Near-Term")
    pdf.bullet("Indeed search presets for the team's actual roles")
    pdf.bullet("Candidate responsiveness tracking and filtering")
    pdf.bullet("Auto-generated pre-screen questions from job requirements")

    pdf.sub_title("Future")
    pdf.bullet("Resume parsing (OCR/PDF extraction for automatic skill detection)")
    pdf.bullet("SMS/email outreach automation for candidate engagement")
    pdf.bullet("Calendar integration for interview scheduling")
    pdf.bullet("Indeed partner API for application tracking (beyond scraping)")

    pdf.ln(5)
    pdf.info_box(
        "STATUS: Core pipeline is built and tested. The scoring engine works but needs domain-specific tuning "
        "based on survey results. Next phase focuses on certification gating and availability - the two features "
        "the team rated as 100% priority."
    )

    output_path = "/home/user/device-link/recruiting-tool/Recruiting_Tool_Overview.pdf"
    pdf.output(output_path)
    return output_path


if __name__ == "__main__":
    path = build_pdf()
    print(f"PDF generated: {path}")
