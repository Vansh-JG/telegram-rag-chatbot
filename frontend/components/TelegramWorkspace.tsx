"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  draftTelegramMessage,
  getTelegramContacts,
  ingestTelegramChats,
  sendTelegramChatQuery,
  sendTelegramMessage,
  type TelegramContact,
  type TelegramSource,
} from "@/lib/api";

interface TelegramMessage {
  role: "user" | "assistant";
  content: string;
  sources?: TelegramSource[];
}

function formatContactName(contact: TelegramContact) {
  return contact.display_names[0] ?? contact.user_id;
}

function formatChatLabel(source: TelegramSource) {
  return source.chat_type === "direct"
    ? `Direct chat with ${source.chat_name}`
    : `Group: ${source.chat_name}`;
}

export default function TelegramWorkspace() {
  const [contacts, setContacts] = useState<TelegramContact[]>([]);
  const [contactsLoading, setContactsLoading] = useState(true);
  const [contactsError, setContactsError] = useState<string | null>(null);
  const [selectedContactId, setSelectedContactId] = useState("");
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestMessage, setIngestMessage] = useState<string | null>(null);

  const [messages, setMessages] = useState<TelegramMessage[]>([]);
  const [query, setQuery] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  const [draftInput, setDraftInput] = useState("");
  const [draftLoading, setDraftLoading] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [refinedDraft, setRefinedDraft] = useState("");
  const [draftSources, setDraftSources] = useState<TelegramSource[]>([]);
  const [sendLoading, setSendLoading] = useState(false);
  const [sendStatus, setSendStatus] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void loadContacts();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatLoading]);

  async function loadContacts() {
    setContactsLoading(true);
    setContactsError(null);

    try {
      const nextContacts = await getTelegramContacts();
      setContacts(nextContacts);
      setSelectedContactId((currentSelection) => {
        if (currentSelection && nextContacts.some((contact) => contact.user_id === currentSelection)) {
          return currentSelection;
        }
        return nextContacts[0]?.user_id ?? "";
      });
    } catch (err) {
      setContactsError(
        err instanceof Error ? err.message : "Failed to load Telegram contacts.",
      );
    } finally {
      setContactsLoading(false);
    }
  }

  async function handleIngest() {
    setIngestLoading(true);
    setIngestMessage(null);
    setContactsError(null);

    try {
      const response = await ingestTelegramChats();
      const { chats, messages, chunks } = response.stats;
      setIngestMessage(
        `Telegram sync complete: ${chats} chats, ${messages} messages, ${chunks} chunks.`,
      );
      await loadContacts();
    } catch (err) {
      setIngestMessage(err instanceof Error ? err.message : "Telegram ingest failed.");
    } finally {
      setIngestLoading(false);
    }
  }

  async function handleChatSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery || chatLoading) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmedQuery }]);
    setQuery("");
    setChatLoading(true);

    try {
      const response = await sendTelegramChatQuery(trimmedQuery);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.answer, sources: response.sources },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: err instanceof Error ? err.message : "Telegram query failed.",
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  async function handleRefineDraft(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedContactId || !draftInput.trim() || draftLoading) return;

    setDraftLoading(true);
    setDraftError(null);
    setSendStatus(null);

    try {
      const response = await draftTelegramMessage(selectedContactId, draftInput);
      setRefinedDraft(response.refined_message);
      setDraftSources(response.sources);
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : "Telegram draft failed.");
    } finally {
      setDraftLoading(false);
    }
  }

  async function handleSendDraft() {
    if (!selectedContactId || !refinedDraft.trim() || sendLoading) return;

    setSendLoading(true);
    setDraftError(null);
    setSendStatus(null);

    try {
      const response = await sendTelegramMessage(selectedContactId, refinedDraft);
      setSendStatus(`Sent to ${response.recipient_name}.`);
      setDraftInput("");
      setRefinedDraft("");
      setDraftSources([]);
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : "Telegram send failed.");
    } finally {
      setSendLoading(false);
    }
  }

  const selectedContact =
    contacts.find((contact) => contact.user_id === selectedContactId) ?? null;

  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-col gap-4 rounded-2xl border border-sky-200 bg-sky-50/80 p-5 dark:border-sky-900 dark:bg-sky-950/40">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Telegram RAG
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Sync your Telegram history, inspect contacts, ask grounded questions, and
              draft context-aware replies before sending them.
            </p>
          </div>
          <button
            type="button"
            onClick={handleIngest}
            disabled={ingestLoading}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {ingestLoading ? "Syncing Telegram..." : "Sync Telegram"}
          </button>
        </div>

        {ingestMessage && (
          <p className="text-sm text-slate-700 dark:text-slate-200">{ingestMessage}</p>
        )}

        <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)_minmax(0,1fr)]">
          <div className="rounded-xl border border-sky-100 bg-white/80 p-4 dark:border-sky-900 dark:bg-slate-900/80">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                Contacts
              </h3>
              <button
                type="button"
                onClick={() => void loadContacts()}
                disabled={contactsLoading}
                className="text-xs font-medium text-sky-700 hover:text-sky-800 disabled:opacity-50 dark:text-sky-300"
              >
                Refresh
              </button>
            </div>

            {contactsLoading && (
              <p className="text-sm text-slate-500 dark:text-slate-400">Loading contacts...</p>
            )}

            {contactsError && (
              <p className="text-sm text-rose-600 dark:text-rose-400">{contactsError}</p>
            )}

            {!contactsLoading && !contactsError && contacts.length === 0 && (
              <p className="text-sm text-slate-500 dark:text-slate-400">
                No Telegram contacts indexed yet. Run a sync to populate this list.
              </p>
            )}

            {!contactsLoading && !contactsError && contacts.length > 0 && (
              <div className="flex max-h-[640px] flex-col gap-2 overflow-y-auto">
                {contacts.map((contact) => {
                  const isSelected = contact.user_id === selectedContactId;

                  return (
                    <button
                      key={contact.user_id}
                      type="button"
                      onClick={() => {
                        setSelectedContactId(contact.user_id);
                        setSendStatus(null);
                        setDraftError(null);
                      }}
                      className={`rounded-lg border p-3 text-left transition ${
                        isSelected
                          ? "border-sky-500 bg-sky-50 shadow-sm dark:border-sky-400 dark:bg-sky-950/40"
                          : "border-slate-200 bg-slate-50 hover:border-sky-300 hover:bg-sky-50/60 dark:border-slate-700 dark:bg-slate-800"
                      }`}
                    >
                      <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                        {formatContactName(contact)}
                      </p>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {contact.chat_count} shared chat{contact.chat_count === 1 ? "" : "s"}
                      </p>
                      {contact.display_names.length > 1 && (
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          Also seen as: {contact.display_names.slice(1).join(", ")}
                        </p>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="flex flex-col gap-4 rounded-xl border border-sky-100 bg-white/80 p-4 dark:border-sky-900 dark:bg-slate-900/80">
            <div className="flex flex-col gap-1">
              <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                Conversation QA
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Ask questions like “What did Inaara say?” or “What did Chaitanya mention
                about the trip?”
              </p>
            </div>

            <div className="flex min-h-[320px] max-h-[520px] flex-col gap-4 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800">
              {messages.length === 0 && (
                <p className="mt-10 text-center text-sm text-slate-400 dark:text-slate-500">
                  Ask about a person, and the backend will scope retrieval to direct and
                  shared-group context.
                </p>
              )}

              {messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`flex flex-col gap-2 ${
                    message.role === "user" ? "items-end" : "items-start"
                  }`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                      message.role === "user"
                        ? "bg-sky-600 text-white"
                        : "border border-slate-200 bg-white text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                    }`}
                  >
                    {message.role === "assistant" ? (
                      <ReactMarkdown
                        components={{
                          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                          ul: ({ children }) => (
                            <ul className="mb-2 list-disc space-y-1 pl-4">{children}</ul>
                          ),
                          ol: ({ children }) => (
                            <ol className="mb-2 list-decimal space-y-1 pl-4">{children}</ol>
                          ),
                          li: ({ children }) => <li>{children}</li>,
                          strong: ({ children }) => (
                            <strong className="font-semibold">{children}</strong>
                          ),
                          em: ({ children }) => <em className="italic">{children}</em>,
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    ) : (
                      message.content
                    )}
                  </div>

                  {message.sources && message.sources.length > 0 && (
                    <details className="max-w-[85%] text-xs text-slate-500 dark:text-slate-400">
                      <summary className="cursor-pointer hover:text-slate-700 dark:hover:text-slate-200">
                        {message.sources.length} Telegram source chunk
                        {message.sources.length === 1 ? "" : "s"}
                      </summary>
                      <div className="mt-2 flex flex-col gap-2">
                        {message.sources.map((source, sourceIndex) => (
                          <div
                            key={`${source.chat_id}-${source.timestamp_start}-${sourceIndex}`}
                            className="rounded-lg border border-slate-200 bg-slate-100 p-3 dark:border-slate-700 dark:bg-slate-700/60"
                          >
                            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-300">
                              {formatChatLabel(source)}
                            </p>
                            <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-100">
                              {source.chunk_text}
                            </p>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              ))}

              {chatLoading && (
                <div className="flex items-start">
                  <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
                    Searching Telegram context...
                  </div>
                </div>
              )}

              <div ref={bottomRef} />
            </div>

            <form onSubmit={handleChatSubmit} className="flex flex-col gap-3 md:flex-row">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask a question about a Telegram contact..."
                disabled={chatLoading}
                className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500"
              />
              <button
                type="submit"
                disabled={chatLoading || !query.trim()}
                className="rounded-xl bg-slate-900 px-4 py-3 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-sky-600 dark:hover:bg-sky-500"
              >
                Ask Telegram
              </button>
            </form>
          </div>

          <div className="flex flex-col gap-4 rounded-xl border border-emerald-100 bg-white/80 p-4 dark:border-emerald-900 dark:bg-slate-900/80">
            <div className="flex flex-col gap-1">
              <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                Compose Message
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Select a contact, write what you want to say, generate a refined draft,
                then confirm before sending.
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800">
              <label
                htmlFor="telegram-recipient"
                className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400"
              >
                Recipient
              </label>
              <select
                id="telegram-recipient"
                value={selectedContactId}
                onChange={(e) => {
                  setSelectedContactId(e.target.value);
                  setSendStatus(null);
                  setDraftError(null);
                }}
                disabled={contactsLoading || contacts.length === 0}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
              >
                {contacts.length === 0 ? (
                  <option value="">No contacts available</option>
                ) : (
                  contacts.map((contact) => (
                    <option key={contact.user_id} value={contact.user_id}>
                      {formatContactName(contact)}
                    </option>
                  ))
                )}
              </select>

              {selectedContact && (
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  Drafting for {formatContactName(selectedContact)} using shared Telegram context.
                </p>
              )}
            </div>

            <form onSubmit={handleRefineDraft} className="flex flex-col gap-3">
              <textarea
                value={draftInput}
                onChange={(e) => setDraftInput(e.target.value)}
                placeholder="Write the rough message you want to send..."
                disabled={draftLoading || sendLoading || !selectedContactId}
                rows={6}
                className="min-h-[160px] rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500"
              />
              <button
                type="submit"
                disabled={!selectedContactId || !draftInput.trim() || draftLoading || sendLoading}
                className="rounded-xl bg-emerald-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {draftLoading ? "Refining draft..." : "Refine Draft"}
              </button>
            </form>

            {draftError && (
              <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300">
                {draftError}
              </p>
            )}

            {sendStatus && (
              <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300">
                {sendStatus}
              </p>
            )}

            <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800">
              <div className="flex items-center justify-between gap-3">
                <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  Refined Preview
                </h4>
                <button
                  type="button"
                  onClick={() => void handleSendDraft()}
                  disabled={!refinedDraft.trim() || sendLoading || draftLoading || !selectedContactId}
                  className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-emerald-600 dark:hover:bg-emerald-500"
                >
                  {sendLoading ? "Sending..." : "Looks Good, Send"}
                </button>
              </div>

              <textarea
                value={refinedDraft}
                onChange={(e) => setRefinedDraft(e.target.value)}
                placeholder="Your refined message preview will appear here."
                disabled={draftLoading || sendLoading}
                rows={8}
                className="min-h-[180px] rounded-xl border border-dashed border-slate-300 bg-white px-4 py-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
              />

              {refinedDraft && (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  You can edit this refined message directly, or change the original draft and regenerate.
                </p>
              )}

              {draftSources.length > 0 && (
                <details className="text-xs text-slate-500 dark:text-slate-400">
                  <summary className="cursor-pointer hover:text-slate-700 dark:hover:text-slate-200">
                    {draftSources.length} context chunk{draftSources.length === 1 ? "" : "s"} used
                    for refinement
                  </summary>
                  <div className="mt-2 flex flex-col gap-2">
                    {draftSources.map((source, index) => (
                      <div
                        key={`${source.chat_id}-${source.timestamp_start}-draft-${index}`}
                        className="rounded-lg border border-slate-200 bg-slate-100 p-3 dark:border-slate-700 dark:bg-slate-700/60"
                      >
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-300">
                          {formatChatLabel(source)}
                        </p>
                        <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-100">
                          {source.chunk_text}
                        </p>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
