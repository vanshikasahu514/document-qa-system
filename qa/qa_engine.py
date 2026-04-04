"""
QA Engine - Document Question Answering System
Handles PDF extraction, chunking, embedding, retrieval and answering.
100% local - no external APIs.
"""

import re
import numpy as np
from typing import List, Tuple, Dict


class QAEngine:
    """Singleton-style engine stored in Django's app registry."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._embedder = None
            cls._instance._qa_pipeline = None
            cls._instance._store: Dict[str, dict] = {}  # doc_id -> data
        return cls._instance

    # ── Lazy model loaders ─────────────────────────────────────
    def _get_embedder(self):
        if self._embedder is None:
            print("[QAEngine] Loading sentence-transformer...")
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer('all-MiniLM-L6-v2')
            print("[QAEngine] Embedder ready.")
        return self._embedder

    def _get_qa_pipeline(self):
        if self._qa_pipeline is None:
            print("[QAEngine] Loading QA model...")
            from transformers import pipeline
            self._qa_pipeline = pipeline(
                'question-answering',
                model='deepset/roberta-base-squad2',
            )
            print("[QAEngine] QA model ready.")
        return self._qa_pipeline

    # ── PDF extraction ─────────────────────────────────────────
    def extract_text(self, filepath: str) -> str:
        from pdfminer.high_level import extract_text
        text = extract_text(filepath)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    # ── Chunking ───────────────────────────────────────────────
    def chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 80) -> List[str]:
        words = text.split()
        chunks, start = [], 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk = ' '.join(words[start:end])
            if chunk.strip():
                chunks.append(chunk)
            if end == len(words):
                break
            start += chunk_size - overlap
        return chunks

    # ── Process & store document ───────────────────────────────
    def process_document(self, filepath: str, doc_id: str) -> dict:
        text = self.extract_text(filepath)
        if not text or len(text) < 50:
            raise ValueError("Could not extract readable text. The PDF may be image-based.")

        chunks = self.chunk_text(text)
        if not chunks:
            raise ValueError("Document is empty after processing.")

        print(f"[QAEngine] Embedding {len(chunks)} chunks for doc {doc_id}...")
        embedder = self._get_embedder()
        embeddings = embedder.encode(chunks, show_progress_bar=False, normalize_embeddings=True)

        self._store[str(doc_id)] = {
            'chunks': chunks,
            'embeddings': np.array(embeddings, dtype='float32'),
            'full_text': text,
        }

        return {
            'num_chunks': len(chunks),
            'num_words': len(text.split()),
            'num_chars': len(text),
        }

    # ── Retrieval ──────────────────────────────────────────────
    def retrieve(self, doc_id: str, question: str, top_k: int = 5) -> List[Tuple[str, float]]:
        doc = self._store.get(str(doc_id))
        if not doc:
            raise ValueError("Document not found in memory. Please re-upload.")
        embedder = self._get_embedder()
        q_emb = embedder.encode([question], normalize_embeddings=True)[0]
        scores = np.dot(doc['embeddings'], q_emb)
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [(doc['chunks'][i], float(scores[i])) for i in top_idx]

    # ── Answer ─────────────────────────────────────────────────
    def answer(self, doc_id: str, question: str) -> dict:
        top_chunks = self.retrieve(doc_id, question, top_k=5)
        context = ' '.join(c for c, _ in top_chunks)

        qa = self._get_qa_pipeline()
        result = qa(question=question, context=context, max_answer_len=200)
        best = result

        if result['score'] < 0.15:
            for chunk, _ in top_chunks:
                try:
                    r = qa(question=question, context=chunk, max_answer_len=200)
                    if r['score'] > best['score']:
                        best = r
                except Exception:
                    pass

        sources = [
            {'text': c[:300] + ('...' if len(c) > 300 else ''), 'similarity': round(s, 3)}
            for c, s in top_chunks[:3]
        ]

        return {
            'answer': best['answer'].strip() or "No specific answer found in the document.",
            'confidence': round(best['score'] * 100, 1),
            'sources': sources,
        }

    def is_loaded(self, doc_id: str) -> bool:
        return str(doc_id) in self._store


# Global singleton
engine = QAEngine()
