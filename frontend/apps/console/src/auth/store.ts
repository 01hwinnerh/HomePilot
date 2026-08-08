import { create } from "zustand";

import { AuthClient } from "@homepilot/auth-client";
import type { AuthResponse, AuthUser } from "@homepilot/auth-client";

export type ConsoleAuthRestoreClient = Pick<AuthClient, "refresh" | "me">;

export type ConsoleAuthState = {
  status: "loading" | "anonymous" | "authenticated";
  accessToken: string | null;
  user: AuthUser | null;
  restoreSession: () => Promise<void>;
  acceptAuth: (response: AuthResponse) => void;
  clear: () => void;
};

export function createConsoleAuthStore(authClient: ConsoleAuthRestoreClient) {
  return create<ConsoleAuthState>((set) => {
    let restoreInFlight: Promise<void> | null = null;

    const setAuthenticated = (response: AuthResponse) => {
      set({
        accessToken: response.access_token,
        status: "authenticated",
        user: response.user,
      });
    };

    const setAnonymous = () => {
      set({ accessToken: null, status: "anonymous", user: null });
    };

    const restoreSession = () => {
      if (restoreInFlight !== null) {
        return restoreInFlight;
      }

      const currentPromise = (async () => {
        try {
          const response = await authClient.refresh();
          const user = await authClient.me(response.access_token);
          setAuthenticated({ ...response, user });
        } catch {
          setAnonymous();
        }
      })();
      restoreInFlight = currentPromise;
      void currentPromise.finally(() => {
        if (restoreInFlight === currentPromise) {
          restoreInFlight = null;
        }
      });
      return currentPromise;
    };

    return {
      accessToken: null,
      acceptAuth: setAuthenticated,
      clear: setAnonymous,
      restoreSession,
      status: "loading",
      user: null,
    };
  });
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const consoleAuthClient = new AuthClient(apiBaseUrl);
export const consoleAuthStore = createConsoleAuthStore(consoleAuthClient);
