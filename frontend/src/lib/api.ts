export type Envelope<T> = {
  code: number;
  message: string;
  data: T;
};

export class ApiError extends Error {
  status: number;
  code: number;

  constructor(message: string, status: number, code: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

const TOKEN_KEY = "tl.token";

export const tokenStore = {
  get(): string {
    try {
      return localStorage.getItem(TOKEN_KEY) ?? "";
    } catch {
      return "";
    }
  },
  set(token: string) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      // 忽略写入失败，本次会话仍可用内存中的 state
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      // 忽略
    }
  },
};

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  raw?: FormData;
  signal?: AbortSignal;
};

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (options.raw) {
    body = options.raw;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const response = await fetch(`/api${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
    signal: options.signal,
  });

  let payload: Envelope<T> | null = null;
  try {
    payload = (await response.json()) as Envelope<T>;
  } catch {
    payload = null;
  }

  if (!response.ok || !payload || payload.code !== 0) {
    if (response.status === 401) tokenStore.clear();
    const message = payload?.message || `请求失败（HTTP ${response.status}）`;
    throw new ApiError(message, response.status, payload?.code ?? response.status);
  }

  return payload.data;
}

export type MenuItem = {
  id: number;
  name: string;
  path: string;
  icon: string;
  permission_code: string;
  allowed: boolean;
};

export type CurrentUser = {
  id: number;
  username: string;
  real_name: string;
  department_id: number | null;
  department_name: string;
  roles: string[];
  data_scope: string;
};

export type Me = {
  user: CurrentUser;
  menus: MenuItem[];
  permissions: string[];
};

export type LoginResult = {
  token: string;
  expires_in: number;
  user: CurrentUser;
  menus: MenuItem[];
};

export const api = {
  login(username: string, password: string) {
    return request<LoginResult>("/auth/login", {
      method: "POST",
      body: { username, password },
    });
  },
  me() {
    return request<Me>("/auth/me");
  },
  logout() {
    return request<{ logged_out: boolean }>("/auth/logout", { method: "POST" });
  },
};

const LANDING_ORDER = [
  "/dashboard",
  "/matching",
  "/job-profiles",
  "/talent-profiles",
  "/exams",
  "/resumes",
  "/system",
  "/training",
];

export function landingPath(me: Me): string {
  const allowedMenus = me.menus.filter((menu) => menu.allowed && menu.path);
  const allowed = new Set(allowedMenus.map((menu) => menu.path));
  return LANDING_ORDER.find((path) => allowed.has(path)) ?? allowedMenus[0]?.path ?? "/403";
}
