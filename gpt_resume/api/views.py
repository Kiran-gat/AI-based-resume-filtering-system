from rest_framework import generics, views, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.core.files.storage import FileSystemStorage
from django.core.files import File
import uuid, os, logging
from sentence_transformers import SentenceTransformer, util

from .models import Job, Applicant
from .serializers import JobSerializer, ApplicantSerializer, ApplicantSummarySerializer
from .utils.resume_dispatcher import ApplicantHandler

logger = logging.getLogger(__name__)

# Load SBERT once
embedder = SentenceTransformer("all-MiniLM-L6-v2")


# ---------------------------
# Job APIs
# ---------------------------
class JobListAPI(generics.ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = JobSerializer
    queryset = Job.objects.all()


class JobCreateAPI(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = JobSerializer


# ---------------------------
# Applicant APIs
# ---------------------------
class ApplicantListAPI(generics.ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ApplicantSerializer

    def get_queryset(self):
        job_u_id = self.kwargs.get("job_u_id")
        job = Job.objects.filter(u_id=job_u_id).first()
        if not job:
            logger.warning(f"Job {job_u_id} not found")
            # return empty queryset instead of raising so frontend gets 200 + empty list
            return Applicant.objects.none()

        type_param = self.request.query_params.get("type", "")
        # safe job description fallback
        job_text = job.job_description or ""
        if not job_text.strip():
            logger.warning(f"Job {job.u_id} has empty description")
            return Applicant.objects.filter(job_applied=job).order_by("-relevance")

        # compute job embedding once
        try:
            job_embedding = embedder.encode(job_text, convert_to_tensor=True)
        except Exception as e:
            logger.exception(f"Failed to encode job description for job {job.u_id}: {e}")
            return Applicant.objects.filter(job_applied=job).order_by("-relevance")

        applicants_qs = Applicant.objects.filter(job_applied=job)

        # update relevance only for applicants missing embeddings
        for applicant in applicants_qs:
            parsed_text = ""
            if applicant.parsed:
                # parsed can be dict or string; handle both
                parsed_text = applicant.parsed.get("text", "") if isinstance(applicant.parsed, dict) else str(applicant.parsed)
            parsed_text = (parsed_text or applicant.resume_text or "").strip()

            # skip if no text available
            if not parsed_text:
                continue

            if not getattr(applicant, "embedding_stored", False):
                try:
                    resume_embedding = embedder.encode(parsed_text, convert_to_tensor=True)
                    score = util.cos_sim(job_embedding, resume_embedding).item() * 100
                    applicant.relevance = int(round(score))
                    # only set embedding attr if model has such a field (safe)
                    if hasattr(applicant, "embedding"):
                        applicant.embedding = resume_embedding.tolist()
                        update_fields = ["relevance", "embedding_stored", "embedding"]
                    else:
                        update_fields = ["relevance", "embedding_stored"]

                    applicant.embedding_stored = True
                    applicant.save(update_fields=update_fields)
                except Exception as e:
                    logger.exception(f"Embedding failed for applicant {getattr(applicant, 'u_id', 'unknown')}: {e}")

        # Queryset filtering by type with a tunable threshold (default 50)
        threshold = int(self.request.query_params.get("threshold", 50))
        queryset = applicants_qs
        if type_param == "rec":
            queryset = queryset.filter(relevance__gte=threshold)
        elif type_param == "norec":
            queryset = queryset.filter(relevance__lt=threshold)

        return queryset.order_by("-relevance")


class ApplicantSummaryAPI(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ApplicantSummarySerializer

    def get_object(self):
        u_id = self.kwargs.get("u_id")
        return Applicant.objects.filter(u_id=u_id).first()


# ---------------------------
# Helper: Process resume
# ---------------------------
def process_resume(file_obj, job, fs, job_embedding):
    try:
        # Use base filename to avoid Windows absolute-path issues
        original_name = os.path.basename(getattr(file_obj, "name", str(file_obj)))
        filename = f"{uuid.uuid4()}_{original_name}"

        # fs.save returns the saved filename (relative to FS location)
        saved_name = fs.save(filename, file_obj)
        file_path = fs.path(saved_name)

        # Create applicant *without* attempting to re-save the uploaded file by Django.
        applicant = Applicant.objects.create(job_applied=job)
        # set the resume field to a relative path that Django understands.
        applicant.resume.name = os.path.join("resumes", saved_name) if not saved_name.startswith("resumes/") else saved_name
        applicant.save(update_fields=["resume"])

        # Parse and populate applicant using existing handler
        handler = ApplicantHandler(applicant)
        handler.populate_fields()

        # Compute relevance (if parsed text exists)
        parsed_text = applicant.parsed.get("text", "") if applicant.parsed and isinstance(applicant.parsed, dict) else (applicant.parsed or applicant.resume_text or "")
        if parsed_text and str(parsed_text).strip():
            try:
                resume_embedding = embedder.encode(str(parsed_text), convert_to_tensor=True)
                score = util.cos_sim(job_embedding, resume_embedding).item() * 100
                applicant.relevance = int(round(score))
                applicant.embedding_stored = True
                # set embedding only if field exists
                if hasattr(applicant, "embedding"):
                    applicant.embedding = resume_embedding.tolist()
                    applicant.save(update_fields=["relevance", "embedding_stored", "embedding"])
                else:
                    applicant.save(update_fields=["relevance", "embedding_stored"])
            except Exception as e:
                logger.exception(f"Failed to compute embedding for applicant {applicant.u_id}: {e}")

        return {
            "applicant_id": str(applicant.u_id),
            "filename": original_name,
            "relevance": applicant.relevance,
            "parsed": applicant.parsed,
        }

    except Exception as e:
        logger.exception(f"Error processing resume {getattr(file_obj, 'name', 'unknown')}: {str(e)}")
        return {"filename": getattr(file_obj, "name", "unknown"), "error": str(e)}


# ---------------------------
# Resume Upload for Existing Job
# ---------------------------
class ResumeUploadAPI(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        job_u_id = request.data.get("job_u_id")
        if not job_u_id:
            return Response({"message": "Job id not found"}, status=status.HTTP_400_BAD_REQUEST)

        job = Job.objects.filter(u_id=job_u_id).first()
        if not job:
            return Response({"message": "Job not found"}, status=status.HTTP_400_BAD_REQUEST)

        files = request.FILES.getlist("files")
        if not files:
            return Response({"message": "No files uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        fs = FileSystemStorage(location="media/resumes")
        job_embedding = embedder.encode(job.job_description, convert_to_tensor=True)
        responses = [process_resume(file, job, fs, job_embedding) for file in files]

        return Response({
            "message": "Resumes uploaded successfully",
            "job_u_id": str(job.u_id),
            "data": responses,
        }, status=status.HTTP_201_CREATED)


# ---------------------------
# Resume Upload With New Job
# ---------------------------
class ResumeUploadWithJobAPI(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        job_title = request.data.get("job_title")
        job_description = request.data.get("job_description")
        documents = request.FILES.getlist("files")

        if not job_title or not job_description:
            return Response({"message": "Job title and description are required"},
                            status=status.HTTP_400_BAD_REQUEST)
        if not documents:
            return Response({"message": "No resumes uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        job = Job.objects.create(job_title=job_title, job_description=job_description)

        fs = FileSystemStorage(location="media/resumes")
        job_embedding = embedder.encode(job.job_description, convert_to_tensor=True)
        responses = [process_resume(doc, job, fs, job_embedding) for doc in documents]

        return Response({
            "message": "Resumes uploaded successfully",
            "job_u_id": str(job.u_id),
            "data": responses,
        }, status=status.HTTP_201_CREATED)
