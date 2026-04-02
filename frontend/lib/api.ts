const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface UploadResponse {
  message: string;
  filename: string;
  file_path: string;
  extracted_text: string;
  chunks: string[];
  chunk_count: number;
}

export interface ChatResponse {
  question: string;
  answer: string;
  sources: string[];
}

export interface TelegramIngestResponse {
  status: string;
  stats: {
    chats: number;
    messages: number;
    chunks: number;
  };
}

export interface TelegramContact {
  user_id: string;
  display_names: string[];
  chat_count: number;
}

export interface TelegramSource {
  chunk_text: string;
  chat_id: string;
  chat_type: "direct" | "group";
  chat_name: string;
  sender_ids: string[];
  primary_speaker_id: string;
  mentions_user_ids: string[];
  timestamp_start: string;
  timestamp_end: string;
  source: string;
  distance?: number;
  final_score?: number;
}

export interface TelegramChatResponse {
  answer: string;
  sources: TelegramSource[];
}

export interface TelegramDraftResponse {
  refined_message: string;
  sources: TelegramSource[];
}

export interface TelegramSendResponse {
  status: string;
  recipient_user_id: string;
  recipient_name: string;
  message_id: number;
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Upload failed." }));
    throw new Error(error.detail ?? "Upload failed.");
  }

  return res.json();
}

export async function sendChatQuery(question: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Query failed." }));
    throw new Error(error.detail ?? "Query failed.");
  }

  return res.json();
}

export async function ingestTelegramChats(): Promise<TelegramIngestResponse> {
  const res = await fetch(`${API_BASE_URL}/telegram/ingest`, {
    method: "POST",
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Telegram ingest failed." }));
    throw new Error(error.detail ?? "Telegram ingest failed.");
  }

  return res.json();
}

export async function getTelegramContacts(): Promise<TelegramContact[]> {
  const res = await fetch(`${API_BASE_URL}/telegram/contacts`);

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Failed to load Telegram contacts." }));
    throw new Error(error.detail ?? "Failed to load Telegram contacts.");
  }

  return res.json();
}

export async function sendTelegramChatQuery(
  query: string,
  topK = 5,
): Promise<TelegramChatResponse> {
  const res = await fetch(`${API_BASE_URL}/telegram/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Telegram query failed." }));
    throw new Error(error.detail ?? "Telegram query failed.");
  }

  return res.json();
}

export async function draftTelegramMessage(
  userId: string,
  draft: string,
  topK = 6,
): Promise<TelegramDraftResponse> {
  const res = await fetch(`${API_BASE_URL}/telegram/draft`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, draft, top_k: topK }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Telegram draft failed." }));
    throw new Error(error.detail ?? "Telegram draft failed.");
  }

  return res.json();
}

export async function sendTelegramMessage(
  userId: string,
  message: string,
): Promise<TelegramSendResponse> {
  const res = await fetch(`${API_BASE_URL}/telegram/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, message }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Telegram send failed." }));
    throw new Error(error.detail ?? "Telegram send failed.");
  }

  return res.json();
}
