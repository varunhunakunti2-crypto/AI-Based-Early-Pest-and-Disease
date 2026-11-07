"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { formatDateTime } from "@/lib/format";
import { useWorkspace } from "@/lib/workspace/store";
import type { ChatMessage } from "@/lib/workspace/types";

import { Icon } from "./ui";

const QUICK_THREAD_TITLE = "Quick assistant";

const QUICK_PROMPTS = [
  { label: "What is on my plant?", prompt: "How can I tell what is affecting my crop?" },
  { label: "Stop it spreading", prompt: "What preventive measures should I take?" },
  { label: "Safe next step", prompt: "What is a safe next step after finding pests?" },
];

export function FloatingChatbot() {
  const { state, newThread, sendChat } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [thinking, setThinking] = useState(false);
  const [pendingMessage, setPendingMessage] = useState<ChatMessage | null>(null);
  const [unread, setUnread] = useState(0);

  const triggerRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<number | null>(null);
  const openRef = useRef(false);

  const thread =
    state.threads.find((item) => item.id === threadId) ??
    state.threads.find((item) => item.title === QUICK_THREAD_TITLE) ??
    null;
  const messages = thread?.messages ?? [];

  useEffect(() => {
    openRef.current = open;
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => inputRef.current?.focus(), 80);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      triggerRef.current?.focus();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [open, messages.length, pendingMessage, thinking]);

  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 96)}px`;
  }, [text]);

  useEffect(
    () => () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    },
    [],
  );

  function toggle() {
    if (open) {
      setOpen(false);
      return;
    }
    setUnread(0);
    setOpen(true);
  }

  function close() {
    setOpen(false);
    window.requestAnimationFrame(() => triggerRef.current?.focus());
  }

  function resetChat() {
    const id = newThread(QUICK_THREAD_TITLE);
    setThreadId(id);
    setText("");
    setPendingMessage(null);
    setThinking(false);
    window.requestAnimationFrame(() => inputRef.current?.focus());
  }

  function submit(event?: React.FormEvent) {
    event?.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || thinking) return;

    let id = thread?.id ?? null;
    if (!id) {
      id = newThread(QUICK_THREAD_TITLE);
      setThreadId(id);
    }

    setText("");
    setPendingMessage({
      id: `local-${crypto.randomUUID()}`,
      role: "user",
      text: trimmed,
      at: new Date().toISOString(),
    });
    setThinking(true);

    if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      sendChat(id, trimmed);
      setPendingMessage(null);
      setThinking(false);
      if (!openRef.current) setUnread((value) => value + 1);
    }, 600);
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className={open ? "ws-chat-fab ws-chat-fab-open" : "ws-chat-fab"}
        aria-label={open ? "Close crop assistant" : "Open crop assistant"}
        aria-expanded={open}
        aria-controls="ws-chat-widget"
        onClick={toggle}
      >
        <span className="ws-chat-fab-icon">
          <Icon name={open ? "close" : "assistant"} size={22} />
        </span>
        <span className="ws-chat-fab-label">{open ? "Close" : "Ask AI"}</span>
        {!open && unread > 0 ? (
          <span className="ws-chat-fab-badge" aria-label={`${unread} new replies`}>
            {unread}
          </span>
        ) : null}
      </button>

      {open ? (
        <section
          id="ws-chat-widget"
          className="ws-chat-widget"
          role="dialog"
          aria-modal="false"
          aria-labelledby="ws-chat-widget-title"
        >
          <header className="ws-chat-widget-head">
            <span className="ws-chat-widget-avatar" aria-hidden="true">
              <Icon name="assistant" size={21} />
            </span>
            <div className="ws-chat-widget-title">
              <h2 id="ws-chat-widget-title">Crop assistant</h2>
              <p>
                <span className="ws-chat-widget-status" aria-hidden="true" />
                Online · guardrailed demo
              </p>
            </div>
            <div className="ws-chat-widget-actions">
              <button
                type="button"
                className="ws-chat-widget-action"
                aria-label="Start a new quick conversation"
                title="New conversation"
                onClick={resetChat}
              >
                <Icon name="plus" size={17} />
              </button>
              <button
                type="button"
                className="ws-chat-widget-action"
                aria-label="Close crop assistant"
                title="Close"
                onClick={close}
              >
                <Icon name="close" size={17} />
              </button>
            </div>
          </header>

          <div
            className="ws-chat-widget-body"
            role="log"
            aria-live="polite"
            aria-relevant="additions"
          >
            {messages.length === 0 && !pendingMessage ? (
              <div className="ws-chat-widget-welcome">
                <span className="ws-chat-widget-welcome-icon" aria-hidden="true">
                  <Icon name="leaf" size={24} />
                </span>
                <h3>What can I help you check?</h3>
                <p>
                  Ask about a symptom, a pest or what to do next. I use your farm
                  context, but I never confirm a diagnosis or recommend a product
                  dose.
                </p>
                <div className="ws-chat-widget-prompts">
                  {QUICK_PROMPTS.map((prompt) => (
                    <button
                      key={prompt.label}
                      type="button"
                      onClick={() => {
                        setText(prompt.prompt);
                        inputRef.current?.focus();
                      }}
                    >
                      {prompt.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((message) => (
                  <WidgetMessage key={message.id} message={message} />
                ))}
                {pendingMessage ? <WidgetMessage message={pendingMessage} pending /> : null}
              </>
            )}

            {thinking ? (
              <div className="ws-chat-widget-message" aria-label="Assistant is typing">
                <span className="ws-chat-widget-message-avatar" aria-hidden="true">
                  <Icon name="assistant" size={15} />
                </span>
                <span className="ws-chat-widget-typing" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                </span>
              </div>
            ) : null}

            <div ref={endRef} />
          </div>

          <form className="ws-chat-widget-composer" onSubmit={submit}>
            <textarea
              ref={inputRef}
              rows={1}
              value={text}
              onChange={(event) => setText(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submit();
                }
              }}
              placeholder="Ask about a pest, disease or next step…"
              aria-label="Message the crop assistant"
            />
            <button
              type="submit"
              className="ws-chat-widget-send"
              aria-label="Send message"
              disabled={!text.trim() || thinking}
            >
              <Icon name="arrow" size={18} />
            </button>
          </form>

          <p className="ws-chat-widget-foot">
            Demo guidance only — not a diagnosis.{" "}
            <Link href="/assistant" onClick={close}>
              Open full assistant
            </Link>
          </p>
        </section>
      ) : null}
    </>
  );
}

function WidgetMessage({
  message,
  pending = false,
}: {
  message: ChatMessage;
  pending?: boolean;
}) {
  const isUser = message.role === "user";
  return (
    <div
      className={
        isUser
          ? "ws-chat-widget-message ws-chat-widget-message-user"
          : "ws-chat-widget-message"
      }
    >
      <span className="ws-chat-widget-message-avatar" aria-hidden="true">
        <Icon name={isUser ? "user" : "assistant"} size={15} />
      </span>
      <div className="ws-chat-widget-message-content">
        <p className="ws-chat-widget-bubble">{message.text}</p>
        <span className="ws-chat-widget-meta">
          {isUser ? "You" : "Assistant"} · {formatDateTime(message.at)}
          {pending ? " · sending…" : ""}
        </span>
      </div>
    </div>
  );
}
