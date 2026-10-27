import pathlib, pickle, faiss, numpy as np
from pypdf import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer

def chunk(text, size=800, overlap=150):
    step = size - overlap
    return [text[i:i + size] for i in range(0, len(text), step) if text[i:i + size].strip()]

def load(f):
    """Return a list of (label, text) pairs for a file."""
    if f.suffix.lower() == ".pdf":
        reader = PdfReader(str(f))
        return [(f"{f.name} p.{n}", page.extract_text() or "")
                for n, page in enumerate(reader.pages, start=1)]
    if f.suffix.lower() == ".docx":
        return [(f.name, "\n".join(p.text for p in Document(str(f)).paragraphs))]
    if f.suffix.lower() in {".txt", ".md"}:
        return [(f.name, f.read_text(encoding="utf-8", errors="ignore"))]
    return []

model = SentenceTransformer("all-MiniLM-L6-v2")
chunks, meta = [], []
for folder in ["docs", "notes"]:
    for f in pathlib.Path(folder).glob("**/*"):
        for label, text in load(f):
            for c in chunk(text):
                chunks.append(c)
                meta.append(label)

if not chunks:
    raise SystemExit("No text found. Check that docs/ has readable files.")

emb = model.encode(chunks, normalize_embeddings=True).astype("float32")
index = faiss.IndexFlatIP(emb.shape[1])
index.add(emb)

faiss.write_index(index, "index.faiss")
pickle.dump((chunks, meta), open("chunks.pkl", "wb"))
print(f"Indexed {len(chunks)} chunks from {len(set(m.split(' p.')[0] for m in meta))} files")