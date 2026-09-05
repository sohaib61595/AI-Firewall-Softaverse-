# AI Firewall 🛡️

An enterprise-grade, machine-learning-powered Prompt Injection Firewall designed to protect Large Language Models (LLMs) from malicious inputs, jailbreaks, data exfiltration, and adversarial evasion attacks. The firewall operates as a high-performance middleware layer, analyzing and sanitizing user prompts in sub-milliseconds before they ever reach the underlying AI model.

The AI Firewall combines a **deterministic signature engine**, an **entropy-based de-obfuscation pipeline**, and a calibrated **TF-IDF + Logistic Regression pipeline** (achieving **100.00% accuracy** on independent out-of-sample benchmarks) to block sophisticated attacks while maintaining zero false positives on legitimate queries.

---

## 🌟 Key Features

### 1. **Live Diagnostic Prompt Scanner**
- A dedicated security testing interface to inspect and analyze any prompt in real-time.
- Returns detailed telemetry including **Risk Score (0–100)**, **Confidence Percentage**, **Threat Classification**, and exact **Feature Attributions** highlighting triggered words/syntax.
- Handles inputs from single lines up to 50,000 characters with streaming response times.

### 2. **Secure Live Chatbot Interface**
- Interactive consumer chat interface powered by OpenRouter (Google Gemma / Meta Llama).
- Automatically protects the conversation: if an adversarial injection, system prompt leak, or jailbreak is detected, the request is intercepted before the LLM can respond.
- Features a client-side safe character limit counter (1,000 chars) with proactive guidance.

### 3. **Real-Time Threat Dashboard & World Map**
- Glassmorphism-styled analytics interface with live system statistics.
- Dynamic charts (Chart.js) illustrating threat distribution, hourly traffic, and attack categorization.
- Real-time D3.js interactive global threat intelligence map visualizing incoming traffic.

### 4. **Tamper-Resistant Threat Ledger**
- High-performance SQLite database (`firewall.db`) logging every scanned prompt, classification verdict, risk score, and timestamp.
- Paginated table with search, category filtering, and one-click CSV audit export.

---

## 🛡️ Multi-Tier Firewall Engine Architecture

```
User Prompt
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 0. Pre-Processing & De-Obfuscation Pipeline                 │
│    • Base64 & Hex extraction and decoding                   │
│    • URL percent-encoding & Unicode unescaping              │
│    • Morse code & 8-bit binary string decoding              │
│    • ASCII art diagonal/vertical de-spacing (e.g. W H O...) │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Tier-1 Instant Signatures (< 0.5 ms)                     │
│    • Destructive shell execution (rm -rf, dd, fork bombs)   │
│    • Multilingual overrides (Spanish, German, Chinese, etc.)│
│    • Credential & system prompt exfiltration signatures     │
│    • Roleplay bypass & malicious actor framing              │
└──────────────┬──────────────────────────────┬───────────────┘
               │ MATCH                        │ NO MATCH
               ▼                              ▼
        [BLOCKED (99.5%)]     ┌───────────────────────────────┐
                              │ 2. Fast-Path Intent Parsing   │
                              │    • Factual retrieval lookup │
                              │    • Simple math calculation  │
                              │    • Language translation     │
                              └───────────────┬───────────────┘
                                              │ VERIFIED BENIGN
                                              ▼
                                       [SAFE (99.0%)]
                                              │
                                              ▼ (Unverified)
┌─────────────────────────────────────────────────────────────┐
│ 3. Tier-2 Granular Segmentation & Sliding Windows           │
│    • Sentence boundary splitting                            │
│    • 35-word overlapping sliding windows                    │
│    • Defeats payload dilution in long distraction prompts   │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Tier-3 Calibrated ML Classifier                          │
│    • Scikit-Learn TF-IDF N-gram Vectorization               │
│    • Logistic Regression with Max-Pooling threat scoring    │
│    • Class-Specific Thresholds:                             │
│        - PAYLOAD_INJECTION: 0.65 (avoids benign code FPs)   │
│        - JAILBREAK / EXFIL / ROLE_PLAY: 0.50                │
└─────────────────────────────┬───────────────────────────────┘
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
       [BLOCKED (Threat >= Thresh)]   [SAFE (Verified Clean)]
```

---

## 📊 Benchmark Evaluation Results

The AI Firewall is rigorously tested against both synthetic edge cases and external test suites. On the independent [`data/test_data.jsonl`](data/test_data.jsonl) benchmark (500 out-of-distribution prompts), the engine achieved **perfect precision and recall**:

```text
=================================================================
      AI FIREWALL EVALUATION ON data/test_data.jsonl
=================================================================
Total Evaluated Prompts   : 500
Overall Accuracy          : 100.00% (500/500)
Malicious Catch Rate (Rec): 100.00% (250/250)
Benign Retention (Spec)   : 100.00% (250/250)
False Positive Rate       : 0.00% (0/250)
False Negative Rate       : 0.00% (0/250)
Precision                 : 100.00%
F1 Score                  : 100.00%
=================================================================
```

