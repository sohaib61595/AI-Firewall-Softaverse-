/* chat.js — Dedicated Chatbot UI Controller */

document.addEventListener("DOMContentLoaded", () => {
    const chatInput = document.getElementById("chatInput");
    const chatSendBtn = document.getElementById("chatSendBtn");
    const chatHistory = document.getElementById("chatHistory");
    const chatVoiceBtn = document.getElementById("chatVoiceBtn");
    const chatCharCounter = document.getElementById("chatCharCounter");
    const clearChatBtn = document.getElementById("clearChatHistoryBtn");
    const quickChips = document.querySelectorAll(".quick-chip");

    // ── Session ID ──────────────────────────────────────────────────────────
    let sessionId = sessionStorage.getItem("shield_chat_session");
    if (!sessionId) {
        sessionId = "session_" + Math.random().toString(36).substring(2, 10);
        sessionStorage.setItem("shield_chat_session", sessionId);
    }

    // ── Character Counter (Max 1,000 characters) ────────────────────────────
    function updateCharCounter() {
        if (!chatInput || !chatCharCounter) return;
        const len = chatInput.value.length;
        chatCharCounter.textContent = `${len} / 1000`;
        chatCharCounter.classList.remove("warn", "danger");
        if (len >= 1000) {
            chatCharCounter.classList.add("danger");
        } else if (len >= 850) {
            chatCharCounter.classList.add("warn");
        }
    }

    if (chatInput) {
        chatInput.addEventListener("input", () => {
            updateCharCounter();
            // Auto resize textarea
            chatInput.style.height = "auto";
            chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + "px";
        });
    }

    // ── Quick Chips ─────────────────────────────────────────────────────────
    quickChips.forEach(chip => {
        chip.addEventListener("click", () => {
            if (!chatInput) return;
            chatInput.value = chip.dataset.prompt || "";
            updateCharCounter();
            chatInput.focus();
        });
    });

    // ── Clear Conversation ──────────────────────────────────────────────────
    if (clearChatBtn) {
        clearChatBtn.addEventListener("click", () => {
            sessionId = "session_" + Math.random().toString(36).substring(2, 10);
            sessionStorage.setItem("shield_chat_session", sessionId);
            chatHistory.innerHTML = `
                <div class="chat-msg assistant">
                  <div class="chat-msg-bubble">
                    Conversation reset. How can I assist you with your project today?
                  </div>
                  <span class="chat-msg-time">Just now</span>
                </div>
            `;
            if (window.showToast) window.showToast("Conversation cleared", "info");
        });
    }

    // ── Voice Input for Chat ────────────────────────────────────────────────
    let chatRecognition;
    let isChatRecording = false;

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        chatRecognition = new SpeechRecognition();
        chatRecognition.continuous = true;
        chatRecognition.interimResults = true;

        chatRecognition.onstart = () => {
            isChatRecording = true;
            if (chatVoiceBtn) {
                chatVoiceBtn.classList.add('recording');
                chatVoiceBtn.style.borderColor = 'var(--danger)';
                chatVoiceBtn.style.color = 'var(--danger)';
            }
            if (chatInput) chatInput.placeholder = 'Listening... Speak now.';
        };

        chatRecognition.onresult = (event) => {
            let transcript = '';
            for (let i = 0; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            if (chatInput) {
                chatInput.value = transcript.substring(0, 1000);
                updateCharCounter();
            }
        };

        chatRecognition.onerror = (event) => {
            console.error('Speech recognition error', event.error);
            stopChatRecording();
            if (event.error !== 'no-speech' && window.showToast) {
                window.showToast('Voice input error: ' + event.error, 'error');
            }
        };

        chatRecognition.onend = () => {
            stopChatRecording();
        };
    } else {
        if (chatVoiceBtn) chatVoiceBtn.style.display = 'none';
    }

    function stopChatRecording() {
        isChatRecording = false;
        if (chatVoiceBtn) {
            chatVoiceBtn.classList.remove('recording');
            chatVoiceBtn.style.borderColor = '';
            chatVoiceBtn.style.color = '';
        }
        if (chatInput) chatInput.placeholder = "Type your message... (Max 1,000 characters)";
    }

    if (chatVoiceBtn) {
        chatVoiceBtn.addEventListener('click', () => {
            if (!chatRecognition) return;
            if (isChatRecording) {
                chatRecognition.stop();
            } else {
                if (chatInput) chatInput.value = '';
                chatRecognition.start();
            }
        });
    }

    // ── Message Rendering ───────────────────────────────────────────────────
    function appendMessage(role, text, firewallLabel = null, isBlocked = false) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `chat-msg ${role} ${isBlocked ? 'blocked' : ''}`;

        const bubble = document.createElement("div");
        bubble.className = "chat-msg-bubble";
        bubble.textContent = text;
        msgDiv.appendChild(bubble);

        if (isBlocked) {
            const interceptCard = document.createElement("div");
            interceptCard.className = "threat-intercept-card";
            interceptCard.innerHTML = `
                <div class="threat-intercept-header">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    </svg>
                    <span>Shield Intercept • ${firewallLabel || 'BLOCKED'}</span>
                </div>
                <div class="threat-intercept-desc">
                    This prompt contained an adversarial pattern or prompt injection attempting to manipulate the AI system.
                </div>
            `;
            msgDiv.appendChild(interceptCard);
        } else if (firewallLabel && role === "assistant") {
            const tag = document.createElement("div");
            tag.className = "firewall-label safe";
            tag.textContent = `Shield: ${firewallLabel}`;
            msgDiv.appendChild(tag);
        }

        const timeSpan = document.createElement("span");
        timeSpan.className = "chat-msg-time";
        timeSpan.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        msgDiv.appendChild(timeSpan);

        chatHistory.appendChild(msgDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    // ── Send Message ────────────────────────────────────────────────────────
    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        if (text.length > 1000) {
            if (window.showToast) {
                window.showToast("Message exceeds 1,000 character maximum limit.", "error");
            }
            return;
        }

        // Add user message to UI
        appendMessage("user", text);
        chatInput.value = "";
        chatInput.style.height = "auto";
        updateCharCounter();

        // Disable input while processing
        chatInput.disabled = true;
        chatSendBtn.disabled = true;

        // Show typing indicator
        const typingDiv = document.createElement("div");
        typingDiv.className = "chat-msg assistant typing-indicator";
        typingDiv.innerHTML = '<div class="chat-msg-bubble">Thinking...</div>';
        chatHistory.appendChild(typingDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text, session_id: sessionId })
            });

            const data = await res.json();
            if (typingDiv.parentNode) typingDiv.parentNode.removeChild(typingDiv);

            if (!res.ok) {
                appendMessage("assistant", `[Error] ${data.detail || "Request failed"}`);
                return;
            }

            const isBlocked = data.status === "blocked" || (data.firewall_label && data.firewall_label.includes("BLOCKED"));
            appendMessage("assistant", data.reply, data.firewall_label, isBlocked);

        } catch (err) {
            console.error("Chat API error:", err);
            if (typingDiv.parentNode) typingDiv.parentNode.removeChild(typingDiv);
            appendMessage("assistant", "[Connection Error] Could not connect to AI Firewall server.");
        } finally {
            chatInput.disabled = false;
            chatSendBtn.disabled = false;
            chatInput.focus();
        }
    }

    if (chatSendBtn && chatInput) {
        chatSendBtn.addEventListener("click", sendMessage);
        chatInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    updateCharCounter();
});
