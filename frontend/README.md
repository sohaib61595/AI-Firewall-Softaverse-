# AI Firewall Frontend Interface

This directory contains the user interface for the AI Firewall project. The frontend is built entirely using lightweight, modern vanilla web technologies to ensure lightning-fast loading and seamless API integration without the overhead of heavy frameworks.

## 🛠 Technology Stack
- **HTML5:** Semantic structure for the dashboard and chat interfaces.
- **CSS3:** Custom styling utilizing CSS variables for consistent theming, implementing a modern "Glassmorphism" aesthetic with smooth micro-animations. No external CSS frameworks are used.
- **Vanilla JavaScript (ES6+):** Handles all DOM manipulation, API routing, and state management.
- **Chart.js:** Used for rendering the real-time analytics graphs on the Dashboard.

## 📁 Directory Structure
- `index.html`: The main entry point containing the UI framework and layout.
- `css/style.css`: The global stylesheet defining the theme, animations, and responsive breakpoints.
- `js/main.js`: Core logic for API polling and general UI state.
- `js/chat.js`: Handles the Live Chatbot interface and interactions with the OpenRouter LLM via the backend.
- `js/scanner.js`: Manages the Live Prompt Scanner functionality and result visualization.
- `js/dashboard.js`: Orchestrates the fetching and rendering of Chart.js metrics.
- `js/ledger.js`: Renders the paginated Threat Ledger history.

## 🚀 Running Locally
The frontend is statically served by the FastAPI backend to avoid CORS issues and simplify deployment.
Start the backend server from the root directory:
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Then simply open your browser to `http://localhost:8000` to interact with the interface.