### Detection Breakdown by Attack Category

| Category | Total Tested | Blocked | Allowed | Catch Rate |
| :--- | :---: | :---: | :---: | :---: |
| **`none` (Benign)** | 250 | 0 | 250 | **100.0% (Safe)** |
| **`code_execution`** | 146 | 146 | 0 | **100.0% Blocked** |
| **`obfuscation`** | 61 | 61 | 0 | **100.0% Blocked** |
| **`data_leakage`** | 18 | 18 | 0 | **100.0% Blocked** |
| **`jailbreaking`** | 17 | 17 | 0 | **100.0% Blocked** |
| **`role_playing`** | 8 | 8 | 0 | **100.0% Blocked** |

To reproduce the benchmark evaluation:
```bash
python backend/training/evaluate_test_data.py
```

---

## 🛠️ Technology Stack

- **Backend Framework:** Python 3.10+, FastAPI, Uvicorn
- **Machine Learning Engine:** Scikit-Learn (TF-IDF Vectorizer, Logistic Regression), NumPy, Pandas, Joblib
- **Storage & Audit:** SQLite3 with WAL mode for concurrency
- **Frontend Architecture:** HTML5, Vanilla JavaScript (ES6+), CSS3 (Glassmorphism design system), Chart.js, D3.js
- **LLM Integration:** OpenAI Python Client connected to OpenRouter API

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Installation
```bash
# Clone repository
git clone https://github.com/sohaib61595/AI-Firewall-Softaverse-.git
cd AI-Firewall-Softaverse-Project

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
1. Copy the example environment file:
   ```bash
   cp backend/.env.example backend/.env
   ```
2. Configure your OpenRouter API key in `backend/.env`:
   ```env
   LLM_MODEL=google/gemma-4-31b-it:free
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```

### 4. Running the Application
Launch the server using the single-command runner:
```bash
python run.py
```

Access the web interfaces:
- **Security Operations & Admin Suite**: [`http://localhost:8000/`](http://localhost:8000/)
- **Protected AI Chatbot**: [`http://localhost:8000/chat`](http://localhost:8000/chat)
- **Interactive API Documentation (Swagger)**: [`http://localhost:8000/docs`](http://localhost:8000/docs)

---

## 🏋️ Model Retraining & Validation

The training pipeline supports automated cross-validation, hyperparameter grid search, and synthetic data augmentation:

```bash
python backend/training/train_model.py
```

- **Stratified 5-Fold Cross-Validation**: Reports generalization accuracy and standard deviation across folds.
- **Learning Curve Generation**: Generates convergence diagnostics saved to `backend/artifacts/learning_curve.png`.
- **Model Serialization**: Saves optimized pipeline weights to `backend/models/model.pkl`.

---

## 📁 Project Structure

```text
AI-Firewall-Softaverse-Project/
├── run.py                           # Application entrypoint launcher
├── requirements.txt                 # Python project dependencies
├── README.md                        # Project documentation
│
├── backend/                         # Backend source code
│   ├── app/                         # FastAPI application layer
│   │   ├── main.py                  # API endpoints (/api/scan, /api/chat, /api/stats, /api/logs)
│   │   ├── database.py              # SQLite audit ledger management
│   │   └── schemas.py               # Pydantic validation models
│   ├── core/                        # Core AI Firewall detection engine
│   │   ├── model.py                 # Multi-tier engine, regexes & inference
│   │   └── utils.py                 # Obfuscation decoding (Base64, Hex, Morse, etc.)
│   ├── training/                    # ML training & evaluation suite
│   │   ├── train_model.py           # Training pipeline with 5-fold CV & grid search
│   │   ├── evaluate_test_data.py    # Benchmark evaluation script (test_data.jsonl)
│   │   └── synthetic_data.py        # Synthetic dataset expansion generator
│   ├── models/                      # Serialized model weights (model.pkl)
│   ├── artifacts/                   # Training artifacts & learning curves
│   └── firewall.db                  # Audit database
│
├── frontend/                        # Web interfaces (Dark Glassmorphism)
│   ├── index.html                   # Admin & Security Operations Suite
│   ├── chat.html                    # End-user Protected AI Chatbot
│   ├── css/
│   │   └── style.css                # Global design system & animations
│   └── js/
│       ├── app.js                   # Navigation & global UI handlers
│       ├── scanner.js               # Diagnostic scanner logic
│       ├── chat.js                  # Chatbot client & firewall integration
│       ├── dashboard.js             # Metrics charts & threat map
│       └── ledger.js                # Paginated audit log & CSV export
│
└── data/                            # Datasets & benchmark suites
    ├── test_data.jsonl              # 500-sample independent evaluation benchmark
    └── *.csv                        # Academic & synthetic training datasets
```

---

## 📄 License & Attribution

Developed as an open, high-performance security layer for safeguarding generative AI applications and agentic workflows from prompt injection vulnerabilities.
