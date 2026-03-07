# 📚 Hellobooks AI — Accounting Q&A Assistant

> An AI-powered bookkeeping assistant built with **FastAPI**, **FAISS**, and **Groq LLaMA** using a **Retrieval-Augmented Generation (RAG)** architecture.

## 🖼️ Screenshots

### Home Page
![Home Page](https://github.com/YASH-02042002/HelloBook-AI/blob/611bec85c934bcbc1858bdd0ff9058bad893696f/Home%20page.png)

### Answer Example
![Answer Example](https://github.com/YASH-02042002/HelloBook-AI/blob/7f590266b22c62729e3bbf05793d68589f1f748e/Answer%20page%201.png)

---

## 📖 Overview

Hellobooks AI answers accounting questions by retrieving relevant information from a curated knowledge base and generating clear, contextual answers using Groq LLaMA.

### RAG Flow:
```
User Question
     │
     ▼
Generate Query Embedding (HuggingFace - Local, FREE)
     │
     ▼
Search FAISS Vector Index → Top-K Relevant Chunks
     │
     ▼
Build Prompt with Context
     │
     ▼
Groq LLaMA Generates Answer
     │
     ▼
Return Answer + Sources
```

---

## 🗂️ Project Structure

```
hellobooks/
├── knowledge_base/               # Accounting documents (Markdown)
│   ├── bookkeeping.md
│   ├── invoices.md
│   ├── profit_and_loss.md
│   ├── balance_sheet.md
│   ├── cash_flow.md
│   ├── accounts_payable_receivable.md
│   ├── taxation_gst.md
│   └── financial_ratios.md
│
├── src/
│   ├── rag.py                    # Core RAG engine
│   └── app.py                    # FastAPI web application
│
├── templates/
│   └── index.html                # Web UI
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## ✅ Prerequisites

| Tool | Notes |
|------|-------|
| Python 3.11+ | Or use Docker |
| Groq API Key | Free at [console.groq.com](https://console.groq.com) |
| Docker (optional) | For containerized deployment |

---

## 🚀 Quick Start

### Step 1 — Clone the repository
```bash
git clone https://github.com/YASH-02042002/HelloBook-AI.git
cd HelloBook-AI
```

### Step 2 — Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Setup environment variables
```bash
copy .env.example .env
notepad .env
```
Add your Groq API key:
```
GROQ_API_KEY=gsk_your-key-here
```

### Step 5 — Build vector index
```bash
python src/rag.py --build
```

### Step 6 — Start the server
```bash
python src/app.py
```

### Step 7 — Open in browser
```
http://localhost:8000
```

---

## 🐳 Docker Deployment

```bash
# Build and run
docker compose up --build

# Open browser
http://localhost:8000
```

---

## 🌐 API Reference

### `GET /`
Web UI

### `GET /health`
```json
{ "status": "ok", "index_loaded": true, "vectors": 36 }
```

### `POST /ask`
**Request:**
```json
{ "question": "What is the difference between cash flow and profit?" }
```
**Response:**
```json
{
  "question": "What is the difference between cash flow and profit?",
  "answer": "Cash flow tracks actual money moving in and out...",
  "sources": ["Cash Flow", "Profit And Loss"],
  "chunks": [{ "source": "Cash Flow", "text": "...", "score": 0.87 }]
}
```

### `POST /rebuild-index`
Rebuilds the FAISS index from the knowledge base.

---

## 📚 Knowledge Base Topics

| File | Topics |
|------|--------|
| `bookkeeping.md` | Double-entry system, journals, ledgers |
| `invoices.md` | Invoice types, payment terms, GST |
| `profit_and_loss.md` | Revenue, COGS, gross/net profit, EBITDA |
| `balance_sheet.md` | Assets, liabilities, equity |
| `cash_flow.md` | Operating/investing/financing activities, FCF |
| `accounts_payable_receivable.md` | AR/AP processes, aging reports, DSO |
| `taxation_gst.md` | Income tax, GST, deductions, depreciation |
| `financial_ratios.md` | Liquidity, profitability, solvency ratios |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` (Local, FREE) |
| Vector Store | FAISS |
| LLM | Groq LLaMA 3.3 70B (Free tier) |
| Frontend | HTML, CSS, JavaScript |
| Deployment | Docker + Docker Compose |

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `GROQ_API_KEY not set` | Add key in `.env` file |
| `Index not found` | Run `python src/rag.py --build` |
| Model decommissioned error | Update model name in `rag.py` |
| Port already in use | Change port in `app.py` |

---

## 📄 License

MIT License — free to use and modify.
