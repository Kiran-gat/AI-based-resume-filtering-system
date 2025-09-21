# test_resume_filter.py
import os
import numpy as np
from resume_parser import extract_resume_text, extract_entities, build_faiss_index, search_best_resumes

# Folder with resumes
RESUME_FOLDER = "sample_resumes"
RESUME_FOLDER = r"C:\Users\blgrk\resumeProject\gpt-resume\sample_resume"



# Dummy embedding function (replace later with OpenAI embeddings)
def embed_text(text):
    # Convert each character to ASCII and normalize
    vec = np.array([ord(c) for c in text[:300]])  # limit length
    vec = np.pad(vec, (0, 300 - len(vec)), 'constant')  # fixed size
    return vec.astype("float32").reshape(1, -1)

if __name__ == "__main__":
    resumes = []
    embeddings = []

    # Load all resumes
    for filename in os.listdir(RESUME_FOLDER):
        if filename.endswith(".pdf"):
            file_path = os.path.join(RESUME_FOLDER, filename)
            print(f"\n📄 Parsing {filename}...")
            
            text = extract_resume_text(file_path)
            entities = extract_entities(text)
            
            print("Extracted Entities:", entities)
            
            resumes.append(filename)
            embeddings.append(embed_text(text))

    # Convert embeddings list to FAISS-compatible array
    embeddings = np.vstack(embeddings)
    
    # Build FAISS index
    index = build_faiss_index(embeddings)

    # Test a query
    query = "Looking for a Python and Machine Learning expert"
    query_vec = embed_text(query)
    distances, indices = search_best_resumes(index, query_vec, top_k=2)

    print("\n🔎 Best matching resumes:")
    for i, idx in enumerate(indices[0]):
        print(f"{i+1}. {resumes[idx]} (score: {distances[0][i]})")
