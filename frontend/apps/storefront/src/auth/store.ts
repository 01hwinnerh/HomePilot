import { create } from "zustand";

import { AuthClient } from "@homepilot/auth-client";
import type { AuthResponse, AuthUser } from "@homepilot/auth-client";

export type AuthRestoreClient = Pick<AuthClient, "refresh">;

export type AuthState = {
  status: "loading" | "anonymous" | "authenticated";
  accessToken: string | null;
  user: AuthUser | null;
  restoreSession: () => Promise<void>;
  acceptAuth: (response: AuthResponse) => void;
  clear: () => void;
};

export function createAuthStore(authClient: AuthRestoreClient) {
  return create<AuthState>((set) => {
    let restoreInFlight: Promise<void> | null = null;

    const setAuthState = (response: AuthResponse) => {
      set({
        status: "authenticated",
        accessToken: response.access_token,
        user: response.user,
      });
    };

    const setAnonymousState = () => {
      set({ status: "anonymous", accessToken: null, user: null });
    };

    const restoreSession = () => {
      if (restoreInFlight !== null) {
        return restoreInFlight;
      }

      const currentPromise = (async () => {
        try {
          const response = await authClient.refresh();
          setAuthState(response);
        } catch {
          setAnonymousState();
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
      status: "loading",
      accessToken: null,
      user: null,
      restoreSession,
      acceptAuth: setAuthState,
      clear: setAnonymousState,
    };
  });
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const storefrontAuthClient = new AuthClient(apiBaseUrl);
export const storefrontAuthStore = createAuthStore(storefrontAuthClient);
