"use client";

import { FormEvent, ReactNode, useEffect, useState } from "react";

type ChatMessage = { id: string; role: "user" | "assistant"; content: string };
type StreamEvent = { event: string; data: Record<string, unknown> };

const initialMessages: ChatMessage[] = [{
  id: "welcome",
  role: "assistant",
  content: "Hermes link ready. What are we building?",
}];

function parseStreamEvent(block: string): StreamEvent | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) data.push(line.slice(5).trim());
  }
  if (!data.length) return null;
  const payload: unknown = JSON.parse(data.join("\n"));
  return payload && typeof payload === "object"
    ? { event, data: payload as Record<string, unknown> }
    : null;
}

export function ChatClient({ account }: { account: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [prompt, setPrompt] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isReceiving, setIsReceiving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hermesStatus, setHermesStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    fetch("/bff/hermes/health")
      .then((response) => response.json())
      .then((payload: { status?: string }) => setHermesStatus(payload.status === "ok" ? "online" : "offline"))
      .catch(() => setHermesStatus("offline"));
  }, []);

  useEffect(() => {
    fetch("/bff/chat/history", { cache: "no-store" })
      .then(async (response) => {
        if (response.status === 401) {
          window.location.assign("/login");
          return [];
        }
        if (!response.ok) throw new Error("Unable to load chat history");
        return response.json() as Promise<ChatMessage[]>;
      })
      .then((history) => setMessages(history.length ? history : initialMessages))
      .catch(() => setError("Chat history could not be loaded."))
      .finally(() => setIsLoadingHistory(false));
  }, []);

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = prompt.trim();
    if (!message || isSending || isLoadingHistory) return;

    setPrompt("");
    setError(null);
    setIsSending(true);
    setIsReceiving(false);
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content: message };
    const conversation = [...messages, userMessage];
    setMessages(conversation);

    try {
      const response = await fetch("/bff/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: message }],
        }),
      });
      if (response.status === 401) {
        window.location.assign("/login");
        return;
      }
      if (!response.ok || !response.body) throw new Error(`Hermes request failed (${response.status})`);

      const assistantId = crypto.randomUUID();
      let assistantAdded = false;
      let buffer = "";
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      const handleBlock = (block: string) => {
        const item = parseStreamEvent(block);
        if (!item) return;
        if (item.event === "error") {
          throw new Error(typeof item.data.message === "string" ? item.data.message : "Hermes stream failed.");
        }
        if (item.event !== "token" || typeof item.data.content !== "string") return;
        const token = item.data.content;
        if (!assistantAdded) {
          assistantAdded = true;
          setIsReceiving(true);
          setMessages((current) => [...current, { id: assistantId, role: "assistant", content: token }]);
        } else {
          setMessages((current) => current.map((item) => item.id === assistantId
            ? { ...item, content: item.content + token }
            : item));
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        buffer = (buffer + decoder.decode(value, { stream: !done })).replaceAll("\r\n", "\n");
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";
        blocks.forEach(handleBlock);
        if (done) break;
      }
      if (buffer.trim()) handleBlock(buffer);
      if (!assistantAdded) throw new Error("Hermes returned an empty response.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to reach Hermes.");
    } finally {
      setIsSending(false);
      setIsReceiving(false);
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <img className="brandLogo" src="/skav-mark.svg" alt="" aria-hidden="true" />
          <div><p className="eyebrow">SKAV PLATFORM</p><h1>Hermes Console</h1></div>
        </div>
        <div className="topbarActions">
          <div className={`status ${hermesStatus}`} aria-label={`Hermes ${hermesStatus}`}>
            <span className="statusDot" aria-hidden="true" />{hermesStatus.toUpperCase()}
          </div>
          {account}
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
          {isSending && !isReceiving && (
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
              disabled={isSending || isLoadingHistory}
            />
            <button type="submit" disabled={!prompt.trim() || isSending || isLoadingHistory}>
              {isLoadingHistory ? "Loading" : isSending ? "Sending" : "Send"}
            </button>
          </form>
          <p className="hint">Enter to send · Shift + Enter for a new line</p>
        </div>
      </section>
    </main>
  );
}
