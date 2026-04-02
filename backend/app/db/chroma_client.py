from pathlib import Path

import chromadb

CHROMA_PATH = Path(__file__).resolve().parents[3] / "storage" / "chroma"

client = chromadb.PersistentClient(path=str(CHROMA_PATH))
