# AI Firewall - Clean Architecture & Project Structure 📁

This document describes the simplified, clean folder structure of the **AI Firewall** codebase. Every file has a single, well-defined location with zero redundant duplicates.

---

## High-Level Layout

```text
AI-Firewall-Softaverse-Project/
├── run.py                         # Single-command application launcher (python run.py)
├── requirements.txt               # Pure-CPU lightweight project dependencies
├── README.md                      # Comprehensive guide & quickstart
│
├── backend/                       # Python FastAPI Backend & ML Engine
│   ├── app/                       # Web & Database Layer
│   │   ├── main.py                # FastAPI REST API (/api/chat, /api/scan, /api/stats)
│   │   ├── database.py            # Optimized SQLite logging & analytics
│   │   └── schemas.py             # Pydantic request & response validation models
│   │
│   ├── core/                      # Multi-Tier Detection Engine
│   │   ├── model.py               # Tier 1 Regex + Tier 2 Sliding Windows + Tier 3 ML
│   │   └── utils.py               # Text normalization & preprocessor
│   │
│   ├── training/                  # Model Training & Synthetic Datasets
│   │   ├── train_model.py         # 5-Fold Stratified Cross-Validation pipeline
│   │   ├── synthetic_data.py      # Multi-vector synthetic prompt expansions
│   │   └── unseen_test_set.py     # Zero-day generalization evaluation benchmarks
│   │
│   ├── models/                    # Trained Model Storage
│   │   └── model.pkl              # Serialized Scikit-Learn TF-IDF + Logistic Regression pipeline
│   │
│   ├── artifacts/                 # Training Diagnostics
│   │   └── learning_curve.png     # Cross-validation convergence plot (anti-overfitting proof)
│   ├── .env                       # Environment configuration (API keys, model name)
│   └── firewall.db                # SQLite audit log ledger
│
├── frontend/                      # Web Interfaces (Pure HTML5 / CSS3 / Vanilla JS)
│   ├── chat.html                  # Consumer Chatbot UI (1,000-character safe limit)
│   ├── index.html                 # Security Admin & Operations Suite (Diagnostic Scanner, Ledger, Map)
│   ├── css/
│   │   └── style.css              # Cyber dark glassmorphism design system & micro-animations
│   └── js/
│       ├── app.js                 # SPA router, API health checker & particle animation
│       ├── chat.js                # Chatbot controller, live char counter & threat intercept cards
│       ├── scanner.js             # Diagnostic scanner controller (up to 50,000 chars)
│       ├── dashboard.js           # Real-time metrics & D3 threat origin world map
│       └── ledger.js              # Paginated audit log & CSV export
│
├── data/                          # Training corpora & labeled benchmark CSV datasets
├── docs/                          # Presentations & architecture documentation
│   ├── AI_Firewall_Presentation.docx
│   └── PROJECT_STRUCTURE.md
└── images/                        # UI screenshots & demo previews
```

---

## Backend Modules (`backend/`)

### 1. `backend/app/` — API & Storage Service
- [`backend/app/main.py`](file:///backend/app/main.py): FastAPI application providing `/api/scan`, `/api/chat`, `/api/stats`, `/api/history`, and static asset delivery.
- [`backend/app/database.py`](file:///backend/app/database.py): High-performance SQLite audit logger with single-query hourly aggregation and indexed threat history.
- [`backend/app/schemas.py`](file:///backend/app/schemas.py): Pydantic validation models enforcing typing and string length constraints.

### 2. `backend/core/` — Multi-Tier AI Detection Engine
- [`backend/core/model.py`](file:///backend/core/model.py):
  - **Tier 1 (Instant Signatures)**: Pre-compiled regex patterns intercepting explicit overrides, system command markers, and persona hijacking in `< 0.5 ms`.
  - **Tier 2 (Dual-Granularity Segmentation)**: Breaks multi-paragraph stories into sentence boundaries and 35-word sliding windows (step 15) to prevent injection phrases from being diluted by benign text.
  - **Tier 3 (Threat Aggregation & Max-Pooling)**: Aggregates collective threat probability (`1.0 - P(SAFE)`) against a calibrated 0.65 threshold. Max-pools threat severity across segments.
- [`backend/core/utils.py`](file:///backend/core/utils.py): Text normalization and token preprocessing function.

### 3. `backend/training/` — Machine Learning Pipeline
- [`backend/training/train_model.py`](file:///backend/training/train_model.py): Automated training script with Stratified 5-Fold Cross-Validation, learning curve generation, and unseen evaluation.
- [`backend/training/synthetic_data.py`](file:///backend/training/synthetic_data.py): Combinatorial dataset generator covering jailbreaks, data exfiltration, payload injections, social engineering pretexts, and safe cybersecurity studies.
- [`backend/training/unseen_test_set.py`](file:///backend/training/unseen_test_set.py): Dedicated benchmark suite of novel, unseen prompt injection variations.

### 4. `backend/models/` — Model Weights
- [`backend/models/model.pkl`](file:///backend/models/model.pkl): The serialized Scikit-Learn TF-IDF + Logistic Regression pipeline.

### 5. `backend/artifacts/` — Training Artifacts
- [`backend/artifacts/learning_curve.png`](file:///backend/artifacts/learning_curve.png): Training curve demonstrating score convergence and confirming zero overfitting.

---

## How to Run

1. **Start the Application**:
   ```bash
   python run.py
   ```
2. **Access the Interfaces**:
   - **Consumer Chatbot (1,000-Char Limit)**: [`http://localhost:8000/chat`](http://localhost:8000/chat)
   - **Security Operations & Admin Suite**: [`http://localhost:8000/`](http://localhost:8000/)
3. **Retrain the Model**:
   ```bash
   python -m backend.training.train_model
   ```
