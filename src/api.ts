import type { AppUser, Leaderboard, PlayerSummary } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export function websocketUrl(path: string): string {
  const base = API_BASE || window.location.origin;
  const url = new URL(path, base.endsWith("/") ? base : `${base}/`);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function bootstrap(userId?: string): Promise<{
  allPlayers: PlayerSummary[];
  currentPlayers: PlayerSummary[];
  leaderboard: Leaderboard;
}> {
  const suffix = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
  return request(`/api/bootstrap${suffix}`);
}

export async function randomStarter(currentOnly = false): Promise<PlayerSummary> {
  return request(`/api/random-starter?currentOnly=${currentOnly ? "true" : "false"}`);
}

export async function validateGuess(
  currentPlayerId: number,
  guess: string,
  usedPlayerIds: number[],
  currentOnly = false
): Promise<{ valid: boolean; reason?: string; player?: PlayerSummary }> {
  return request("/api/validate", {
    method: "POST",
    body: JSON.stringify({ current_player_id: currentPlayerId, guess, used_player_ids: usedPlayerIds, current_only: currentOnly })
  });
}

export async function fetchTeammates(playerId: number, usedIds: number[]): Promise<PlayerSummary[]> {
  const used = usedIds.join(",");
  const payload = await request<{ players: PlayerSummary[] }>(`/api/teammates/${playerId}?used=${used}`);
  return payload.players;
}

export async function fetchBotAnswer(playerId: number, usedIds: number[], currentOnly = false): Promise<PlayerSummary | null> {
  const used = usedIds.join(",");
  const payload = await request<{ player: PlayerSummary | null }>(
    `/api/bot-answer/${playerId}?used=${used}&currentOnly=${currentOnly ? "true" : "false"}`
  );
  return payload.player;
}

export async function updateStats(userId: string, won: boolean, correctAnswers: number) {
  return request<{ user: AppUser; leaderboard: Leaderboard }>("/api/stats", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, won, correct_answers: correctAnswers })
  });
}

export async function loginWithGoogle(credential: string, username?: string): Promise<{ user: AppUser; error?: string }> {
  return request("/api/auth/google", {
    method: "POST",
    body: JSON.stringify({ credential, username })
  });
}

export async function updateUsername(userId: string, username: string): Promise<{ user: AppUser; error?: string }> {
  return request("/api/me/username", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, username })
  });
}
