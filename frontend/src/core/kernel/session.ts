/* Copyright 2024 Marimo. All rights reserved. */
// session.ts

import { init } from "@paralleldrive/cuid2";
import type { TypedString } from "@/utils/typed";
import { updateQueryParams } from "@/utils/urls";
import { Logger } from "@/utils/Logger";
import { KnownQueryParams } from "../constants";

export type SessionId = TypedString<"SessionId">;

const createId = init({ length: 6 });

export function generateSessionId(): SessionId {
  return `s_${createId()}` as SessionId;
}

export function isSessionId(value: string | null): value is SessionId {
  if (!value) {
    return false;
  }
  return /^s_[\da-z]{6}$/.test(value);
}

// Main session block
const sessionId = (() => {
  const url = new URL(window.location.href);
  const id = url.searchParams.get(KnownQueryParams.sessionId) as SessionId | null;

  // 🔥 DEBUG visibility hooks
  console.warn("🔥 session.ts is active!");
  (window as any).__MARIMO_DEBUG_SESSION = {
    cookie: document.cookie,
    userAgent: navigator.userAgent,
    href: url.toString(),
    query: Object.fromEntries(url.searchParams.entries()),
  };
  document.body.setAttribute("data-session-trace", "loaded");

  // Also use Logger
  Logger.debug("Current cookies:", document.cookie);
  Logger.debug("Navigator info:", navigator.userAgent);
  Logger.debug("Base URI:", document.baseURI);
  Logger.debug("Raw session_id from URL:", id);
  Logger.debug("Full URL:", url.toString());
  Logger.debug("All query params:", Object.fromEntries(url.searchParams.entries()));

  if (isSessionId(id)) {
    Logger.debug("Valid session_id found in URL:", id);
    document.cookie = `marimo_session_id=${id}; path=/; SameSite=Lax`;
    Logger.debug("Set marimo_session_id cookie from URL param:", id);

    updateQueryParams((params) => {
      if (params.has(KnownQueryParams.kiosk)) {
        Logger.debug("Kiosk mode active — preserving session_id in URL.");
        return;
      }
      Logger.debug("Removing session_id from query string.");
      params.delete(KnownQueryParams.sessionId);
    });

    return id;
  }

  Logger.debug("No valid session_id in URL. Generating a new one.");
  const newId = generateSessionId();
  Logger.debug("Generated new session_id:", newId);

  document.cookie = `marimo_session_id=${newId}; path=/; SameSite=Lax`;
  Logger.debug("Set marimo_session_id cookie from generator:", newId);

  return newId;
})();

/**
 * Resume an existing session or start a new one
 */
export function getSessionId(): SessionId {
  return sessionId;
}

