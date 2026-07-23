"""Run during Docker build to pre-download model weights into the image cache,
so the container doesn't fetch them from the internet at runtime/startup."""
import os

from sentence_transformers import SentenceTransformer

TEXT_MODEL_NAME = os.getenv("TEXT_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
CLIP_MODEL_NAME = os.getenv("CLIP_MODEL_NAME", "sentence-transformers/clip-ViT-B-32")

print(f"Downloading {TEXT_MODEL_NAME} ...")
SentenceTransformer(TEXT_MODEL_NAME)

print(f"Downloading {CLIP_MODEL_NAME} ...")
SentenceTransformer(CLIP_MODEL_NAME)

print("Done.")
