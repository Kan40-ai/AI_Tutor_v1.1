// ==========================================
// ETHOS AI - FRONTEND CHAT LOGIC
// ==========================================

// --- Function triggered when a Prompt Pill is clicked ---
function usePrompt(text) {
    const inputField = document.getElementById('user-input');
    inputField.value = text;
    
    // Hide the welcome screen immediately
    const welcomeScreen = document.getElementById('welcome-screen');
    if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
    }
    
    sendMessage(); // Auto-send!
}

document.addEventListener('DOMContentLoaded', () => {
    const sendBtn = document.getElementById('send-btn');
    const inputField = document.getElementById('user-input');

    // Allow pressing "Enter" to send
    inputField.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);
});

async function sendMessage() {
    const input = document.getElementById('user-input');
    const chatPanel = document.getElementById('chat-panel');
    const sidePanel = document.getElementById('side-panel');
    const message = input.value.trim();

    if (!message) return;

    // --- Hide the welcome screen when a user types their own message ---
    const welcomeScreen = document.getElementById('welcome-screen');
    if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
    }

    // 1. Add User Message
    chatPanel.innerHTML += `<div class="msg user"><b>You:</b> ${message}</div>`;
    input.value = '';
    
    // Auto-scroll to bottom
    chatPanel.scrollTop = chatPanel.scrollHeight;

    // 2. Add Loading Indicator
    const botMsgId = 'bot-' + Date.now();
    chatPanel.innerHTML += `<div class="msg bot" id="${botMsgId}"><i>Thinking...</i></div>`;
    chatPanel.scrollTop = chatPanel.scrollHeight;

    try {
        // 3. Call the Flask Backend
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, mode: 'rag' })
        });

        const data = await response.json();
        const botDiv = document.getElementById(botMsgId);

        if (data.error) {
            botDiv.innerHTML = `<b>Tutor:</b> ⚠️ ${data.error}`;
            return;
        }
        
        // --- 4. Render the Answer & Extract Links (WITH ERROR HANDLING) ---
        let formattedAnswer = data.answer || "";
        const extractedLLMLinks = []; 

        // 1. Broad Regex: Catches ANY attempt at [Text](url)
        const attemptedMarkdownRegex = /\[([^\]]+)\]\s*\(([^)]+)\)/g;
        
        formattedAnswer = formattedAnswer.replace(attemptedMarkdownRegex, function(match, text, url) {
            const cleanText = text ? text.trim() : "";
            const cleanUrl = url ? url.trim() : "";
            const isValidUrl = /^https?:\/\/[^\s]+$/.test(cleanUrl);
            const hasTitle = cleanText.length > 0;

            if (!isValidUrl || !hasTitle) {
                console.error("🚨 MALFORMED AI LINK DETECTED 🚨\nOutput:", match);
                return `<span style="color: #dc3545; font-size: 0.9em; border-bottom: 1px dotted #dc3545; cursor: help;" title="Broken URL: ${cleanUrl}">⚠️ [Broken Link: ${cleanText}]</span>`;
            }

            extractedLLMLinks.push({ isLLMLink: true, title: cleanText, url: cleanUrl }); 
            return `<a href="${cleanUrl}" target="_blank" style="color: #007bff; text-decoration: underline;">${cleanText}</a>`;
        });

        // B. Convert any remaining naked URLs
        const nakedUrlRegex = /(?<!href=")(https?:\/\/[^\s<]+)/g;
        formattedAnswer = formattedAnswer.replace(nakedUrlRegex, function(url) {
            const cleanUrl = url.trim();
            extractedLLMLinks.push({ isLLMLink: true, title: cleanUrl, url: cleanUrl });
            return `<a href="${cleanUrl}" target="_blank" style="color: #007bff; text-decoration: underline;">${cleanUrl}</a>`;
        });

        // C. Replace newlines with <br> and bold with <b> tags
        formattedAnswer = formattedAnswer.replace(/\n/g, '<br>');
        formattedAnswer = formattedAnswer.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');

        botDiv.innerHTML = `<b>Tutor:</b> ${formattedAnswer}`;

        // --- 5. Update the Sources Sidebar ---
        sidePanel.innerHTML = '<h3>📚 Sources</h3>';
        
        const rawSources = data.sources || [];
        const cleanSources = rawSources.filter(src => src && src !== "");

        // Dump extracted links into sources array
        extractedLLMLinks.forEach(linkObj => cleanSources.push(linkObj));

        // ROUTE A: General LLM Route
        if (cleanSources.length === 0) {
            sidePanel.innerHTML += `
                <div class="source-card" style="border-left: 4px solid #6c757d; background: #f8f9fa;">
                    <div style="font-size: 1.2rem; margin-bottom: 5px;">🧠</div>
                    <strong>General Knowledge</strong><br>
                    <small class="text-muted">This response is based on the AI's baseline training. No specific course documents were matched.</small>
                </div>`;
        } 
        // ROUTE B, C, & D: RAG, YouTube, or Extracted Links
        else {
            cleanSources.forEach(src => {
                let cardHTML = "";

                if (src.isLLMLink) {
                    cardHTML = `
                        <div class="source-card" style="border-left: 4px solid #17a2b8;">
                            <strong>🌐 Web Resource</strong><br>
                            <a href="${src.url}" target="_blank" style="color: #007bff; text-decoration: underline; font-size: 0.85rem;">${src.title}</a>
                        </div>`;
                } else if (typeof src === 'string') {
                    if (src.includes("youtube.com") || src.includes("youtu.be")) {
                        cardHTML = `
                            <div class="source-card" style="border-left: 4px solid #ff0000;">
                                <strong>▶️ YouTube Video</strong><br>
                                <a href="${src}" target="_blank" style="color: #007bff; text-decoration: underline; font-size: 0.85rem;">Watch Reference Video</a>
                            </div>`;
                    } else {
                        cardHTML = `
                            <div class="source-card" style="border-left: 4px solid #007bff;">
                                <strong>📄 ${src}</strong><br>
                                <small class="text-muted">Reference Document</small>
                            </div>`;
                    }
                } else if (typeof src === 'object' && !src.isLLMLink) {
                    const fileName = src.file || src.source || "Course Material";
                    const pageInfo = src.page ? `Page(s): ${src.page}` : "Reference Text";
                    
                    cardHTML = `
                        <div class="source-card" style="border-left: 4px solid #28a745;">
                            <strong>📄 ${fileName}</strong><br>
                            <small class="text-muted">${pageInfo}</small>
                        </div>`;
                }

                sidePanel.innerHTML += cardHTML;
            });
        }

        // 6. Tell MathJax to render formulas
        if (window.MathJax) {
            MathJax.typesetPromise([chatPanel]).catch(function (err) {
                console.error('MathJax error:', err.message);
            });
        }

        chatPanel.scrollTop = chatPanel.scrollHeight;

    } catch (error) {
        document.getElementById(botMsgId).innerHTML = "<b>Tutor:</b> ⚠️ Network error. Please check your backend terminal.";
        console.error("Fetch error:", error);
    }
}