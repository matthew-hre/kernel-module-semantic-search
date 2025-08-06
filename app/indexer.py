from sentence_transformers import SentenceTransformer
import faiss
import numpy as np


class ModuleIndexer:
    def __init__(self, modules):
        self.modules = modules
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embeddings = self.model.encode(
            [f"{m['name']}: {m['desc']}" for m in self.modules]
        )
        self.index = self._build_index()

    def _build_index(self):
        dim = self.embeddings[0].shape[0]
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(self.embeddings))
        return index

    def search(self, query, k=20):
        query_vec = self.model.encode([query])
        _, idxs = self.index.search(query_vec, k)
        return [self.modules[i] for i in idxs[0]]
