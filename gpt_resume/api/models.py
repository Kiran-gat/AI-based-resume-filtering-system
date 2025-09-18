# gpt_resume/api/models.py
import os
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator


class Document(models.Model):
    """
    Stores uploaded resume files. FileField enforces PDF extension via validator.
    """
    document = models.FileField(
        upload_to="resume/",
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
    Job posting model. Uses UUID as primary key.
    """
    u_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_title = models.TextField(blank=False, verbose_name="Job Title")
    job_description = models.TextField(blank=False, verbose_name="Job Description")

    def __str__(self):
        # Keep it short for admin display
        return (self.job_title[:80] + "...") if len(self.job_title or "") > 80 else (self.job_title or str(self.u_id))


class Applicant(models.Model):
    """
    Applicant record. 'resume' stores the path or URL to the resume (string).
    'resume_text' stores extracted text (optional).
    """
    u_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField(blank=True, verbose_name="Applicant's Name")
    email = models.EmailField(blank=True, verbose_name="Applicant's Email")
    resume = models.TextField(blank=False, verbose_name="Applicant's Resume Path")
    resume_text = models.TextField(blank=True, verbose_name="Applicant's Resume Text Content")
    job_applied = models.ForeignKey(Job, on_delete=models.CASCADE, verbose_name="Job Applied For")
    relevance = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Relevance Score",
    )

    def __str__(self):
        return self.name or str(self.u_id)


class College(models.Model):
    """
    College details. One-to-one with Applicant (single college record per applicant).
    """
    u_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField(blank=True, verbose_name="College Name")
    branch = models.TextField(blank=True, verbose_name="Branch of Study")
    degree = models.TextField(blank=True, verbose_name="Degree")
    # max_length=7 suggests YYYY-MM format; kept as-is
    start_date = models.CharField(max_length=7, blank=True, null=True, verbose_name="Start Date")
    end_date = models.CharField(max_length=7, blank=True, null=True, verbose_name="End Date")
    applicant = models.OneToOneField(Applicant, on_delete=models.CASCADE, related_name="college")

    def __str__(self):
        return f"{self.name or 'College'} - {self.degree or ''}"


class Project(models.Model):
    """
    Project entries related to an applicant. tech_stack and time_duration are JSON fields.
    Defaults prevent missing-key errors when creating instances without these fields.
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
        verbose_name="Relevance Score",
    )

    def __str__(self):
        return self.title or f"Project {self.u_id}"


class ProfessionalExperience(models.Model):
    """
    Professional experience entries for an applicant.
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
        verbose_name="Relevance Score",
    )

    def __str__(self):
        return f"{self.role or 'Experience'} @ {self.organization or ''}"
