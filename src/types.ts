export type PlayerSummary = {
  id: number;
  name: string;
};

export type LeaderboardUser = {
  id: string;
  username: string;
  avatarUrl?: string | null;
  wins: number;
  losses: number;
  correctAnswers: number;
  winPercentage: number;
  rank?: number | null;
};

export type Leaderboard = {
  top: LeaderboardUser[];
  me?: LeaderboardUser | null;
};

export type AppUser = LeaderboardUser;

export type Seat = {
  id: string;
  username: string;
  user_id?: string | null;
  active: boolean;
  correct: number;
  eliminated_reason?: string | null;
  botAccuracy?: number;
};

export type RoomState = {
  event: string;
  roomId?: string;
  gameMode?: "all" | "current";
  message?: string | null;
  seats: Seat[];
  currentSeatId: string | null;
  currentTarget: PlayerSummary;
  chain: PlayerSummary[];
  usedPlayerIds: number[];
  expiresAt: number;
  finished: boolean;
  winnerSeatId?: string | null;
  youSeatId?: string;
};
