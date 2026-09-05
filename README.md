# AI Firewall 🛡️

An advanced, machine-learning-powered Prompt Injection Firewall designed to protect Large Language Models (LLMs) from malicious inputs. This project acts as a robust middleware layer, analyzing user prompts in real-time before they ever reach the underlying AI model.

The AI Firewall leverages a custom-trained **TF-IDF + Logistic Regression pipeline** (achieving 95%+ accuracy) to classify and block sophisticated jailbreaks, data exfiltration attempts, and payload injections.

---

## 🌟 Key Features

### 1. **Live Prompt Scanner**
- A dedicated testing ground to scan any input prompt instantly.
- Returns detailed analytics including a **Risk Score (0-100)**, **Confidence Metrics**, and specific **Threat Categorization**.
- Highlights exactly which words or tokens triggered the firewall (e.g., detecting `DROP TABLE` or `Ignore all prior instructions`).

![Scanner blocking an SQL Injection Payload](images/scanner_blocked.png)

### 2. **Secure Live Chatbot**
- An interactive chatbot powered by the OpenRouter API (Google Gemma / Meta Llama).
- Fully integrated with the firewall: if a user types a malicious prompt, the firewall intercepts and blocks it directly in the chat interface before the LLM can respond, preventing system leaks.

### 3. **Real-Time Threat Dashboard**
- A beautiful, glassmorphism-styled metrics dashboard.
- Visualizes system health, total scans, and blocked threats over time using dynamic charts (Pie Charts for threat distribution, Line Graphs for activity timelines).

### 4. **Threat Ledger**
- A comprehensive, paginated historical log of all prompts processed by the system.
- Stored securely in a local SQLite database (`firewall.db`), allowing administrators to audit past attacks, view timestamps, and analyze bypass attempts.

### 5. **Multi-Vector Threat Detection**
The model is specifically trained on thousands of data points to categorize and neutralize:
- **JAILBREAK:** Direct attempts to override system rules (e.g., "DO ANYTHING NOW").
- **DATA_EXFILTRATION:** Attempts to extract the hidden system prompt or confidential context.
- **PAYLOAD_INJECTION:** Embedded code execution attempts like SQLi, XSS, or SSTI (e.g., `{{ config.items() }}`).
- **ROLE_PLAY_BYPASS:** framing malicious requests within fictional scenarios or games.
- **SOCIAL_ENGINEERING:** Using false authority to bypass restrictions.

### 6. **Automated ML Training Pipeline**
- Includes a fully automated backend training script (`train_model.py`) that utilizes cross-validation, grid search, and dataset augmentation to continually harden the model against novel edge cases.

---

## 🛠️ Technology Stack

- **Backend:** Python, FastAPI, Uvicorn
- **Machine Learning:** Scikit-Learn (TF-IDF Vectorization, Logistic Regression), Pandas, Joblib
- **Database:** SQLite3
- **Frontend:** HTML5, Vanilla JavaScript, CSS3 (Glassmorphism & Micro-animations), Chart.js
- **LLM Integration:** OpenAI Python Client via OpenRouter API

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- An OpenRouter API Key (for the Live Chatbot feature)

### Installation
1. Clone the repository and navigate to the project folder.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration
1. Rename `backend/.env.example` to `backend/.env`.
2. Add your OpenRouter API key to the `.env` file:
   ```env
   LLM_MODEL=google/gemma-4-31b-it:free
   OPENROUTER_API_KEY=your_api_key_here
   ```

### Running the Application
1. Start the server using the single-command runner:
   ```bash
   python run.py
   ```
2. Open your web browser:
   - **Protected AI Chatbot (1,000-Char Safe Limit)**: [`http://localhost:8000/chat`](http://localhost:8000/chat)
   - **Security Operations & Admin Suite**: [`http://localhost:8000/`](http://localhost:8000/)

### Retraining the Model
If you add new datasets to the `data/` folder and want to harden the firewall:
```bash
python -m backend.training.train_model
```
This runs the full pipeline with Stratified 5-Fold Cross-Validation, generates an updated learning curve in `backend/artifacts/`, and saves `model.pkl`.

---

## 📁 Project Structure

```text
AI-Firewall-Softaverse-Project/
├── run.py                           # Single-command launcher (python run.py)
├── requirements.txt                 # Clean, pure-CPU project dependencies
├── README.md                        # Documentation & quickstart guide
│
├── backend/                         # Core Python Backend & ML Engine
│   ├── app/                         # FastAPI application, database & schemas
│   │   ├── main.py                  # API endpoints (/api/scan, /api/chat, /api/stats)
│   │   ├── database.py              # High-performance SQLite audit ledger
│   │   └── schemas.py               # Pydantic request & response validation
│   ├── core/                        # Multi-Tier Firewall Engine & preprocessors
│   │   ├── model.py                 # Multi-Tier engine (Regex, sliding windows, max-pooling)
│   │   └── utils.py                 # Text normalization routines
│   ├── training/                    # Model training & synthetic data pipelines
│   │   ├── train_model.py           # Training pipeline with 5-Fold Cross-Validation
│   │   ├── synthetic_data.py        # Multi-vector synthetic data expansions
│   │   └── unseen_test_set.py       # Zero-day generalization evaluation prompts
│   ├── models/                      # Serialized model weights (model.pkl)
│   ├── artifacts/                   # Training metrics & learning curve plots
│   ├── firewall.db                  # Local SQLite database for audit trails
│   └── .env                         # Environment configuration (API keys)
│
├── frontend/                        # Web Applications (Dark Glassmorphism)
│   ├── chat.html                    # Dedicated Consumer Chatbot UI (/chat)
│   ├── index.html                   # Security Operations & Admin Suite (/)
│   ├── css/
│   │   └── style.css                # Global design system & animations
│   └── js/
│       ├── app.js                   # SPA router, API health checks & particles
│       ├── chat.js                  # Chat controller, 1,000-char counter & alert cards
│       ├── scanner.js               # Diagnostic scanner (up to 50,000 chars)
│       ├── dashboard.js             # Live analytics & D3 world threat map
│       └── ledger.js                # Paginated audit log & CSV export
│
├── data/                            # Training & benchmark datasets (CSV)
├── docs/                            # Documentation & presentations
│   ├── AI_Firewall_Presentation.docx
│   └── PROJECT_STRUCTURE.md         # Detailed component architecture guide
└── images/                          # Screenshots & UI previews
```

---

## 🔮 Future Improvements

While the current TF-IDF + Logistic Regression model is highly effective and fast, there are several areas planned for future enhancement:

1. **Transformer-Based Architecture:** Upgrading the core classification engine from TF-IDF/Logistic Regression to a fine-tuned, lightweight Transformer model (such as DistilBERT or RoBERTa). This will fundamentally improve the firewall's ability to understand deep semantic context, making it much harder to bypass using advanced context-switching or complex role-play scenarios.
2. **Distributed Session Storage:** Migrating the in-memory `cachetools.TTLCache` rate-limiting and session management to a dedicated Redis instance to support horizontal scaling across multiple API workers.
3. **Advanced Anomaly Detection:** Implementing unsupervised anomaly detection alongside the supervised classifier to catch entirely novel zero-day prompt injection structures before they are added to the training corpus.
4. **Streaming API Responses:** Upgrading the chat interface to support WebSocket or SSE (Server-Sent Events) for real-time streaming of LLM tokens, while still running the firewall check asynchronously on the full input block.
