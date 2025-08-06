from sentence_transformers import SentenceTransformer
import faiss
import numpy as np


class ModuleIndexer:
    def __init__(self, modules, progress_callback=None):
        self.modules = modules
        self.progress_callback = progress_callback
        
        if self.progress_callback:
            self.progress_callback("Loading AI model...", 45)
        
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        
        if self.progress_callback:
            self.progress_callback("Generating embeddings...", 70)
        
        self.embeddings = self.model.encode(
            [f"{m['config']}: {m['desc']}" for m in self.modules]
        )
        
        if self.progress_callback:
            self.progress_callback("Building search index...", 85)
        
        self.index = self._build_index()
        
        if self.progress_callback:
            self.progress_callback("Complete!", 100)

    def _build_index(self):
        dim = self.embeddings[0].shape[0]
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(self.embeddings))
        return index

    def search(self, query, k=20):
        query_vec = self.model.encode([query])
        _, idxs = self.index.search(query_vec, k)
        return [self.modules[i] for i in idxs[0]]
