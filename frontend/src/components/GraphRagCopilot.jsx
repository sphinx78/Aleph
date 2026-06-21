// frontend/src/components/GraphRagCopilot.jsx
import React, { useState, useRef, useEffect } from 'react';
import AlephCard from './AlephCard';
import { Send } from 'lucide-react';

const renderMarkdown = (text) => {
  if (!text) return null;
  const lines = text.split('\n');
  return lines.map((line, idx) => {

    // Bullet: must start with "* " OR "- " (with a space), NOT "**" (bold)
    const isBullet = /^\s*(\*|-)\s+/.test(line) && !/^\s*\*\*/.test(line);
    if (isBullet) {
      const bulletText = line.replace(/^\s*[*-]\s+/, '');
      const formatted = bulletText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      return (
        <ul key={idx} className="list-disc pl-4 mb-0.5">
          <li dangerouslySetInnerHTML={{ __html: formatted }} />
        </ul>
      );
    }

    // Numbered list: "1. item"
    const numMatch = line.trim().match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      const rest = numMatch[2].replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      return (
        <ol key={idx} className="list-decimal pl-4 mb-0.5">
          <li value={parseInt(numMatch[1], 10)} dangerouslySetInnerHTML={{ __html: rest }} />
        </ol>
      );
    }

    // Dividers: ==== or ----
    if (/^={4,}$/.test(line.trim()) || /^-{4,}$/.test(line.trim())) {
      return <hr key={idx} className="border-t border-[#EAE1D4] my-2" />;
    }

    // Empty lines
    if (line.trim() === '') {
      return <div key={idx} className="h-1" />;
    }

    // Replace bold **text** AFTER all structural checks
    const content = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    return (
      <p
        key={idx}
        className="mb-0.5"
        dangerouslySetInnerHTML={{ __html: content }}
      />
    );
  });
};

export default function GraphRagCopilot({ accountId, accountMetrics }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  // Reset messages when account changes
  useEffect(() => {
    setMessages([
      {
        sender: 'system',
        text: `ALEPH Copilot initialised. Target: Account ${accountId || '—'}`
      }
    ]);
  }, [accountId]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput('');
    setLoading(true);

    setMessages(prev => [...prev, { sender: 'user', text: userText }]);
    // Placeholder for the incoming stream
    setMessages(prev => [...prev, { sender: 'copilot', text: '' }]);

    try {
      const response = await fetch('/api/copilot/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          account_id: accountId,
          message: userText,
          metrics: accountMetrics || {}
        })
      });

      if (!response.ok) throw new Error(`Backend error: ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const raw = decoder.decode(value, { stream: true });
        // SSE lines are separated by double newline
        const lines = raw.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const parsed = JSON.parse(line.slice(6));
              const token = parsed.token || '';
              if (token) {
                setMessages(prev => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  updated[updated.length - 1] = { ...last, text: last.text + token };
                  return updated;
                });
              }
            } catch {
              // ignore parse errors on partial chunks
            }
          }
        }
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { sender: 'system', text: `Connection error: ${err.message}` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const senderLabel = { user: 'Analyst', copilot: 'ALEPH Copilot', system: 'System' };
  const senderStyle = {
    user: 'bg-[#FAF7F2] border-[#EAE1D4] text-[#2D2D2D]',
    copilot: 'bg-[#99B29B]/8 border-[#99B29B]/25 text-[#2D2D2D]',
    system: 'bg-transparent border-transparent text-[#6B6864] italic text-center'
  };

  return (
    <AlephCard className="p-8 h-[480px]">
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="mb-5 shrink-0">
          <span className="text-[9px] uppercase tracking-[0.2em] text-[#C07A50] font-bold">
            AI Analyst Copilot
          </span>
          <h3 className="text-xl font-serif font-bold text-[#2D2D2D] mt-0.5">
            Graph-RAG Inquiry Engine
          </h3>
          <p className="text-xs text-[#6B6864] font-light mt-0.5">
            Powered by Llama 3.1 · Context-aware AML analysis
          </p>
        </div>

        {/* Message thread */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto space-y-2.5 pr-1 mb-4"
        >
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`px-3 py-2.5 rounded-lg border text-xs leading-relaxed font-mono ${senderStyle[m.sender]}`}
            >
              <span className="block text-[8px] uppercase tracking-widest font-bold text-[#C07A50] mb-0.5">
                {senderLabel[m.sender] || m.sender}
              </span>
              <div className="block text-[11px] leading-relaxed">
                {/* Stream raw text during generation; snap to markdown when done */}
                {loading && idx === messages.length - 1 && m.sender === 'copilot'
                  ? (
                    <span className="whitespace-pre-wrap break-words">
                      {m.text}
                      <span className="inline-block w-1.5 h-3 bg-[#99B29B] ml-0.5 animate-pulse rounded-sm" />
                    </span>
                  )
                  : renderMarkdown(m.text)
                }
              </div>
            </div>
          ))}
        </div>

        {/* Input bar */}
        <form
          onSubmit={handleSend}
          className="flex items-center space-x-2 border-t border-[#EAE1D4] pt-4 shrink-0"
        >
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            disabled={loading}
            placeholder="Ask about structuring risk, layering chains, or draft a SAR..."
            className="flex-1 bg-[#FAF7F2] border border-[#EAE1D4] rounded-lg px-3.5 py-2 text-xs
                       text-[#2D2D2D] placeholder-[#A3917A] font-mono
                       focus:outline-none focus:border-[#99B29B] focus:ring-1 focus:ring-[#99B29B]/30
                       disabled:opacity-50 transition-colors"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="flex items-center space-x-1.5 bg-[#2D2D2D] text-white px-4 py-2 rounded-lg
                       text-[10px] font-semibold uppercase tracking-wider
                       hover:bg-[#1A1A1A] disabled:opacity-40 disabled:cursor-not-allowed
                       transition-all duration-200 shrink-0"
          >
            <Send size={11} />
            <span>Send</span>
          </button>
        </form>
      </div>
    </AlephCard>
  );
}
