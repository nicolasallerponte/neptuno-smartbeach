/* ================================================================
   NEPTUNO - Chat Interface
   Sends messages to /api/chat with conversation history.
   Renders markdown (bold, lists, line breaks) and typewriter effect.
   ================================================================ */

const NeptunoChat = {
    isProcessing: false,
    conversationHistory: [],
    MAX_HISTORY: 6,

    init() {
        this.input = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('chat-send');
        this.messages = document.getElementById('chat-messages');

        if (!this.input || !this.sendBtn || !this.messages) return;

        this.input.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.send(); }
        });
        this.sendBtn.addEventListener('click', () => this.send());

        // Suggestion chips
        document.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                this.input.value = chip.dataset.text || chip.textContent;
                this.send();
                const sugg = document.getElementById('chat-suggestions');
                if (sugg) sugg.style.display = 'none';
            });
        });

        this.input.focus();
    },

    async send() {
        const text = this.input.value.trim();
        if (!text || this.isProcessing) return;

        const sugg = document.getElementById('chat-suggestions');
        if (sugg) sugg.style.display = 'none';

        this.isProcessing = true;
        this.sendBtn.disabled = true;
        this.input.value = '';

        this._appendMessage('user', text, false);
        this.conversationHistory.push({ role: 'user', content: text });

        const typingEl = this._showTyping();
        let responseText = '';

        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 45000);

            const resp = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    history: this.conversationHistory.slice(-this.MAX_HISTORY),
                }),
                signal: controller.signal,
            });
            clearTimeout(timeout);

            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            responseText = data.response || 'Sin respuesta del asistente.';
        } catch (err) {
            if (err.name === 'AbortError') {
                responseText = 'La solicitud ha tardado demasiado (45s). Asegurate de que Ollama esta activo en el host con: ollama serve';
            } else {
                responseText = `No se pudo contactar con el asistente. Comprueba que Ollama esta en marcha. (${err.message})`;
            }
        } finally {
            typingEl.remove();
            this.isProcessing = false;
            this.sendBtn.disabled = false;
        }

        this.conversationHistory.push({ role: 'assistant', content: responseText });
        if (this.conversationHistory.length > this.MAX_HISTORY * 2) {
            this.conversationHistory = this.conversationHistory.slice(-this.MAX_HISTORY * 2);
        }

        this._appendMessage('bot', responseText, true);
        this.input.focus();
    },

    _appendMessage(role, text, useTypewriter) {
        const wrapper = document.createElement('div');
        wrapper.className = `message ${role}`;

        if (role === 'bot') {
            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.setAttribute('aria-hidden', 'true');
            avatar.textContent = 'N';
            avatar.style.cssText = 'width:32px;height:32px;border-radius:50%;width:30px;height:30px;border-radius:50%;background:#111827;display:flex;align-items:center;justify-content:center;font-family:'DM Serif Display',serif;font-style:italic;font-size:0.85rem;color:#fff;flex-shrink:0;margin-top:4px';
            wrapper.appendChild(avatar);
        }

        const bubble = document.createElement('div');
        bubble.className = 'message-content';

        if (useTypewriter && role === 'bot') {
            wrapper.appendChild(bubble);
            this.messages.appendChild(wrapper);
            this._scrollBottom();
            this._typewriter(bubble, text);
        } else {
            bubble.innerHTML = role === 'bot' ? this._renderMarkdown(text) : this._esc(text);
            wrapper.appendChild(bubble);
            this.messages.appendChild(wrapper);
            this._scrollBottom();
        }
    },

    _typewriter(el, text, speed = 8) {
        const rendered = this._renderMarkdown(text);
        // Split by HTML tags to avoid breaking them during typewriter
        const parts = rendered.split(/(<[^>]+>)/);
        let output = '';
        let i = 0;
        const tick = () => {
            if (i < parts.length) {
                const part = parts[i++];
                if (part.startsWith('<')) {
                    output += part;
                    el.innerHTML = output;
                    tick();
                } else {
                    let ci = 0;
                    const inner = () => {
                        if (ci < part.length) {
                            output += part[ci++];
                            el.innerHTML = output;
                            this._scrollBottom();
                            setTimeout(inner, speed);
                        } else {
                            tick();
                        }
                    };
                    inner();
                }
            }
        };
        tick();
    },

    _renderMarkdown(text) {
        let s = this._esc(text);
        s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        s = s.replace(/\*(.+?)\*/g, '<em>$1</em>');
        // List items
        const lines = s.split('\n');
        let inList = false;
        const result = [];
        for (const line of lines) {
            if (line.startsWith('- ')) {
                if (!inList) { result.push('<ul>'); inList = true; }
                result.push(`<li>${line.slice(2)}</li>`);
            } else {
                if (inList) { result.push('</ul>'); inList = false; }
                result.push(line);
            }
        }
        if (inList) result.push('</ul>');
        return result.join('<br>').replace(/<br>(<ul>)/g, '$1').replace(/<\/ul><br>/g, '</ul>');
    },

    _showTyping() {
        const wrapper = document.createElement('div');
        wrapper.className = 'message bot';
        const avatar = document.createElement('div');
        avatar.setAttribute('aria-hidden', 'true');
        avatar.style.cssText = 'width:32px;height:32px;border-radius:50%;width:30px;height:30px;border-radius:50%;background:#111827;display:flex;align-items:center;justify-content:center;font-family:'DM Serif Display',serif;font-style:italic;font-size:0.85rem;color:#fff;flex-shrink:0;margin-top:4px';
        avatar.textContent = 'N';
        const bubble = document.createElement('div');
        bubble.className = 'message-content';
        bubble.innerHTML = '<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>';
        wrapper.appendChild(avatar);
        wrapper.appendChild(bubble);
        this.messages.appendChild(wrapper);
        this._scrollBottom();
        return wrapper;
    },

    _scrollBottom() {
        if (this.messages) this.messages.scrollTop = this.messages.scrollHeight;
    },

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    }
};

document.addEventListener('DOMContentLoaded', () => NeptunoChat.init());
