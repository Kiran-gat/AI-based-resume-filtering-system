from django.urls import path
from .views import (
    JobListAPI,
    JobCreateAPI,
    ApplicantListAPI,
    ApplicantSummaryAPI,
    ResumeUploadAPI,
    ResumeUploadWithJobAPI,
)

urlpatterns = [
    # ---------------------------
    # Job API Endpoints
    # ---------------------------
    path("jobs/", JobListAPI.as_view(), name="job-list"),             # GET: list all jobs
    path("jobs/create/", JobCreateAPI.as_view(), name="job-create"),  # POST: create a new job

    # ---------------------------
    # Applicant API Endpoints
    # ---------------------------
    path("jobs/<uuid:job_u_id>/applicants/", ApplicantListAPI.as_view(), name="applicant-list"),  # GET applicants by job
    path("applicants/<uuid:u_id>/summary/", ApplicantSummaryAPI.as_view(), name="applicant-summary"),  # GET single applicant summary

    # ---------------------------
    # Resume Upload APIs
    # ---------------------------
    path("resumes/upload/", ResumeUploadAPI.as_view(), name="resume-upload"),  # POST resumes without creating job
    path("resumes/upload-with-job/", ResumeUploadWithJobAPI.as_view(), name="resume-upload-with-job"),  # POST resumes with job creation

    # Alias for frontend or Thunder Client POST
    path("post-resume-with-job/", ResumeUploadWithJobAPI.as_view(), name="post-resume-with-job"),

    # ---------------------------
    # Frontend-specific Endpoints
    # ---------------------------
    path("get-applicant-list/<uuid:job_u_id>/", ApplicantListAPI.as_view(), name="get-applicant-list"),  # GET applicants (rec/norec)
    path("get-applicant-summary/<uuid:u_id>/", ApplicantSummaryAPI.as_view(), name="get-applicant-summary"),  # GET applicant summary

    # Backward compatibility / old frontend
    path("result/<uuid:job_u_id>/", ApplicantListAPI.as_view(), name="frontend-result"),
]
