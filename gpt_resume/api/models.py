import os
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator


class Document(models.Model):
    """
    Stores uploaded resume files.
    """
    document = models.FileField(
        upload_to="resumes/",
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
        verbose_name="Applicant's Resume",
    )

    def __str__(self):
        try:
            name = getattr(self.document, "name", None)
            return os.path.basename(name) if name else str(self.id)
        except Exception:
            return str(self.id)


class Job(models.Model):
    """
    Job posting model.
    """
    u_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_title = models.TextField(blank=False, verbose_name="Job Title")
    job_description = models.TextField(blank=False, verbose_name="Job Description")

    def __str__(self):
        if self.job_title:
            return (self.job_title[:80] + "...") if len(self.job_title) > 80 else self.job_title
        return str(self.u_id)


class Applicant(models.Model):
    """
    Applicant record.
    """
    u_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField(blank=True, verbose_name="Applicant's Name")
    email = models.EmailField(blank=True, verbose_name="Applicant's Email")
    resume = models.FileField(
        upload_to="resumes/",
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
        verbose_name="Applicant's Resume File",
    )
    resume_text = models.TextField(blank=True, verbose_name="Extracted Resume Text")
    parsed = models.JSONField(blank=True, null=True, verbose_name="Parsed Resume Data")
    job_applied = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applicants", verbose_name="Job Applied For")
    relevance = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Relevance Score",
    )
    embedding_stored = models.BooleanField(default=False, verbose_name="Embedding Stored Flag")
    
    # ✅ Already exists (keep it)
    explanation = models.TextField(blank=True, verbose_name="AI Ranking Explanation")

    def __str__(self):
        return self.name or str(self.u_id)


class College(models.Model):
    """
    College details. Each applicant may have multiple colleges (e.g., undergrad + masters).
    """
    u_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField(blank=True, verbose_name="College Name")
    branch = models.TextField(blank=True, verbose_name="Branch of Study")
    degree = models.TextField(blank=True, verbose_name="Degree")
    start_date = models.DateField(blank=True, null=True, verbose_name="Start Date")
    end_date = models.DateField(blank=True, null=True, verbose_name="End Date")
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name="colleges")

    # ✅ New field
    explanation = models.TextField(blank=True, verbose_name="Relevance Explanation")

    def __str__(self):
        return f"{self.name or 'College'} - {self.degree or ''}"


class Project(models.Model):
    """
    Projects related to an applicant.
    """
    u_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.TextField(blank=True, verbose_name="Project Title")
    description = models.TextField(blank=True, verbose_name="Project Description")
    tech_stack = models.JSONField(blank=True, null=True, default=list, verbose_name="Tech Stack Used")
    time_duration = models.JSONField(blank=True, null=True, default=dict, verbose_name="Time Duration")
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name="projects")
    relevance = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="Project Relevance Score",
    )
    
    # ✅ New field
    explanation = models.TextField(blank=True, verbose_name="Project Relevance Explanation")

    def __str__(self):
        return self.title or f"Project {self.u_id}"


class ProfessionalExperience(models.Model):
    """
    Professional experiences for an applicant.
    """
    u_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.TextField(blank=True, verbose_name="Role")
    organization = models.TextField(blank=True, null=True, verbose_name="Organization Name")
    description = models.TextField(blank=True, verbose_name="Description")
    tech_stack = models.JSONField(blank=True, null=True, default=list, verbose_name="Tech Stack Used")
    time_duration = models.JSONField(blank=True, null=True, default=dict, verbose_name="Time Duration")
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name="professional_experiences")
    relevance = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name="Experience Relevance Score",
    )
    
    # ✅ New field
    explanation = models.TextField(blank=True, verbose_name="Experience Relevance Explanation")

    def __str__(self):
        return f"{self.role or 'Experience'} @ {self.organization or ''}"
