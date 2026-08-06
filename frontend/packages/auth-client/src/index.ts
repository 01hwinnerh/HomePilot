export type MerchantMembership = {
  merchant_id: number;
  merchant_name: string;
  role: "OWNER" | "STAFF";
};

export type AuthUser = {
  id: number;
  email: string;
  is_platform_admin: boolean;
  memberships: MerchantMembership[];
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export type RegisterInput = {
  email: string;
  password: string;
};

export type LoginInput = RegisterInput;

export class AuthApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail);
    this.name = "AuthApiError";
  }
}

type AuthRequestInit = Omit<RequestInit, "headers"> & {
  csrf?: boolean;
  headers?: HeadersInit;
};

/**
 * Shared browser client for HomePilot's authentication endpoints.
 *
 * It deliberately never stores access tokens. The caller owns in-memory state,
 * while browser cookies carry the HttpOnly refresh token.
 */
export class AuthClient {
  private readonly baseUrl: string;

  constructor(baseUrl = "") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  register(input: RegisterInput): Promise<AuthResponse> {
    return this.request<AuthResponse>("/register", {
      body: JSON.stringify(input),
      method: "POST",
    });
  }

  login(input: LoginInput): Promise<AuthResponse> {
    return this.request<AuthResponse>("/login", {
      body: JSON.stringify(input),
      method: "POST",
    });
  }

  refresh(): Promise<AuthResponse> {
    return this.request<AuthResponse>("/refresh", { csrf: true, method: "POST" });
  }

  async logout(): Promise<void> {
    await this.request<void>("/logout", { csrf: true, method: "POST" });
  }

  me(accessToken: string): Promise<AuthUser> {
    return this.request<AuthUser>("/me", {
      headers: { Authorization: `Bearer ${accessToken}` },
      method: "GET",
    });
  }

  private async request<T>(path: string, init: AuthRequestInit): Promise<T> {
    const { csrf = false, headers: requestHeaders, ...requestInit } = init;
    const headers = new Headers(requestHeaders);
    headers.set("Content-Type", "application/json");

    if (csrf) {
      headers.set("X-CSRF-Token", readCookie("csrf_token"));
    }

    const response = await fetch(`${this.baseUrl}/api/v1/auth${path}`, {
      ...requestInit,
      credentials: "include",
      headers,
    });

    if (!response.ok) {
      throw new AuthApiError(response.status, await responseDetail(response));
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  }
}

function readCookie(name: string): string {
  if (typeof document === "undefined") {
    return "";
  }

  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie.split("; ").find((entry) => entry.startsWith(prefix));
  return cookie === undefined ? "" : decodeURIComponent(cookie.slice(prefix.length));
}

async function responseDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body) {
      const detail = body.detail;
      if (typeof detail === "string") {
        return detail;
      }
    }
  } catch {
    // Authentication failures may come from a proxy with a non-JSON body.
  }

  return "Authentication request failed";
}
