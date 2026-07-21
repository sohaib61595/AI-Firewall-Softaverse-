document.addEventListener("DOMContentLoaded", () => {
    const chatInput = document.getElementById("chatInput");
    const chatSendBtn = document.getElementById("chatSendBtn");
    const chatHistory = document.getElementById("chatHistory");
    const chatVoiceBtn = document.getElementById("chatVoiceBtn");
    
    // ── Voice Input for Chat ───────────────────────────────────────────────
    let chatRecognition;
    let isChatRecording = false;
    
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        chatRecognition = new SpeechRecognition();
        chatRecognition.continuous = true;
        chatRecognition.interimResults = true;
    
        chatRecognition.onstart = () => {
            isChatRecording = true;
            chatVoiceBtn.classList.add('recording');
            chatVoiceBtn.style.color = 'var(--danger)'; // Visual indicator
            chatInput.placeholder = 'Listening... Speak now.';
        };
    
        chatRecognition.onresult = (event) => {
            let transcript = '';
            for (let i = 0; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            chatInput.value = transcript;
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
            chatVoiceBtn.style.color = '';
        }
        chatInput.placeholder = "Type your message here...";
    }
    
    if (chatVoiceBtn) {
        chatVoiceBtn.addEventListener('click', () => {
            if (!chatRecognition) return;
            if (isChatRecording) {
                chatRecognition.stop();
            } else {
                chatInput.value = '';
                chatRecognition.start();
            }
        });
    }

    // Generate a simple session ID for this browser tab
    const sessionId = "session_" + Math.random().toString(36).substring(2, 10);

    function addMessage(role, text, firewallLabel = null) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `chat-message ${role}`;
        
        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";
        bubble.textContent = text;
        
        msgDiv.appendChild(bubble);
        
        if (firewallLabel) {
            const labelSpan = document.createElement("div");
            labelSpan.className = "firewall-label";
            if (firewallLabel.startsWith("BLOCKED")) {
                labelSpan.classList.add("blocked");
                bubble.classList.add("blocked-bubble");
            } else {
                labelSpan.classList.add("safe");
            }
            labelSpan.textContent = `Firewall: ${firewallLabel}`;
            msgDiv.appendChild(labelSpan);
        }
        
        chatHistory.appendChild(msgDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;
        
        // Add user message to UI
        addMessage("user", text);
        chatInput.value = "";
        
        // Disable input while waiting
        chatInput.disabled = true;
        chatSendBtn.disabled = true;
        
        // Show typing indicator
        const typingDiv = document.createElement("div");
        typingDiv.className = "chat-message assistant typing-indicator";
        typingDiv.innerHTML = '<div class="chat-bubble">...</div>';
        chatHistory.appendChild(typingDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text, session_id: sessionId })
            });
            
            const data = await res.json();
            
            // Remove typing indicator
            chatHistory.removeChild(typingDiv);
            
            // Add bot response
            addMessage("assistant", data.reply, data.firewall_label);
            
        } catch (err) {
            console.error("Chat API error:", err);
            chatHistory.removeChild(typingDiv);
            addMessage("assistant", "[Connection Error] Could not reach the server.");
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
});
