// Talks to the Orion API. The access token lives in memory only; the refresh token is an
// httpOnly cookie set by the API (path /auth), sent with credentials: "include".

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type User = { id: string; email: string; name?: string | null };

export type Question = {
  id: string;
  prompt: string;
  type: "choice" | "number" | "text" | "file" | "size_table" | "placement";
  choices: string[];
  required: boolean;
  hint?: string | null;
  section: Section;
  allow_other?: boolean;   // "Other" chip with the customer's own text
  multiple?: boolean;      // several options may be picked
  mockup?: string | null;  // placement: which garment drawing
  multiline?: boolean;     // text: a long description (large box)
  prompt_ar?: string | null;
  hint_ar?: string | null;
  choices_ar?: string[];   // Arabic labels, same order as choices (values stay English)
  cost_tiers?: number[];   // relative cost per choice: 1 = $, 2 = $$, 3 = $$$ (0 = none)
};

export type SummaryItem = { id: string; type: string; label: string; value: string; raw: unknown };
export type Summary = {
  lang: "ar" | "en";
  product: string;
  option: string;
  market: string;
  mockup?: string | null;
  quantity: number | null;
  sizes: Record<string, number>;
  sections: { id: Section; items: SummaryItem[] }[];
  extras: SummaryItem[];
  files: { url: string; kind: string }[];
  open_gaps: string[];
};

export type Section = "design" | "quantity" | "quality";

export type UploadedFile = { file_id: string; name: string; content_type: string; size?: number };

/** Upload a logo/artwork file to an order. The API checks type (by content) and size. */
export async function uploadFile(orderId: string, file: File, retried = false): Promise<UploadedFile> {
  const form = new FormData();
  form.append("file", file);
  const r = await fetch(`${API_URL}/orders/${encodeURIComponent(orderId)}/files`, {
    method: "POST", credentials: "include", body: form,
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
  if (r.status === 401 && !retried && (await refreshSession())) return uploadFile(orderId, file, true);
  const data = await r.json().catch(() => null);
  if (!r.ok) throw new ApiError(r.status, typeof data?.detail === "string" ? data.detail : `HTTP ${r.status}`);
  return data as UploadedFile;
}

const fileUrls = new Map<string, Promise<string>>();

/** A private file as an object URL (fetched with the login token; plain <img src> cannot send it). */
export function fileObjectUrl(orderId: string, fileId: string): Promise<string> {
  const key = `${orderId}/${fileId}`;
  if (!fileUrls.has(key)) {
    const load = async (retried: boolean): Promise<string> => {
      const r = await fetch(`${API_URL}/orders/${encodeURIComponent(orderId)}/files/${encodeURIComponent(fileId)}`, {
        credentials: "include", headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      });
      if (r.status === 401 && !retried && (await refreshSession())) return load(true);
      if (!r.ok) throw new ApiError(r.status, "file not available");
      return URL.createObjectURL(await r.blob());
    };
    const p = load(false);
    p.catch(() => fileUrls.delete(key));
    fileUrls.set(key, p);
  }
  return fileUrls.get(key)!;
}

/** "Ask Orion" about one form section. Advice only; nothing is saved. */
export async function askAboutSection(
  orderId: string, section: Section, question: string, answers: Record<string, unknown>, lang: "ar" | "en",
): Promise<string> {
  const r = await api<{ answer: string }>(`/orders/${encodeURIComponent(orderId)}/assist`, {
    method: "POST", body: { section, question, answers, lang },
  });
  return r.answer;
}

export type Prompt =
  | {
      step: string; kind: "choice"; prompt: string; prompt_ar?: string | null;
      options: { id: string; name: string; name_ar?: string | null }[]; error?: string | null;
    }
  | {
      step: string; kind: "form"; prompt: string; prompt_ar?: string | null; questions: Question[];
      values: Record<string, unknown>; errors: Record<string, string>;
    }
  | {
      step: string; kind: "confirm"; prompt: string; prompt_ar?: string | null; pre_receipt: string;
      summary?: Summary | null; error?: string | null;
    }
  // Orders paused by an older API version: a single message to answer in free text
  | { step: string; kind: "chat"; message: string };

export type OrderView = {
  order_id: string;
  stage: string;
  status: { en: string; ar: string };
  waiting_on: "customer" | "manufacturer" | null;
  prompt: Prompt | null;
  messages: { role: "customer" | "orion"; content: string }[];
  pre_receipt: string | null;
  summary?: Summary | null;
  spec: { option?: string; quantity?: number; answers?: Record<string, unknown>; frozen?: boolean } | null;
};

export type OrderRow = {
  id: string; stage: string; option: string | null; quantity: number | null; created_at: string; updated_at: string;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

type TokenResponse = { access_token: string; user: User };

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => null);
  if (!r.ok) throw new ApiError(r.status, data?.detail ?? `HTTP ${r.status}`);
  return data as T;
}

/** Restore the session from the refresh cookie. Returns the user, or null if logged out. */
export async function refreshSession(): Promise<User | null> {
  try {
    const data = await post<TokenResponse>("/auth/refresh", { audience: "customer" });
    accessToken = data.access_token;
    return data.user;
  } catch {
    accessToken = null;
    return null;
  }
}

export async function startEmailLogin(email: string): Promise<void> {
  await post("/auth/email/start", { email, audience: "customer" });
}

export async function verifyEmailLogin(email: string, code: string): Promise<User> {
  const data = await post<TokenResponse>("/auth/email/verify", { email, code, audience: "customer" });
  accessToken = data.access_token;
  return data.user;
}

export async function googleLogin(idToken: string): Promise<User> {
  const data = await post<TokenResponse>("/auth/google", { id_token: idToken });
  accessToken = data.access_token;
  return data.user;
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_URL}/auth/logout`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ audience: "customer" }),
    });
  } finally {
    accessToken = null;
  }
}

/** Authenticated request; refreshes the access token once on 401. */
export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}, retried = false): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, {
    method: init.method ?? "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
  if (r.status === 401 && !retried && (await refreshSession())) return api<T>(path, init, true);
  const data = await r.json().catch(() => null);
  if (!r.ok) throw new ApiError(r.status, typeof data?.detail === "string" ? data.detail : `HTTP ${r.status}`);
  return data as T;
}
