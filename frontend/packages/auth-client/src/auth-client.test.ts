import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthClient } from "./index";

const fetchMock = vi.fn();

describe("AuthClient", () => {
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("sends cookies and the CSRF token when refreshing a session", async () => {
    vi.stubGlobal("fetch", fetchMock.mockResolvedValue(jsonResponse({ access_token: "token" })));
    vi.stubGlobal("document", { cookie: "theme=light; csrf_token=csrf-value" });

    const client = new AuthClient("http://localhost:8000");

    await client.refresh();

    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/auth/refresh");
    expect(request.credentials).toBe("include");
    expect(request.method).toBe("POST");
    expect(new Headers(request.headers).get("X-CSRF-Token")).toBe("csrf-value");
  });

  it("sends cookies and the CSRF token when logging out", async () => {
    vi.stubGlobal("fetch", fetchMock.mockResolvedValue(new Response(null, { status: 204 })));
    vi.stubGlobal("document", { cookie: "csrf_token=csrf-value" });

    const client = new AuthClient("http://localhost:8000");

    await client.logout();

    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/auth/logout");
    expect(request.credentials).toBe("include");
    expect(request.method).toBe("POST");
    expect(new Headers(request.headers).get("X-CSRF-Token")).toBe("csrf-value");
  });
});

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status: 200,
  });
}
