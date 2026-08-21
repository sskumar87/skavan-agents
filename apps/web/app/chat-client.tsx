"use client";

import { FormEvent, ReactNode, useEffect, useRef, useState } from "react";

type ChatMessage = { id: string; role: "user" | "assistant"; content: string };
type StreamEvent = { event: string; data: Record<string, unknown> };
type ThemeName = "neon-grid" | "violet-pulse" | "amber-terminal" | "daylight-circuit";

const themes: { value: ThemeName; label: string }[] = [
  { value: "neon-grid", label: "Neon Grid" },
  { value: "violet-pulse", label: "Violet Pulse" },
  { value: "amber-terminal", label: "Amber Terminal" },
  { value: "daylight-circuit", label: "Daylight Circuit" },
];

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

export function ChatClient({ account, userName }: { account: ReactNode; userName: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [prompt, setPrompt] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isReceiving, setIsReceiving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hermesStatus, setHermesStatus] = useState<"checking" | "online" | "offline">("checking");
  const [theme, setTheme] = useState<ThemeName>("neon-grid");
  const [isThemeMenuOpen, setIsThemeMenuOpen] = useState(false);
  const [isThreadDrawerOpen, setIsThreadDrawerOpen] = useState(false);
  const [canScrollUp, setCanScrollUp] = useState(false);
  const [canScrollDown, setCanScrollDown] = useState(false);
  const messagesRef = useRef<HTMLDivElement>(null);
  const followBottomRef = useRef(true);

  useEffect(() => {
    fetch("/bff/hermes/health")
      .then((response) => response.json())
      .then((payload: { status?: string }) => setHermesStatus(payload.status === "ok" ? "online" : "offline"))
      .catch(() => setHermesStatus("offline"));
  }, []);

  function updateScrollControls() {
    const element = messagesRef.current;
    if (!element) return;
    const distanceFromBottom = element.scrollHeight - element.scrollTop - element.clientHeight;
    const isNearBottom = distanceFromBottom < 80;
    followBottomRef.current = isNearBottom;
    setCanScrollUp(element.scrollTop > 80);
    setCanScrollDown(!isNearBottom);
  }

  function scrollMessages(position: "top" | "bottom") {
    const element = messagesRef.current;
    if (!element) return;
    const toBottom = position === "bottom";
    followBottomRef.current = toBottom;
    element.scrollTo({ top: toBottom ? element.scrollHeight : 0, behavior: "smooth" });
  }

  useEffect(() => {
    if (isLoadingHistory) return;
    followBottomRef.current = true;
    requestAnimationFrame(() => {
      const element = messagesRef.current;
      if (!element) return;
      element.scrollTop = element.scrollHeight;
      updateScrollControls();
    });
  }, [isLoadingHistory]);

  useEffect(() => {
    if (!followBottomRef.current) return;
    requestAnimationFrame(() => {
      const element = messagesRef.current;
      if (!element) return;
      element.scrollTop = element.scrollHeight;
      updateScrollControls();
    });
  }, [messages, isSending]);

  useEffect(() => {
    fetch("/bff/users/me", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Unable to load user preferences");
        return response.json() as Promise<{ preferences?: { theme?: ThemeName } }>;
      })
      .then(({ preferences }) => {
        const saved = preferences?.theme;
        if (!saved || !themes.some((item) => item.value === saved)) return;
        document.documentElement.dataset.theme = saved;
        window.localStorage.setItem("skavan-theme", saved);
        setTheme(saved);
      })
      .catch(() => setTheme((document.documentElement.dataset.theme as ThemeName) || "neon-grid"));
  }, []);

  async function selectTheme(value: ThemeName) {
    const previous = theme;
    document.documentElement.dataset.theme = value;
    window.localStorage.setItem("skavan-theme", value);
    setTheme(value);
    try {
      const response = await fetch("/bff/users/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme: value }),
      });
      if (!response.ok) throw new Error("Unable to save theme");
    } catch {
      document.documentElement.dataset.theme = previous;
      window.localStorage.setItem("skavan-theme", previous);
      setTheme(previous);
      setError("Theme preference could not be saved.");
    }
  }

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
    followBottomRef.current = true;
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
    <main className="workspaceShell">
      <aside className="primaryRail">
        <a className="workspaceBrand" href="/" aria-label="Skav Platform home">
          <img src="/skav-mark.svg" alt="" aria-hidden="true" />
          <span>SKAV PLATFORM</span>
        </a>
        <nav className="primaryNavigation" aria-label="Primary navigation">
          <button type="button" className="active" aria-current="page"><NavIcon kind="user" />Personal</button>
          <button type="button" disabled title="Groups are the next development slice"><NavIcon kind="groups" />Groups</button>
          <button type="button" disabled title="Approvals are planned for V1"><NavIcon kind="shield" />Approvals</button>
          <button type="button" disabled title="Connections are planned for V1"><NavIcon kind="link" />Connections</button>
          <button type="button" disabled title="Settings are coming next"><NavIcon kind="settings" />Settings</button>
        </nav>
      </aside>

      <header className="workspaceTopbar">
        <button
          className="backButton"
          type="button"
          aria-label="Open threads"
          aria-expanded={isThreadDrawerOpen}
          onClick={() => setIsThreadDrawerOpen(true)}
        >‹</button>
        <div className="workspaceSearch" aria-label="Search is coming in the groups slice">
          <NavIcon kind="search" /><span>Search across your groups...</span><kbd>⌘ K</kbd>
        </div>
        <div className="workspaceActions">
          <button
            className="themeMenuButton"
            type="button"
            aria-label="Choose theme"
            aria-expanded={isThemeMenuOpen}
            onClick={() => setIsThemeMenuOpen((open) => !open)}
          >☼</button>
          <div className="desktopAccount">{account}</div>
        </div>
        {isThemeMenuOpen && (
          <section className="themeMenu uiPanel" aria-label="Theme selection">
            <div className="themeMenuTitle">Theme</div>
            <div className="themeGrid">
              {themes.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  className={`themeCard ${item.value}`}
                  aria-pressed={theme === item.value}
                  onClick={() => selectTheme(item.value)}
                >
                  <span className="themePreview"><i /><i /><i /></span>
                  <strong>{item.label}</strong>
                </button>
              ))}
            </div>
            <p>✓ Saved to your profile</p>
          </section>
        )}
      </header>

      <aside className="threadRail">
        <div className="workspaceIdentity"><strong>Personal</strong><span>Private workspace</span></div>
        <button className="newThreadButton" type="button" disabled title="Multiple threads are the next development slice">＋ New thread</button>
        <div className="threadList" aria-label="Threads">
          <button className="threadItem active" type="button">
            <span className="threadGlyph">◇</span>
            <span><strong>General</strong><small>Your private Hermes thread</small></span>
          </button>
        </div>
      </aside>

      <section className="conversationPane" aria-label="Chat with Hermes">
        <header className="conversationHeader">
          <div><h1>General</h1><p>Personal</p></div>
          <div className={`status ${hermesStatus}`} aria-label={`Hermes ${hermesStatus}`}>
            <span className="statusDot" aria-hidden="true" />Hermes {hermesStatus}
          </div>
        </header>
        <div className="messages" aria-live="polite" ref={messagesRef} onScroll={updateScrollControls}>
          <div className="dayDivider"><span>Today</span></div>
          {messages.map((message) => (
            <article className={`message ${message.role}`} key={message.id}>
              <span className="messageAvatar">{message.role === "assistant" ? "H" : userName.slice(0, 1).toUpperCase()}</span>
              <div className="messageBody">
                <div className="messageMeta">{message.role === "assistant" ? "Hermes · Agent" : userName}</div>
                <p>{message.content}</p>
              </div>
            </article>
          ))}
          {isSending && !isReceiving && (
            <article className="message assistant pending">
              <span className="messageAvatar">H</span>
              <div className="messageBody"><div className="messageMeta">Hermes · Agent</div><p>Processing<span className="pulse">...</span></p></div>
            </article>
          )}
        </div>
        <div className="scrollControls" aria-label="Conversation scroll controls">
          {canScrollUp && <button type="button" onClick={() => scrollMessages("top")} aria-label="Scroll to first message">↑</button>}
          {canScrollDown && <button type="button" onClick={() => scrollMessages("bottom")} aria-label="Scroll to latest message">↓</button>}
        </div>
        <div className="composerArea">
          {error && <p className="error" role="alert">{error}</p>}
          <form className="composer" onSubmit={sendMessage}>
            <span className="composerIcon" aria-hidden="true">⌁</span>
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
              placeholder="Message General..."
              rows={1}
              disabled={isSending || isLoadingHistory}
            />
            <button type="submit" disabled={!prompt.trim() || isSending || isLoadingHistory}>
              {isLoadingHistory ? "Loading" : isSending ? "Sending" : "Send"}
            </button>
          </form>
          <p className="hint">Hermes may make mistakes. Verify important information.</p>
        </div>
      </section>

      <aside className="contextRail">
        <h2>Context</h2>
        <section className="contextSection">
          <span className="contextLabel">Signed in user</span>
          <div className="contextUser"><span>{userName.slice(0, 1).toUpperCase()}</span><div><strong>{userName}</strong><small>Immutable identity</small></div></div>
          <div className="contextRow"><span>Role</span><strong>Owner</strong></div>
        </section>
        <section className="contextSection">
          <span className="contextLabel">Personal memory (private)</span>
          <div className="contextFeature"><span>▤</span><div><strong>Personal</strong><small>Relevant personal memory only.<br />Thread history stays separate.</small></div></div>
        </section>
        <section className="contextSection">
          <span className="contextLabel">Selected agent</span>
          <div className="contextFeature"><span>H</span><div><strong>Hermes</strong><small>Personal assistant</small></div><i className="onlineMark" /></div>
        </section>
        <section className="contextSection capabilities">
          <span className="contextLabel">Available now</span>
          <p>✓ Answer questions</p><p>✓ Conversation history</p><p>✓ Theme preference</p>
        </section>
      </aside>

      {isThreadDrawerOpen && (
        <>
          <div className="threadDrawerBackdrop open" onClick={() => setIsThreadDrawerOpen(false)} />
          <aside className="threadDrawer open" aria-label="Thread navigation">
            <div className="threadDrawerHeader">
              <div><strong>Personal</strong><span>Private workspace</span></div>
              <button type="button" onClick={() => setIsThreadDrawerOpen(false)} aria-label="Close threads">×</button>
            </div>
            <button className="threadItem active" type="button" onClick={() => setIsThreadDrawerOpen(false)}>
              <span className="threadGlyph">◇</span>
              <span><strong>General</strong><small>Your private Hermes thread</small></span>
            </button>
          </aside>
        </>
      )}

      <nav className="mobileNavigation" aria-label="Mobile navigation">
        <button type="button" className="active" aria-current="page"><NavIcon kind="user" /><span>Home</span></button>
        <button type="button" disabled><NavIcon kind="groups" /><span>Groups</span></button>
        <button type="button" disabled><NavIcon kind="shield" /><span>Approvals</span></button>
        <button type="button" disabled><NavIcon kind="settings" /><span>Settings</span></button>
      </nav>
    </main>
  );
}

function NavIcon({ kind }: { kind: string }) {
  const paths: Record<string, string> = {
    user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0",
    groups: "M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm8-1a2.5 2.5 0 1 0 0-5M2.5 20a5.5 5.5 0 0 1 11 0m1-6a5 5 0 0 1 7 4.6",
    shield: "M12 3 5 6v5c0 4.5 2.8 8 7 10 4.2-2 7-5.5 7-10V6l-7-3Zm-3 9 2 2 4-5",
    link: "M9.5 14.5 14.5 9M7 17H5a4 4 0 0 1 0-8h3m8 0h3a4 4 0 0 1 0 8h-3",
    settings: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm0-12v2m0 13v2m8.5-8.5h-2m-13 0h-2m14.5-6-1.5 1.5m-9 9L6 18m12 0-1.5-1.5m-9-9L6 6",
    search: "m20 20-4.5-4.5M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z",
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d={paths[kind]} /></svg>;
}
