import os
import re
import fitz  # PyMuPDF
import docx
import numpy as np
import faiss

# ---------------------------
# Extract text from PDF, DOCX, or TXT
# ---------------------------
def extract_resume_text(file_path):
    """
    Extracts text from PDF, DOCX, or TXT for better coverage.
    """
    text = ""
    try:
        file_path = file_path.strip()
        if file_path.lower().endswith(".pdf"):
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text("text") + "\n"

        elif file_path.lower().endswith(".docx"):
            try:
                doc = docx.Document(file_path)
                text = " ".join([p.text for p in doc.paragraphs])
            except Exception as e:
                print(f"[ERROR] Reading DOCX {file_path}: {e}")

        elif file_path.lower().endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

    except Exception as e:
        print(f"[ERROR] Reading file {file_path}: {e}")

    # Normalize text
    text = text.replace("\n", " ").strip()
    text = re.sub(r'\s+', ' ', text)
    return text


# ---------------------------
# Extract structured entities
# ---------------------------
def extract_entities(text):
    """
    Extracts structured information from resume text.
    Returns a dictionary suitable for Applicant.parsed.
    """
    parsed = {}
    parsed["text"] = text or ""

    # ---------------- Email ----------------
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    parsed["email"] = email_match.group(0) if email_match else ""

    # ---------------- Phone ----------------
    phone_match = re.search(r'\+?\d[\d\s\-]{8,15}\d', text)
    parsed["phone"] = phone_match.group(0) if phone_match else ""

    # ---------------- Name ----------------
    if parsed["email"]:
        before_email = text.split(parsed["email"])[0].strip()
        parsed["name"] = " ".join(before_email.split()[:4]) or "Unknown"
    else:
        parsed["name"] = " ".join(text.split()[:4]) if text else "Unknown"

    # ---------------- Colleges ----------------
    colleges = re.findall(
        r'([A-Z][a-zA-Z &]{2,}(?:University|College|Institute|Academy))',
        text
    )
    parsed["college"] = colleges if colleges else []

    # ---------------- Skills ----------------
    skill_list = [
        "Python", "Java", "JavaScript", "React", "Node.js",
        "SQL", "Machine Learning", "Docker", "Django", "Flask",
        "AWS", "C++", "TensorFlow", "Keras", "Pandas"
    ]
    parsed["skills"] = [
        skill for skill in skill_list
        if re.search(rf'\b{re.escape(skill)}\b', text, re.I)
    ]

    # ---------------- Projects ----------------
    projects = []
    proj_matches = re.findall(
        r'(?:Projects?|Portfolio|Work Done)(?:\:|\s)(.*?)(?=(?:Experience|Skills|Education|$))',
        text, flags=re.I | re.DOTALL
    )
    for proj in proj_matches:
        items = re.split(r'•|-|·|\n|\|', proj)
        projects.extend([p.strip() for p in items if p.strip()])
    parsed["projects"] = projects

    # ---------------- Professional Experiences ----------------
    experiences = []
    exp_matches = re.findall(
        r'(?:Experience|Professional Experience|Work History)(?:\:|\s)(.*?)(?=(?:Projects|Skills|Education|$))',
        text, flags=re.I | re.DOTALL
    )
    for exp in exp_matches:
        items = re.split(r'•|-|·|\n', exp)
        experiences.extend([e.strip() for e in items if e.strip()])
    parsed["professional_experiences"] = experiences

    return parsed


# ---------------------------
# Build FAISS index
# ---------------------------
def build_faiss_index(embeddings):
    """
    embeddings: numpy array of shape (num_resumes, embedding_dim)
    """
    embeddings = np.array(embeddings).astype("float32")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index


# ---------------------------
# Search best resumes using FAISS
# ---------------------------
def search_best_resumes(index, query_embedding, top_k=3):
    """
    index: FAISS index
    query_embedding: numpy array of shape (1, embedding_dim)
    """
    query_embedding = np.array(query_embedding).astype("float32")
    if query_embedding.ndim == 1:
        query_embedding = query_embedding.reshape(1, -1)

    distances, indices = index.search(query_embedding, top_k)
    return distances, indices
