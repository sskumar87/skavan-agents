"use client";

import { FormEvent, ReactNode, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  isCurrentUser?: boolean;
  authorName?: string | null;
};
type StoredChatMessage = Omit<ChatMessage, "isCurrentUser" | "authorName"> & {
  is_current_user: boolean;
  author_name?: string | null;
};
type StreamEvent = { event: string; data: Record<string, unknown> };
type ThreadSource = "skavan" | "hermes";
type ChatThread = {
  id: string;
  nativeId: string;
  title: string;
  source: ThreadSource;
  preview?: string | null;
  activityAt: number;
};
type StoredThread = { id: string; title: string; last_active?: string | null };
type HermesSession = { id: string; title: string; preview?: string | null; last_active?: number | null };
type ProfileKey = "personal" | "work";
type ChatProfile = { key: ProfileKey; label: string };
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

function activityTimestamp(value: string | number | null | undefined): number {
  if (typeof value === "string") return Number.isNaN(Date.parse(value)) ? 0 : Date.parse(value);
  if (typeof value !== "number" || !Number.isFinite(value)) return 0;
  return value < 1_000_000_000_000 ? value * 1000 : value;
}

function newestFirst(items: ChatThread[]): ChatThread[] {
  return [...items].sort((left, right) => right.activityAt - left.activityAt);
}

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
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [profiles, setProfiles] = useState<ChatProfile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<ProfileKey | null>(null);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [prompt, setPrompt] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isReceiving, setIsReceiving] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hermesStatus, setHermesStatus] = useState<"checking" | "online" | "offline">("checking");
  const [theme, setTheme] = useState<ThemeName>("neon-grid");
  const [isThemeMenuOpen, setIsThemeMenuOpen] = useState(false);
  const [isThreadDrawerOpen, setIsThreadDrawerOpen] = useState(false);
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [deletingThread, setDeletingThread] = useState<ChatThread | null>(null);
  const [isDeletingThread, setIsDeletingThread] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [canScrollUp, setCanScrollUp] = useState(false);
  const [canScrollDown, setCanScrollDown] = useState(false);
  const messagesRef = useRef<HTMLDivElement>(null);
  const promptRef = useRef<HTMLTextAreaElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const drawerSearchInputRef = useRef<HTMLInputElement>(null);
  const followBottomRef = useRef(true);

  useEffect(() => {
    fetch("/bff/hermes/health")
      .then((response) => response.json())
      .then((payload: { status?: string }) => setHermesStatus(payload.status === "ok" ? "online" : "offline"))
      .catch(() => setHermesStatus("offline"));
  }, []);

  useEffect(() => {
    const textarea = promptRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const maximumHeight = Number.parseFloat(window.getComputedStyle(textarea).maxHeight);
    const nextHeight = Math.min(textarea.scrollHeight, maximumHeight);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > maximumHeight ? "auto" : "hidden";
  }, [prompt]);

  useEffect(() => {
    function focusSearch(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchInputRef.current?.focus();
      }
      if (event.key === "Escape" && [searchInputRef.current, drawerSearchInputRef.current].includes(document.activeElement as HTMLInputElement)) {
        setSearchQuery("");
        searchInputRef.current?.blur();
        drawerSearchInputRef.current?.blur();
      }
    }
    window.addEventListener("keydown", focusSearch);
    return () => window.removeEventListener("keydown", focusSearch);
  }, []);

  useEffect(() => {
    if (!isThreadDrawerOpen || document.activeElement !== searchInputRef.current) return;
    requestAnimationFrame(() => drawerSearchInputRef.current?.focus());
  }, [isThreadDrawerOpen]);

  function openMobileSearch() {
    if (window.matchMedia("(max-width: 900px)").matches) setIsThreadDrawerOpen(true);
  }

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
    fetch("/bff/chat/profiles", { cache: "no-store" })
      .then(async (response) => {
        if (response.status === 401) {
          window.location.assign("/login");
          return [];
        }
        if (!response.ok) throw new Error("Unable to load profile roles");
        return response.json() as Promise<ChatProfile[]>;
      })
      .then((items) => {
        setProfiles(items);
        setSelectedProfile(items[0]?.key ?? null);
        if (!items.length) {
          setError("No Personal or Work role is present in your login token.");
          setIsLoadingHistory(false);
        }
      })
      .catch(() => {
        setError("Profile roles could not be loaded.");
        setIsLoadingHistory(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedProfile) return;
    setIsLoadingHistory(true);
    setThreads([]);
    setSelectedThreadId(null);
    setMessages(initialMessages);
    Promise.all([
      fetch(`/bff/chat/threads?profile=${encodeURIComponent(selectedProfile)}`, { cache: "no-store" }),
      fetch(`/bff/hermes/sessions?profile=${encodeURIComponent(selectedProfile)}`, { cache: "no-store" }),
    ])
      .then(async ([threadResponse, sessionResponse]) => {
        if (threadResponse.status === 401 || sessionResponse.status === 401) {
          window.location.assign("/login");
          return [];
        }
        if (!threadResponse.ok) throw new Error("Unable to load chats");
        const stored = await threadResponse.json() as StoredThread[];
        const native = sessionResponse.ok ? await sessionResponse.json() as HermesSession[] : [];
        return newestFirst([
          ...stored.map((thread): ChatThread => ({
            id: `skavan:${thread.id}`, nativeId: thread.id, title: thread.title, source: "skavan",
            activityAt: activityTimestamp(thread.last_active),
          })),
          ...native.map((session): ChatThread => ({
            id: `hermes:${session.id}`, nativeId: session.id, title: session.title,
            source: "hermes", preview: session.preview, activityAt: activityTimestamp(session.last_active),
          })),
        ]);
      })
      .then((items) => {
        setThreads(items);
        setSelectedThreadId(items[0]?.id ?? null);
        if (!items.length) setIsLoadingHistory(false);
      })
      .catch(() => {
        setError("Threads could not be loaded.");
        setIsLoadingHistory(false);
      });
  }, [selectedProfile]);

  useEffect(() => {
    if (!selectedThreadId || !selectedProfile) return;
    const selectedThread = threads.find((thread) => thread.id === selectedThreadId);
    if (!selectedThread) return;
    setIsLoadingHistory(true);
    const historyUrl = selectedThread.source === "hermes"
      ? `/bff/hermes/sessions/${encodeURIComponent(selectedThread.nativeId)}/messages?profile=${encodeURIComponent(selectedProfile)}`
      : `/bff/chat/history?profile=${encodeURIComponent(selectedProfile)}&thread_id=${encodeURIComponent(selectedThread.nativeId)}`;
    fetch(historyUrl, { cache: "no-store" })
      .then(async (response) => {
        if (response.status === 401) {
          window.location.assign("/login");
          return [];
        }
        if (!response.ok) throw new Error("Unable to load chat history");
        const history = await response.json() as StoredChatMessage[];
        return history.map((message) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          isCurrentUser: message.is_current_user,
          authorName: message.author_name,
        }));
      })
      .then((history) => setMessages(history.length ? history : initialMessages))
      .catch(() => setError("Chat history could not be loaded."))
      .finally(() => setIsLoadingHistory(false));
  }, [selectedProfile, selectedThreadId, threads]);

  async function createThread() {
    setError(null);
    try {
      if (!selectedProfile) throw new Error("Choose a profile first");
      const response = await fetch("/bff/chat/threads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile: selectedProfile }),
      });
      if (!response.ok) throw new Error("Unable to create a new chat");
      const stored = await response.json() as StoredThread;
      const thread: ChatThread = {
        id: `skavan:${stored.id}`, nativeId: stored.id, title: stored.title, source: "skavan",
        activityAt: activityTimestamp(stored.last_active) || Date.now(),
      };
      setThreads((current) => [thread, ...current]);
      setSelectedThreadId(thread.id);
      setMessages(initialMessages);
      setIsThreadDrawerOpen(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to create a new chat.");
    }
  }

  function selectProfile(profile: ProfileKey) {
    setError(null);
    setSelectedThreadId(null);
    setSelectedProfile(profile);
  }

  function selectThread(threadId: string) {
    setSelectedThreadId(threadId);
    setIsThreadDrawerOpen(false);
  }

  function beginRename(thread: ChatThread) {
    setEditingThreadId(thread.id);
    setEditingTitle(thread.title);
  }

  async function renameThread(event: FormEvent<HTMLFormElement>, thread: ChatThread) {
    event.preventDefault();
    const title = editingTitle.trim();
    if (!selectedProfile || thread.source !== "skavan" || !title) return;
    setError(null);
    try {
      const response = await fetch(`/bff/chat/threads/${encodeURIComponent(thread.nativeId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile: selectedProfile, title }),
      });
      if (!response.ok) throw new Error("Unable to rename this chat");
      const updated = await response.json() as StoredThread;
      setThreads((current) => current.map((item) => item.id === thread.id
        ? { ...item, title: updated.title }
        : item));
      setEditingThreadId(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to rename this chat.");
    }
  }

  async function deleteThread() {
    if (!selectedProfile || !deletingThread || deletingThread.source !== "skavan") return;
    setError(null);
    setIsDeletingThread(true);
    try {
      const response = await fetch(
        `/bff/chat/threads/${encodeURIComponent(deletingThread.nativeId)}?profile=${encodeURIComponent(selectedProfile)}`,
        { method: "DELETE" },
      );
      if (!response.ok) throw new Error("Unable to delete this chat");
      const remaining = threads.filter((thread) => thread.id !== deletingThread.id);
      setThreads(remaining);
      if (selectedThreadId === deletingThread.id) {
        setSelectedThreadId(remaining[0]?.id ?? null);
        if (!remaining.length) setMessages(initialMessages);
      }
      setDeletingThread(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to delete this chat.");
    } finally {
      setIsDeletingThread(false);
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = prompt.trim();
    if (!message || isSending || isLoadingHistory) return;

    setPrompt("");
    setError(null);
    setIsSending(true);
    setIsReceiving(false);
    setStreamingMessageId(null);
    followBottomRef.current = true;
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(), role: "user", content: message,
      isCurrentUser: true, authorName: userName,
    };
    const conversation = [...messages, userMessage];
    setMessages(conversation);

    try {
      const activeThread = threads.find((thread) => thread.id === selectedThreadId);
      if (!activeThread || !selectedProfile) throw new Error("Choose a chat first");
      setThreads((current) => newestFirst(current.map((thread) => thread.id === activeThread.id
        ? { ...thread, activityAt: Date.now() }
        : thread)));
      const streamUrl = activeThread.source === "hermes"
        ? `/bff/hermes/sessions/${encodeURIComponent(activeThread.nativeId)}/chat/stream`
        : "/bff/chat/stream";
      const requestBody = activeThread.source === "hermes"
        ? { message, profile: selectedProfile }
        : {
            messages: [{ role: "user", content: message }],
            thread_id: activeThread.nativeId,
            profile: selectedProfile,
          };
      const response = await fetch(streamUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
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
          setStreamingMessageId(assistantId);
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
      const detail = cause instanceof Error ? cause.message : "";
      const interrupted = cause instanceof TypeError || detail === "Load failed" || detail === "Failed to fetch";
      setError(interrupted
        ? "Connection interrupted. Hermes may still be working; reopen this chat to refresh its saved response."
        : detail || "Unable to reach Hermes.");
    } finally {
      setIsSending(false);
      setIsReceiving(false);
      setStreamingMessageId(null);
    }
  }

  function renderThreadList() {
    const normalizedQuery = searchQuery.trim().toLocaleLowerCase();
    const visibleThreads = normalizedQuery
      ? threads.filter((thread) => [thread.title, thread.preview, thread.source]
        .some((value) => value?.toLocaleLowerCase().includes(normalizedQuery)))
      : threads;

    return (
      <div className="threadList" aria-label="Chats and Hermes sessions">
        {visibleThreads.map((thread) => editingThreadId === thread.id ? (
          <form className="threadRenameForm" key={thread.id} onSubmit={(event) => renameThread(event, thread)}>
            <label className="srOnly" htmlFor={`rename-${thread.id}`}>Rename chat</label>
            <input
              id={`rename-${thread.id}`}
              value={editingTitle}
              onChange={(event) => setEditingTitle(event.target.value)}
              maxLength={300}
              autoFocus
            />
            <button type="submit" aria-label="Save chat name">✓</button>
            <button type="button" aria-label="Cancel rename" onClick={() => setEditingThreadId(null)}>×</button>
          </form>
        ) : (
          <div className={`threadItemWrap ${thread.id === selectedThreadId ? "active" : ""}`} key={thread.id}>
            <button className="threadItem" type="button" onClick={() => selectThread(thread.id)}>
              <span className="threadGlyph">{thread.source === "hermes" ? "H" : "◇"}</span>
              <span>
                <strong>{thread.title}</strong>
                <small>{thread.source === "hermes" ? "Hermes terminal session" : `Shared ${selectedProfile} chat`}</small>
              </span>
            </button>
            {thread.source === "skavan" && (
              <span className="threadActions">
                <button className="threadRenameButton" type="button" aria-label={`Rename ${thread.title}`} onClick={() => beginRename(thread)}>✎</button>
                <button className="threadDeleteButton" type="button" aria-label={`Delete ${thread.title}`} onClick={() => setDeletingThread(thread)}>×</button>
              </span>
            )}
          </div>
        ))}
        {visibleThreads.length === 0 && (
          <div className="threadSearchEmpty" role="status">
            <strong>No chats found</strong>
            <span>Try a different title or keyword.</span>
          </div>
        )}
      </div>
    );
  }

  const activeThreadSource = threads.find((thread) => thread.id === selectedThreadId)?.source;

  return (
    <main className="workspaceShell">
      <aside className="primaryRail">
        <a className="workspaceBrand" href="/" aria-label="Skav Platform home">
          <img src="/skav-mark.svg" alt="" aria-hidden="true" />
          <span>SKAV PLATFORM</span>
        </a>
        <nav className="primaryNavigation" aria-label="Primary navigation">
          <button type="button" className="active" aria-current="page"><NavIcon kind="user" />Chats</button>
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
        <div className="workspaceSearch">
          <NavIcon kind="search" />
          <label className="srOnly" htmlFor="chat-search">Search chats</label>
          <input
            id="chat-search"
            ref={searchInputRef}
            type="search"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            onFocus={openMobileSearch}
            placeholder="Search chats..."
            autoComplete="off"
          />
          {!searchQuery && <kbd>⌘ K</kbd>}
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
        <div className="workspaceIdentity">
          <strong>{profiles.find((item) => item.key === selectedProfile)?.label ?? "Profile"}</strong>
          <span>Shared Hermes workspace</span>
        </div>
        {profiles.length > 1 && (
          <div className="profileSwitcher" role="group" aria-label="Active profile">
            {profiles.map((profile) => (
              <button key={profile.key} type="button" aria-pressed={selectedProfile === profile.key} onClick={() => selectProfile(profile.key)}>{profile.label}</button>
            ))}
          </div>
        )}
        <button className="newThreadButton" type="button" onClick={createThread}>＋ New chat</button>
        {renderThreadList()}
      </aside>

      <section className="conversationPane" aria-label="Chat with Hermes">
        <header className="conversationHeader">
          <div><h1>{threads.find((thread) => thread.id === selectedThreadId)?.title ?? "General"}</h1><p>{profiles.find((item) => item.key === selectedProfile)?.label ?? "Profile"}</p></div>
          <div className={`status ${hermesStatus}`} aria-label={`Hermes ${hermesStatus}`}>
            <span className="statusDot" aria-hidden="true" />Hermes {hermesStatus}
          </div>
        </header>
        <div className="messages" aria-live="polite" ref={messagesRef} onScroll={updateScrollControls}>
          <div className="dayDivider"><span>Today</span></div>
          {messages.map((message) => {
            const isAssistant = message.role === "assistant";
            const isOwn = !isAssistant && (message.isCurrentUser ?? true);
            const isTerminalUser = !isAssistant && activeThreadSource === "hermes";
            const isRightAligned = isOwn || isTerminalUser;
            const authorName = isAssistant ? "Hermes · Agent" : (message.authorName || (isOwn ? userName : "Group member"));
            return (
              <article className={`message ${isAssistant ? "assistant" : isRightAligned ? "user" : "participant"}`} key={message.id}>
                <span className="messageAvatar">{isAssistant ? "H" : authorName.slice(0, 1).toUpperCase()}</span>
                <div className="messageBody">
                  <div className="messageMeta">{authorName}</div>
                  <div className={`messageContent ${isAssistant ? "markdown" : "plain"}`}>
                    {isAssistant ? (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          a: ({ children, ...props }) => <a {...props} target="_blank" rel="noreferrer noopener">{children}</a>,
                        }}
                      >{message.content}</ReactMarkdown>
                    ) : message.content}
                    {streamingMessageId === message.id && (
                      <span className="streamingIndicator" role="status">
                        <span aria-hidden="true"><i /><i /><i /></span>
                        More response is coming
                      </span>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
          {isSending && !isReceiving && (
            <article className="message assistant pending">
              <span className="messageAvatar">H</span>
              <div className="messageBody"><div className="messageMeta">Hermes · Agent</div><div className="messageContent plain">Processing<span className="pulse">...</span></div></div>
            </article>
          )}
        </div>
        <div className="scrollControls" aria-label="Conversation scroll controls">
          {canScrollUp && <button type="button" onClick={() => scrollMessages("top")} aria-label="Scroll to first message">↑</button>}
          {canScrollDown && <button type="button" onClick={() => scrollMessages("bottom")} aria-label="Scroll to latest message">↓</button>}
        </div>
        <div className="composerArea">
          {error && <p className="error" role="alert">{error}</p>}
          {!selectedProfile && error?.startsWith("No Personal or Work role") && (
            <a className="refreshAccess" href="/refresh-access">Refresh profile access</a>
          )}
          <form className="composer" onSubmit={sendMessage}>
            <span className="composerIcon" aria-hidden="true">⌁</span>
            <label className="srOnly" htmlFor="prompt">Message Hermes</label>
            <textarea
              id="prompt"
              ref={promptRef}
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && event.ctrlKey && !event.nativeEvent.isComposing) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              placeholder={`Message ${threads.find((thread) => thread.id === selectedThreadId)?.title ?? "General"}...`}
              rows={1}
              disabled={!selectedProfile || isSending || isLoadingHistory}
            />
            <button
              type="submit"
              aria-keyshortcuts="Control+Enter"
              title="Send (Ctrl+Enter)"
              disabled={!selectedProfile || !prompt.trim() || isSending || isLoadingHistory}
            >
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
          <div className="contextRow"><span>Access</span><strong>Profile member</strong></div>
        </section>
        <section className="contextSection">
          <span className="contextLabel">Profile memory (shared)</span>
          <div className="contextFeature"><span>▤</span><div><strong>{profiles.find((item) => item.key === selectedProfile)?.label ?? "Profile"}</strong><small>USER.md and MEMORY.md are shared<br />with everyone in this profile.</small></div></div>
        </section>
        <section className="contextSection">
          <span className="contextLabel">Selected agent</span>
          <div className="contextFeature"><span>H</span><div><strong>Hermes</strong><small>{selectedProfile === "work" ? "Work profile" : "Personal profile"}</small></div><i className="onlineMark" /></div>
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
              <div><strong>{profiles.find((item) => item.key === selectedProfile)?.label ?? "Profile"}</strong><span>Shared Hermes workspace</span></div>
              <button type="button" onClick={() => setIsThreadDrawerOpen(false)} aria-label="Close threads">×</button>
            </div>
            {profiles.length > 1 && (
              <div className="profileSwitcher" role="group" aria-label="Active profile">
                {profiles.map((profile) => (
                  <button key={profile.key} type="button" aria-pressed={selectedProfile === profile.key} onClick={() => selectProfile(profile.key)}>{profile.label}</button>
                ))}
              </div>
            )}
            <div className="workspaceSearch drawerSearch">
              <NavIcon kind="search" />
              <label className="srOnly" htmlFor="drawer-chat-search">Search chats</label>
              <input
                id="drawer-chat-search"
                ref={drawerSearchInputRef}
                type="search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search chats..."
                autoComplete="off"
              />
            </div>
            <button className="newThreadButton" type="button" onClick={createThread}>＋ New chat</button>
            {renderThreadList()}
          </aside>
        </>
      )}

      {deletingThread && (
        <div className="confirmDialogBackdrop" role="presentation">
          <section className="confirmDialog uiPanel" role="alertdialog" aria-modal="true" aria-labelledby="delete-chat-title" aria-describedby="delete-chat-description">
            <span className="confirmDialogIcon" aria-hidden="true">×</span>
            <h2 id="delete-chat-title">Delete this chat?</h2>
            <p id="delete-chat-description"><strong>{deletingThread.title}</strong> will be removed from the shared profile chat list. Its stored messages will be retained for recovery.</p>
            <div className="confirmDialogActions">
              <button type="button" onClick={() => setDeletingThread(null)} disabled={isDeletingThread}>Cancel</button>
              <button className="danger" type="button" onClick={deleteThread} disabled={isDeletingThread}>{isDeletingThread ? "Deleting…" : "Delete chat"}</button>
            </div>
          </section>
        </div>
      )}

      <nav className="mobileNavigation" aria-label="Mobile navigation">
        <button type="button" className="active" aria-current="page"><NavIcon kind="user" /><span>Chats</span></button>
        <button type="button" disabled><NavIcon kind="groups" /><span>Profiles</span></button>
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
