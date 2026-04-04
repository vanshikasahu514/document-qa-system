# DocQA (Django) — Document Question Answering System

A fully local, privacy-first PDF Q&A system built with **Django**. Upload any PDF and ask questions in natural language — answers are extracted only from your document, with no external APIs.

---

## 🏗 Architecture

```
PDF Upload ──► Text Extraction (pdfminer.six)
                      │
                 Word-level Chunking (400w, 80w overlap)
                      │
              Embedding (sentence-transformers: all-MiniLM-L6-v2)
                      │
              Stored in memory (numpy arrays)
                      │
Question ──► Embed Question ──► Cosine Similarity ──► Top-5 Chunks
                                                            │
                                             QA Model (roberta-base-squad2)
                                                            │
                                              Answer + Confidence + Sources
```

### Key components

| Layer | Tech | Purpose |
|-------|------|---------|
| Web framework | Django 4.2+ | Views, routing, sessions, ORM |
| Database | SQLite (via Django ORM) | Store document metadata |
| PDF parsing | `pdfminer.six` | Extract text from PDFs |
| Embeddings | `all-MiniLM-L6-v2` | Encode text chunks & questions |
| Retrieval | NumPy cosine similarity | Find relevant chunks |
| QA model | `deepset/roberta-base-squad2` | Extract answer spans |
| Frontend | Vanilla JS + CSS | Chat UI, drag-and-drop |

---

## 🚀 Setup & Run

### 1. Clone the project
```bash
git clone https://github.com/yourusername/doc-qa-django.git
cd doc-qa-django
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```
> **Note:** First run downloads ML models (~500 MB). This is automatic and happens only once.

### 4. Run migrations
```bash
python manage.py migrate
```

### 5. (Optional) Create admin user
```bash
python manage.py createsuperuser
```

### 6. Start the development server
```bash
python manage.py runserver
```

### 7. Open the app
```
http://127.0.0.1:8000/
```

Admin panel (if you created a superuser):
```
http://127.0.0.1:8000/admin/
```

---

##  Project Structure

```
doc-qa-django/
├── manage.py
├── requirements.txt
├── README.md
├── db.sqlite3              ← Auto-created on first migrate
├── uploads/                ← PDF files saved here
│
├── config/                 ← Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
└── qa/                     ← Main Django app
    ├── models.py           ← Document model (UUID pk, metadata)
    ├── views.py            ← IndexView, UploadView, AskView, DocInfoView
    ├── urls.py             ← App URL patterns
    ├── forms.py            ← UploadDocumentForm, AskQuestionForm
    ├── qa_engine.py        ← Core QA logic (singleton)
    ├── admin.py            ← Django admin registration
    ├── templates/qa/
    │   └── index.html      ← Single-page UI (uses Django template tags)
    └── static/qa/
        ├── css/style.css
        └── js/app.js
```

---

## 🌐 API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/` | Main UI |
| POST | `/upload/` | Upload & process PDF |
| POST | `/ask/` | Ask a question (JSON body) |
| GET | `/doc-info/` | Get current document metadata |
| GET | `/admin/` | Django admin panel |

### POST `/upload/`
Form data: `file` (PDF), `csrfmiddlewaretoken`

Response:
```json
{
  "success": true,
  "doc_id": "uuid",
  "filename": "report.pdf",
  "num_words": 4200,
  "num_chunks": 18
}
```

### POST `/ask/`
```json
{ "question": "What is the main topic?", "doc_id": "uuid" }
```
Response:
```json
{
  "answer": "The main topic is...",
  "confidence": 82.4,
  "sources": [
    { "text": "excerpt...", "similarity": 0.87 }
  ]
}
```

---

## ⚙ Configuration

Tune these in `qa/qa_engine.py`:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `chunk_size` | 400 words | Size of each text chunk |
| `overlap` | 80 words | Overlap between chunks |
| `top_k` | 5 | Chunks retrieved per question |

---

##  Limitations

- Image-based / scanned PDFs are not supported (no OCR)
- Very large PDFs (100+ pages) may take 15–30 seconds to process
- In-memory embeddings reset on server restart (metadata stays in DB, file re-indexes automatically on next question)

---

##  Privacy

Everything runs **100% locally**. No data is sent to any external server or API.
