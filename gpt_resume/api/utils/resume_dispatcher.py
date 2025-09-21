from .base_prompt import base_function_prompt
from ..serializers import ApplicantSerializer  # Fixed import
from ..models import Applicant, College, Project, ProfessionalExperience, Job
import os, json
from django.conf import settings
from concurrent.futures import ThreadPoolExecutor, as_completed
import fitz
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
client = OpenAI(api_key=settings.OPENAI_API_KEY)


# ---------------------------
# Helper: Normalize Dates
# ---------------------------
def normalize_date(value):
    if not value or str(value).strip() in ["-", "—", "–"]:
        return None

    value = str(value).strip()

    # Case 1: Only year
    if len(value) == 4 and value.isdigit():
        return f"{value}-01-01"

    # Case 2: Month-Year
    try:
        if "-" in value:
            if len(value.split("-")[0]) <= 2:
                return datetime.strptime(value, "%m-%Y").strftime("%Y-%m-%d")
            if len(value.split("-")[0]) == 4:
                return datetime.strptime(value, "%Y-%m").strftime("%Y-%m-%d")
    except:
        pass

    # Case 3: Full date
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        return None


class ApplicantHandler:
    def __init__(self, applicant: Applicant):
        self.applicant = applicant
        self.openai = client
        self.text = self._extract_text_data_from_pdf()

    def _update_resume(self, data: dict, relevance: int) -> None:
        self.applicant.resume_text = self.text or ""
        self.applicant.name = data.get("name", "")
        self.applicant.email = data.get("email", "")
        self.applicant.relevance = relevance
        self.applicant.embedding_stored = False
        self.applicant.save()

    def _create_college(self, data: dict) -> None:
        if data:
            if "start_date" in data:
                data["start_date"] = normalize_date(data["start_date"])
            if "end_date" in data:
                data["end_date"] = normalize_date(data["end_date"])

            # ✅ Ensure branch is always present
            if not data.get("branch"):
                data["branch"] = "Unknown"

            # ✅ Filter only valid fields
            allowed_fields = {f.name for f in College._meta.get_fields()}
            clean_data = {k: v for k, v in data.items() if k in allowed_fields}
            College.objects.create(**clean_data, applicant=self.applicant)

    def _create_project(self, data: dict) -> None:
        if data:
            # ✅ Filter invalid keys like duration_months
            allowed_fields = {f.name for f in Project._meta.get_fields()}
            clean_data = {k: v for k, v in data.items() if k in allowed_fields}
            Project.objects.create(**clean_data, applicant=self.applicant)

    def _create_professional_experience(self, data: dict) -> None:
        if data:
            if "start_date" in data:
                data["start_date"] = normalize_date(data["start_date"])
            if "end_date" in data:
                data["end_date"] = normalize_date(data["end_date"])

            # ✅ Filter invalid keys safely
            allowed_fields = {f.name for f in ProfessionalExperience._meta.get_fields()}
            clean_data = {k: v for k, v in data.items() if k in allowed_fields}
            ProfessionalExperience.objects.create(**clean_data, applicant=self.applicant)

    def _extract_text_data_from_pdf(self) -> str:
        if not getattr(self.applicant.resume, "path", None):
            return ""
        try:
            file_path = os.path.abspath(self.applicant.resume.path)
            doc = fitz.open(file_path)
            text = ""
            for i, page in enumerate(doc):
                text += page.get_text() + "\n"
                if i >= 2:  # only first 3 pages
                    break
            doc.close()
            return text.strip()
        except Exception as e:
            print(f"Error reading PDF {self.applicant.resume}: {e}")
            return ""

    def parse_resume(self):
        if not self.text:
            return {}
        try:
            response = self.openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": self.text},
                    {"role": "user",
                     "content": f"Job Title: {self.applicant.job_applied.job_title}\n"
                                f"Job Description: {self.applicant.job_applied.job_description}"},
                ],
                functions=base_function_prompt,
                function_call="auto",
                temperature=1,
                max_tokens=2000,
                top_p=1,
            )

            # ✅ Fixed for latest SDK
            arguments = None
            if hasattr(response.choices[0].message, "function_call"):
                arguments = response.choices[0].message.function_call.arguments
            elif hasattr(response.choices[0].message, "function"):
                arguments = response.choices[0].message.function.arguments

            return json.loads(arguments) if arguments else {}
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return {}

    def explain_ranking(self) -> str:
        """Generate explanation for applicant using OpenAI."""
        if not self.text or not self.applicant.job_applied:
            return "No resume text or job info available."
        try:
            response = self.openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user",
                           "content": f"Resume:\n{self.text}\n\nJob Title: {self.applicant.job_applied.job_title}\n"
                                      f"Job Description:\n{self.applicant.job_applied.job_description}\n"
                                      f"Explain in 2-3 sentences why this candidate is suitable for the job."}],
                temperature=0.7,
                max_tokens=200
            )
            explanation = response.choices[0].message.content.strip()
            self.applicant.explanation = explanation
            self.applicant.save(update_fields=["explanation"])
            return explanation
        except Exception as e:
            print(f"OpenAI explanation error: {e}")
            return "No explanation available."

    def populate_fields(self):
        """Parse resume, populate fields, and generate explanation."""
        final_data = self.parse_resume()
        if not final_data:
            return

        self._update_resume(final_data.get("profile", {}), final_data.get("relevance", 0))

        if final_data.get("college"):
            self._create_college(final_data.get("college"))

        for project in (final_data.get("projects") or []):
            self._create_project(project)

        for exp in (final_data.get("professional_experiences") or []):
            self._create_professional_experience(exp)

        self.explain_ranking()


# ---------------------------
# Helper functions for batch processing
# ---------------------------
def handle_applicant(file_path: str, job: Job):
    serializer = ApplicantSerializer(data={"resume": file_path, "job_applied": job.u_id})
    if not serializer.is_valid():
        return {"success": False, "errors": serializer.errors}
    applicant = serializer.save()
    try:
        handler = ApplicantHandler(applicant)
        handler.populate_fields()
        return {"success": True, "message": "Resume added successfully", "resume": serializer.data}
    except Exception as e:
        applicant.delete()
        return {"success": False, "message": str(e), "resume": serializer.data}


def manage_pdf_files(files: list, job: Job):
    responses = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(handle_applicant, f, job): f for f in files}
        for future in as_completed(futures):
            try:
                responses.append(future.result())
            except Exception as e:
                print(f"Error processing {futures[future]}: {e}")
    return responses


# ---------------------------
# Aliases
# ---------------------------
add_candidate = handle_applicant
extract_profile = ApplicantHandler.parse_resume
rank_resumes_for_job = manage_pdf_files
