"use client";

import { FormEvent, useEffect, useState } from "react";

type ChatMessage = { id: string; role: "user" | "assistant"; content: string };

const initialMessages: ChatMessage[] = [{
  id: "welcome",
  role: "assistant",
  content: "Hermes link ready. What are we building?",
}];

function responseText(payload: unknown): string {
  if (typeof payload === "string") return payload;
  if (!payload || typeof payload !== "object") return "Hermes returned an empty response.";

  const body = payload as Record<string, unknown>;
  if (body.message && typeof body.message === "object") {
    const message = body.message as Record<string, unknown>;
    if (typeof message.content === "string") return message.content;
  }
  for (const key of ["reply", "message", "content", "response"]) {
    if (typeof body[key] === "string") return body[key];
  }
  return "Hermes returned an unsupported response shape.";
}

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [prompt, setPrompt] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hermesStatus, setHermesStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    fetch("/api/hermes/health")
      .then((response) => response.json())
      .then((payload: { status?: string }) => setHermesStatus(payload.status === "ok" ? "online" : "offline"))
      .catch(() => setHermesStatus("offline"));
  }, []);

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = prompt.trim();
    if (!message || isSending) return;

    setPrompt("");
    setError(null);
    setIsSending(true);
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content: message };
    const conversation = [...messages, userMessage];
    setMessages(conversation);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: conversation
            .filter((item) => item.id !== "welcome")
            .map(({ role, content }) => ({ role, content })),
        }),
      });
      if (!response.ok) throw new Error(`Hermes request failed (${response.status})`);

      const contentType = response.headers.get("content-type") ?? "";
      const payload: unknown = contentType.includes("application/json")
        ? await response.json()
        : await response.text();
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "assistant", content: responseText(payload) },
      ]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to reach Hermes.");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brandMark" aria-hidden="true">S</span>
          <div><p className="eyebrow">SKAV PLATFORM</p><h1>Hermes Console</h1></div>
        </div>
        <div className={`status ${hermesStatus}`} aria-label={`Hermes ${hermesStatus}`}>
          <span className="statusDot" aria-hidden="true" />{hermesStatus.toUpperCase()}
        </div>
      </header>

      <section className="chat" aria-label="Chat with Hermes">
        <div className="messages" aria-live="polite">
          {messages.map((message) => (
            <article className={`message ${message.role}`} key={message.id}>
              <div className="messageMeta">{message.role === "assistant" ? "HERMES" : "YOU"}</div>
              <p>{message.content}</p>
            </article>
          ))}
          {isSending && (
            <article className="message assistant pending">
              <div className="messageMeta">HERMES</div><p>Processing<span className="pulse">...</span></p>
            </article>
          )}
        </div>

        <div className="composerArea">
          {error && <p className="error" role="alert">{error}</p>}
          <form className="composer" onSubmit={sendMessage}>
            <label className="srOnly" htmlFor="prompt">Message Hermes</label>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              placeholder="Ask Hermes anything..."
              rows={1}
              disabled={isSending}
            />
            <button type="submit" disabled={!prompt.trim() || isSending}>{isSending ? "Sending" : "Send"}</button>
          </form>
          <p className="hint">Enter to send · Shift + Enter for a new line</p>
        </div>
      </section>
    </main>
  );
}
