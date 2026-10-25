// Talks to the Orion API. The access token lives in memory only; the refresh token is an
// httpOnly cookie set by the API (path /auth), sent with credentials: "include".

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type User = { id: string; email: string; name?: string | null };

export type Question = {
  id: string;
  prompt: string;
  type: "choice" | "number" | "text" | "file" | "size_table";
  choices: string[];
  required: boolean;
  hint?: string | null;
  section: Section;
  allow_other?: boolean;   // "Other" chip with the customer's own text
  multiple?: boolean;      // several options may be picked
};

export type Section = "design" | "quantity" | "quality";

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
  | { step: string; kind: "choice"; prompt: string; options: { id: string; name: string }[]; error?: string | null }
  | {
      step: string; kind: "form"; prompt: string; questions: Question[];
      values: Record<string, unknown>; errors: Record<string, string>;
    }
  | { step: string; kind: "confirm"; prompt: string; pre_receipt: string; error?: string | null };

export type OrderView = {
  order_id: string;
  stage: string;
  status: { en: string; ar: string };
  waiting_on: "customer" | "manufacturer" | null;
  prompt: Prompt | null;
  messages: { role: "customer" | "orion"; content: string }[];
  pre_receipt: string | null;
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
