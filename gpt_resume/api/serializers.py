from rest_framework import serializers
from .models import Job, Applicant, College, Project, ProfessionalExperience


# ---------------------------
# Job Serializer
# ---------------------------
class JobSerializer(serializers.ModelSerializer):
    u_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Job
        fields = '__all__'


# ---------------------------
# College Serializer
# ---------------------------
class CollegeSerializer(serializers.ModelSerializer):
    explanation = serializers.CharField(read_only=True)

    class Meta:
        model = College
        fields = [
            'name',
            'branch',
            'degree',
            'start_date',
            'end_date',
            'explanation'
        ]


# ---------------------------
# Project Serializer
# ---------------------------
class ProjectSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='title')
    short_description = serializers.CharField(source='description')
    relevancy = serializers.IntegerField(source='relevance', read_only=True)
    explanation = serializers.CharField(read_only=True)

    class Meta:
        model = Project
        fields = [
            'project_title',
            'short_description',
            'tech_stack',
            'time_duration',
            'relevancy',
            'explanation'
        ]


# ---------------------------
# Professional Experience Serializer
# ---------------------------
class ProfessionalExperienceSerializer(serializers.ModelSerializer):
    short_description = serializers.CharField(source='description')
    relevancy = serializers.IntegerField(source='relevance', read_only=True)
    explanation = serializers.CharField(read_only=True)

    class Meta:
        model = ProfessionalExperience
        fields = [
            'role',
            'organization',
            'short_description',
            'tech_stack',
            'time_duration',
            'relevancy',
            'explanation'
        ]


# ---------------------------
# Applicant Serializer
# ---------------------------
class ApplicantSerializer(serializers.ModelSerializer):
    u_id = serializers.UUIDField(read_only=True)
    parsed = serializers.JSONField(read_only=True)
    explanation = serializers.CharField(read_only=True)

    class Meta:
        model = Applicant
        exclude = ['resume_text']
        extra_kwargs = {
            "name": {"read_only": True},
            "email": {"read_only": True},
            "relevance": {"read_only": True},
            "job_applied": {"write_only": True},
        }


# ---------------------------
# Applicant Summary Serializer
# ---------------------------
class ApplicantSummarySerializer(serializers.ModelSerializer):
    u_id = serializers.UUIDField(read_only=True)
    college = serializers.SerializerMethodField()
    projects = serializers.SerializerMethodField()
    professional_experiences = serializers.SerializerMethodField()
    parsed = serializers.JSONField(read_only=True)
    explanation = serializers.CharField(read_only=True)

    class Meta:
        model = Applicant
        exclude = ['job_applied', 'resume_text']

    def get_college(self, obj):
        qs = getattr(obj, 'colleges', None) or obj.college_set.all()
        return (
            CollegeSerializer(qs.order_by('-end_date'), many=True).data
            if qs.exists() else []
        )

    def get_projects(self, obj):
        qs = getattr(obj, 'projects', None) or obj.project_set.all()
        return (
            ProjectSerializer(qs.order_by('-relevance'), many=True).data
            if qs.exists() else []
        )

    def get_professional_experiences(self, obj):
        qs = getattr(obj, 'professional_experiences', None) or obj.professionalexperience_set.all()
        return (
            ProfessionalExperienceSerializer(qs.order_by('-relevance'), many=True).data
            if qs.exists() else []
        )
