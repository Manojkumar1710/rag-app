import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Send } from "lucide-react";
import type { ChatMessage } from "../types/api";
import { streamChatMessage } from "../services/api";
import ErrorBanner from "../components/ErrorBanner";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  async function handleSend() {
    const text = input.trim();
    if (!text || isStreaming) return;

    setError("");
    const userMessage: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage, { role: "assistant", content: "" }]);
    setInput("");
    setIsStreaming(true);

    let accumulated = "";

    await streamChatMessage(
      text,
      (token) => {
        accumulated += token;
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { role: "assistant", content: accumulated };
          return next;
        });
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      },
      (citations) => {
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { role: "assistant", content: accumulated, citations };
          return next;
        });
        setIsStreaming(false);
      },
      (err) => {
        setError(err);
        setIsStreaming(false);
      }
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <h1 className="page-title">AI Chat</h1>
      <p className="page-subtitle">Ask questions grounded in your indexed documents.</p>

      <ErrorBanner message={error} />

      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 16, paddingBottom: 16 }}>
        {messages.length === 0 && (
          <div className="card" style={{ color: "var(--text-secondary)" }}>
            Start a conversation. Upload documents first for grounded answers.
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={`card chat-message ${m.role === "user" ? "user-message" : "assistant-message"}`}
            style={{
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              background: m.role === "user" ? "var(--accent)" : "var(--bg-card)",
              color: m.role === "user" ? "white" : "var(--text-primary)",
            }}
          >
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content || "..."}</ReactMarkdown>
            </div>

            {m.citations && m.citations.length > 0 && (
              <div style={{ marginTop: 10, borderTop: "1px solid var(--border)", paddingTop: 8 }}>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 6 }}>Sources</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {m.citations.map((c, idx) => (
                    <span key={idx} className="badge" title={c.snippet}>
                      {c.filename} {c.page ? `(p.${c.page})` : `#${c.chunk_number}`}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div style={{ display: "flex", gap: 10, paddingTop: 10 }}>
        <input
          type="text"
          style={{ flex: 1 }}
          placeholder="Ask something about your documents..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          disabled={isStreaming}
        />
        <button className="btn" onClick={handleSend} disabled={isStreaming || !input.trim()}>
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
