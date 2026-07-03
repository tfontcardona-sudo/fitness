/**
 * Capa de acceso a la API.
 *
 * Un único cliente fetch que adjunta el JWT, parsea JSON y normaliza errores.
 * Cada método mapea a un endpoint real de las Fases 2–4. Los tipos vienen de
 * types.ts (espejo de los schemas Pydantic).
 */

import type {
  BrandConfigOut,
  ChangeRequestOut,
  ClientCreate,
  ClientCreatedOut,
  ClientOut,
  ClientStatus,
  ExerciseOut,
  MeOut,
  PortalLinkOut,
  TokenOut,
} from "../types";

const TOKEN_KEY = "fitness_coach_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  opts: { raw?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`/api${path}`, { method, headers, body: payload });

  if (res.status === 401) {
    clearToken();
    // Señaliza a la app que debe volver al login.
    window.dispatchEvent(new CustomEvent("auth:expired"));
    throw new ApiError(401, "Sesión caducada");
  }

  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) detail = data.detail.map((d: any) => d.msg).join("; ");
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new ApiError(res.status, detail);
  }

  if (opts.raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // --- auth ---
  login: (username: string, password: string) =>
    request<TokenOut>("POST", "/auth/login", { username, password }),
  me: () => request<MeOut>("GET", "/auth/me"),

  // --- clients ---
  listClients: (params: { status?: ClientStatus; q?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set("status", params.status);
    if (params.q) qs.set("q", params.q);
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<ClientOut[]>("GET", `/clients${suffix}`);
  },
  getClient: (id: number) => request<ClientOut>("GET", `/clients/${id}`),
  createClient: (body: ClientCreate) =>
    request<ClientCreatedOut>("POST", "/clients", body),
  updateClient: (id: number, patch: Partial<ClientOut>) =>
    request<ClientOut>("PATCH", `/clients/${id}`, patch),
  portalLink: (id: number) =>
    request<PortalLinkOut>("GET", `/clients/${id}/portal-link`),
  regeneratePortalToken: (id: number) =>
    request<PortalLinkOut>("POST", `/clients/${id}/portal-token/regenerate`),
  exportClientUrl: (id: number) => `/api/clients/${id}/export`,
  listPlans: (clientId: number) =>
    request<{ id: number; month_index: number; version: number; status: string }[]>(
      "GET", `/clients/${clientId}/plans`),
  planDocumentUrl: (planId: number) => `/api/plans/${planId}/document`,
  listClientDocuments: (clientId: number) =>
    request<{ name: string; size_kb: number; uploaded_at: number }[]>(
      "GET", `/clients/${clientId}/documents`),
  uploadClientDocument: (clientId: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ name: string }>("POST", `/clients/${clientId}/documents`, fd);
  },
  clientDocumentUrl: (clientId: number, name: string) =>
    `/api/clients/${clientId}/documents/${encodeURIComponent(name)}`,

  // --- brand ---
  getBrand: () => request<BrandConfigOut>("GET", "/brand"),
  updateBrand: (body: Omit<BrandConfigOut, "id" | "logo_path">) =>
    request<BrandConfigOut>("PUT", "/brand", body),
  uploadLogo: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<BrandConfigOut>("POST", "/brand/logo", fd);
  },

  // --- exercises ---
  listExercises: (params: { q?: string; pattern?: string; muscle?: string; include_archived?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.pattern) qs.set("pattern", params.pattern);
    if (params.muscle) qs.set("muscle", params.muscle);
    if (params.include_archived) qs.set("include_archived", "true");
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<ExerciseOut[]>("GET", `/exercises${suffix}`);
  },
  archiveExercise: (id: number) =>
    request<ExerciseOut>("POST", `/exercises/${id}/archive`),
  restoreExercise: (id: number) =>
    request<ExerciseOut>("POST", `/exercises/${id}/restore`),
  updateExercise: (id: number, patch: Partial<ExerciseOut>) =>
    request<ExerciseOut>("PATCH", `/exercises/${id}`, patch),
};

export type { ChangeRequestOut };
