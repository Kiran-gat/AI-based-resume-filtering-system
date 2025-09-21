import os
import re
import docx
import numpy as np
import faiss
import spacy
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from pdfminer.high_level import extract_text

# -------------------------------
# Load NLP models once
# -------------------------------
nlp = spacy.load("en_core_web_sm")
kw_model = KeyBERT()
embedder = SentenceTransformer("all-MiniLM-L6-v2")


# -------------------------------
# Extract text from resumes
# -------------------------------
def extract_resume_text(file_path: str) -> str:
    text = ""
    try:
        if file_path.endswith(".pdf"):
            text = extract_text(file_path)
        elif file_path.endswith(".docx"):
            doc = docx.Document(file_path)
            text = " ".join([p.text for p in doc.paragraphs])
        elif file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        # Normalize text
        text = re.sub(r'\s+', ' ', text).strip()
    except Exception as e:
        print(f"[ERROR] Failed to extract text from {file_path}: {e}")
    return text


# -------------------------------
# Extract structured entities
# -------------------------------
def extract_entities(text: str, top_n_keywords: int = 10) -> dict:
    doc = nlp(text)
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}", text)

    # Extract names using spaCy
    names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]

    # Extract keywords/skills using KeyBERT
    skills = [kw[0] for kw in kw_model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 2),
        stop_words="english",
        top_n=top_n_keywords
    )]

    return {
        "names": names,
        "emails": emails,
        "skills": skills
    }


# -------------------------------
# Get embedding for a text
# -------------------------------
def get_embedding(text: str) -> np.ndarray:
    vec = embedder.encode([text])[0]
    return np.array(vec, dtype="float32")


# -------------------------------
# Build FAISS index from resume texts
# -------------------------------
def build_faiss_index(resume_texts: list):
    embeddings = [get_embedding(text) for text in resume_texts if text.strip()]
    if not embeddings:
        raise ValueError("No valid resume texts found.")

    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings).astype("float32"))

    return index, embeddings


# -------------------------------
# Search best resumes given a job description
# -------------------------------
def search_best_resumes(job_desc: str, index, resumes: list, top_k: int = 3):
    """
    Returns top_k resumes most similar to the job description.
    Uses L2 distance; lower is better.
    """
    job_vector = get_embedding(job_desc)
    D, I = index.search(np.array([job_vector]), k=top_k)

    results = []
    for j, i in enumerate(I[0]):
        results.append({
            "resume": resumes[i],
            "distance": float(D[0][j])  # Lower distance = better match
        })

    return results
