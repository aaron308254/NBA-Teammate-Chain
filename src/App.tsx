import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, FormEvent } from "react";
import { Bot, Crown, LogIn, RadioTower, Search, ShieldX, Trophy, UserRound, Users } from "lucide-react";
import {
  bootstrap,
  fetchBotAnswer,
  loginWithGoogle,
  randomStarter,
  updateStats,
  updateUsername,
  validateGuess
} from "./api";
import type { AppUser, Leaderboard, PlayerSummary, RoomState, Seat } from "./types";

const TURN_SECONDS = 15;
const emptyLeaderboard: Leaderboard = { top: [], me: null };
type SoundName = "tick" | "correct" | "wrong" | "win";
type TurnSnapshot = {
  seatId: string;
  targetId: number;
  expiresAt: number;
};
type SeatBubble = {
  text: string;
  tone: "thinking" | "correct" | "wrong";
};

function normalize(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function makeSeat(username: string, botAccuracy?: number): Seat {
  return {
    id: crypto.randomUUID(),
    username,
    active: true,
    correct: 0,
    botAccuracy
  };
}

function Home({
  user,
  leaderboard,
  onQueue,
  onAi,
  onLogin,
  onUsername
}: {
  user: AppUser | null;
  leaderboard: Leaderboard;
  onQueue: () => void;
  onAi: () => void;
  onLogin: (credential: string) => void;
  onUsername: (value: string) => void;
}) {
  const [username, setUsername] = useState(user?.username ?? "");
  const googleButtonRef = useRef<HTMLDivElement | null>(null);
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId || user || !googleButtonRef.current) return;
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      const google = (window as unknown as { google?: any }).google;
      if (!googleButtonRef.current || !google?.accounts?.id) return;
      google.accounts.id.initialize({
        client_id: clientId,
        callback: (response: { credential: string }) => onLogin(response.credential)
      });
      google.accounts.id.renderButton(googleButtonRef.current, {
        theme: "filled_black",
        size: "large",
        shape: "pill"
      });
    };
    document.body.appendChild(script);
    return () => {
      script.remove();
    };
  }, [clientId, onLogin, user]);

  return (
    <main className="home-shell">
      <div className="court-aurora" />
      <header className="topbar">
        <h1 className="home-title">TEAMMATES : NBA</h1>
        <div className="auth-panel">
          {user ? (
            <>
              <div className="avatar">{user.avatarUrl ? <img src={user.avatarUrl} alt="" /> : <UserRound size={18} />}</div>
              <input
                aria-label="Username"
                value={username}
                maxLength={24}
                onChange={(event) => setUsername(event.target.value)}
                onBlur={() => username.trim() && username !== user.username && onUsername(username)}
              />
              <span className="wins-pill">{user.wins} wins</span>
            </>
          ) : clientId ? (
            <div ref={googleButtonRef} />
          ) : (
            <button className="ghost-button" type="button" disabled>
              <LogIn size={17} />
              Add Google client ID
            </button>
          )}
        </div>
      </header>

      <section className="home-grid">
        <div className="home-actions">
          <div className="action-row">
            <button className="primary-action" type="button" onClick={onQueue}>
              <Users size={20} />
              Queue against other players
            </button>
            <button className="secondary-action" type="button" onClick={onAi}>
              <Bot size={20} />
              Play against AI
            </button>
          </div>
        </div>

        <LeaderboardPanel leaderboard={leaderboard} user={user} />

        <section className="how-card">
          <h2>How it works</h2>
          <p>
            A top-75 all-time scorer starts the chain. On your turn, name one regular-season NBA teammate before the
            clock hits zero. Repeats are blocked, wrong links eliminate you, and the last active player wins.
          </p>
        </section>
      </section>
    </main>
  );
}

function LeaderboardPanel({ leaderboard, user }: { leaderboard: Leaderboard; user: AppUser | null }) {
  return (
    <aside className="leaderboard">
      <div className="panel-title">
        <Trophy size={20} />
        <h2>Leaderboard</h2>
      </div>
      <div className="leaderboard-list">
        {leaderboard.top.length ? (
          leaderboard.top.map((entry, index) => (
            <div className="leader-row" key={entry.id}>
              <span className="rank">{entry.rank ?? index + 1}</span>
              <span className="leader-name">{entry.username}</span>
              <span className="leader-wins">{entry.wins}</span>
            </div>
          ))
        ) : (
          <div className="empty-board">No saved wins yet.</div>
        )}
      </div>
      {leaderboard.me ? (
        <div className="my-rank">
          <span>#{leaderboard.me.rank}</span>
          <strong>{leaderboard.me.username}</strong>
          <span>{leaderboard.me.wins} wins</span>
        </div>
      ) : user ? (
        <div className="my-rank">
          <span>Stats</span>
          <strong>{user.username}</strong>
          <span>{user.winPercentage}% win rate</span>
        </div>
      ) : null}
    </aside>
  );
}

function QueueScreen({
  user,
  onCancel,
  onStarted
}: {
  user: AppUser | null;
  onCancel: () => void;
  onStarted: (state: RoomState, socket: WebSocket) => void;
}) {
  const [queued, setQueued] = useState(1);
  const [needed, setNeeded] = useState(4);
  const handedOffRef = useRef(false);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const username = encodeURIComponent(user?.username ?? "Player");
    const userId = encodeURIComponent(user?.id ?? "");
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/queue?username=${username}&userId=${userId}`);
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as RoomState & { queued?: number; needed?: number };
      if (payload.event === "queued") {
        setQueued(payload.queued ?? 1);
        setNeeded(payload.needed ?? 4);
      }
      if (payload.currentTarget) {
        handedOffRef.current = true;
        onStarted(payload, socket);
      }
    };
    return () => {
      if (!handedOffRef.current) socket.close();
    };
  }, [onStarted, user?.id, user?.username]);

  return (
    <main className="queue-screen">
      <div className="queue-orbit">
        <RadioTower size={34} />
        <h1>Finding four players</h1>
        <p>
          {queued} of {needed} seats filled
        </p>
        <div
          className="queue-meter"
          style={{ "--queue": `${Math.min(100, (queued / needed) * 100)}%` } as CSSProperties & Record<"--queue", string>}
        />
        <button className="ghost-button" type="button" onClick={onCancel}>
          Leave queue
        </button>
      </div>
    </main>
  );
}

function Game({
  initialState,
  allPlayers,
  user,
  mode,
  onlineSocket,
  playSound,
  onExit,
  onStats
}: {
  initialState: RoomState;
  allPlayers: PlayerSummary[];
  user: AppUser | null;
  mode: "ai" | "online";
  onlineSocket: WebSocket | null;
  playSound: (name: SoundName) => void;
  onExit: () => void;
  onStats: (user: AppUser, leaderboard: Leaderboard) => void;
}) {
  const [state, setState] = useState<RoomState>(initialState);
  const [guess, setGuess] = useState("");
  const [invalid, setInvalid] = useState(false);
  const [message, setMessage] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [seatBubbles, setSeatBubbles] = useState<Record<string, SeatBubble>>({});
  const [now, setNow] = useState(Date.now() / 1000);
  const [humanCorrect, setHumanCorrect] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);
  const submittedStatsRef = useRef(false);
  const lastTickRef = useRef<number | null>(null);
  const stateRef = useRef(state);
  const gameOverSoundRef = useRef(false);

  const youSeatId = state.youSeatId ?? state.seats.find((seat) => !seat.botAccuracy)?.id ?? state.seats[0]?.id;
  const currentSeat = state.seats.find((seat) => seat.id === state.currentSeatId);
  const isYourTurn = currentSeat?.id === youSeatId && !state.finished;
  const secondsLeft = Math.max(0, Math.ceil(state.expiresAt - now));

  const suggestions = useMemo(() => {
    const needle = normalize(guess);
    if (needle.length < 2) return [];
    return allPlayers
      .filter((player) => {
        const parts = player.name.split(" ");
        const first = normalize(parts[0] ?? "");
        const last = normalize(parts[parts.length - 1] ?? "");
        const full = normalize(player.name);
        return first.startsWith(needle) || last.startsWith(needle) || full.includes(needle);
      })
      .slice(0, 7);
  }, [allPlayers, guess]);

  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now() / 1000), 200);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    if (mode !== "online" || !onlineSocket) return;
    const socket = onlineSocket;
    socketRef.current = onlineSocket;
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as RoomState & { player?: PlayerSummary };
      if (payload.event === "repeat") {
        flashInvalid("No repeats in the chain.");
        if (stateRef.current.currentSeatId) {
          markBubble(stateRef.current.currentSeatId, "Repeat", "wrong");
        }
        return;
      }
      if (payload.currentTarget) {
        stateRef.current = payload;
        setState(payload);
        setGuess("");
        setShowSuggestions(false);
      }
    };
    return () => socket.close();
  }, [mode, onlineSocket]);

  useEffect(() => {
    if (mode !== "ai" || state.finished) return;
    const botSeat = currentSeat?.botAccuracy ? currentSeat : null;
    if (!botSeat) return;
    const turn: TurnSnapshot = {
      seatId: botSeat.id,
      targetId: state.currentTarget.id,
      expiresAt: state.expiresAt
    };
    const timeout = window.setTimeout(async () => {
      const shouldHit = Math.random() < (botSeat.botAccuracy ?? 0);
      if (shouldHit) {
        const pick = await fetchBotAnswer(state.currentTarget.id, state.usedPlayerIds);
        if (!isSameTurn(turn)) return;
        if (pick) {
          await applyLocalGuess(pick.name, true, turn);
          return;
        }
      }
      await applyLocalGuess("Aaron James", true, turn);
    }, 2000 + Math.random() * 3000);
    return () => window.clearTimeout(timeout);
  }, [currentSeat?.id, mode, state.currentTarget.id, state.expiresAt, state.finished]);

  useEffect(() => {
    if (mode !== "ai" || state.finished || secondsLeft > 0 || !currentSeat) return;
    eliminateLocal(currentSeat.id, "time");
  }, [secondsLeft, mode, state.finished, currentSeat?.id]);

  useEffect(() => {
    if (!state.finished || submittedStatsRef.current || !user) return;
    const won = state.winnerSeatId === youSeatId;
    submittedStatsRef.current = true;
    updateStats(user.id, won, humanCorrect).then((payload) => onStats(payload.user, payload.leaderboard));
  }, [humanCorrect, onStats, state.finished, state.winnerSeatId, user, youSeatId]);

  useEffect(() => {
    if (state.finished || secondsLeft <= 0 || lastTickRef.current === secondsLeft) return;
    lastTickRef.current = secondsLeft;
    playSound("tick");
  }, [playSound, secondsLeft, state.finished]);

  useEffect(() => {
    if (!state.finished || gameOverSoundRef.current) return;
    gameOverSoundRef.current = true;
    playSound("win");
  }, [playSound, state.finished]);

  function isSameTurn(turn: TurnSnapshot) {
    const latest = stateRef.current;
    return (
      !latest.finished &&
      latest.currentSeatId === turn.seatId &&
      latest.currentTarget.id === turn.targetId &&
      latest.expiresAt === turn.expiresAt
    );
  }

  function flashInvalid(nextMessage: string) {
    playSound("wrong");
    setInvalid(true);
    setMessage(nextMessage);
    window.setTimeout(() => setInvalid(false), 650);
  }

  function markBubble(seatId: string, text: string, tone: SeatBubble["tone"]) {
    setSeatBubbles((previous) => ({
      ...previous,
      [seatId]: { text, tone }
    }));
  }

  function nextActiveIndex(seats: Seat[], currentIndex: number) {
    for (let offset = 1; offset <= seats.length; offset += 1) {
      const index = (currentIndex + offset) % seats.length;
      if (seats[index].active) return index;
    }
    return currentIndex;
  }

  function updateTurn(nextState: RoomState, seats: Seat[], fromSeatId: string) {
    const active = seats.filter((seat) => seat.active);
    if (active.length <= 1) {
      nextState.finished = true;
      nextState.winnerSeatId = active[0]?.id ?? null;
      nextState.currentSeatId = null;
      nextState.expiresAt = Date.now() / 1000;
      return nextState;
    }
    const currentIndex = seats.findIndex((seat) => seat.id === fromSeatId);
    const nextIndex = nextActiveIndex(seats, currentIndex);
    nextState.currentSeatId = seats[nextIndex].id;
    nextState.expiresAt = Date.now() / 1000 + TURN_SECONDS;
    return nextState;
  }

  function eliminateLocal(seatId: string, reason: string, turn?: TurnSnapshot) {
    if (turn && !isSameTurn(turn)) return;
    playSound("wrong");
    if (!seatBubbles[seatId]) {
      markBubble(seatId, reason === "time" ? "Time" : reason === "repeat" ? "Repeat" : "Wrong", "wrong");
    }
    setState((previous) => {
      if (turn && (previous.currentSeatId !== turn.seatId || previous.currentTarget.id !== turn.targetId || previous.expiresAt !== turn.expiresAt)) {
        return previous;
      }
      const seats = previous.seats.map((seat) =>
        seat.id === seatId ? { ...seat, active: false, eliminated_reason: reason } : seat
      );
      const nextState = updateTurn({ ...previous, seats }, seats, seatId);
      stateRef.current = nextState;
      return nextState;
    });
    setGuess("");
    setShowSuggestions(false);
  }

  async function applyLocalGuess(value: string, fromBot = false, turn?: TurnSnapshot) {
    const latest = stateRef.current;
    if (turn && !isSameTurn(turn)) return;
    const seat = latest.seats.find((item) => item.id === latest.currentSeatId);
    if (!seat) return;
    markBubble(seat.id, value, "thinking");
    const localMatch = allPlayers.find((player) => normalize(player.name) === normalize(value));
    if (localMatch && latest.usedPlayerIds.includes(localMatch.id)) {
      if (!fromBot) flashInvalid("That player is already in the chain.");
      markBubble(seat.id, value, "wrong");
      return;
    }
    const result = await validateGuess(latest.currentTarget.id, value, latest.usedPlayerIds);
    if (turn && !isSameTurn(turn)) return;
    if (!result.valid || !result.player) {
      if (result.reason === "repeat") {
        if (!fromBot) flashInvalid("No repeats in the chain.");
        markBubble(seat.id, value, "wrong");
        return;
      }
      markBubble(seat.id, value, "wrong");
      eliminateLocal(seat.id, result.reason ?? "wrong", turn);
      setMessage(`${seat.username} missed the link.`);
      return;
    }
    const player = result.player;
    setState((previous) => {
      if (turn && (previous.currentSeatId !== turn.seatId || previous.currentTarget.id !== turn.targetId || previous.expiresAt !== turn.expiresAt)) {
        return previous;
      }
      const seats = previous.seats.map((item) => (item.id === seat.id ? { ...item, correct: item.correct + 1 } : item));
      const nextState: RoomState = {
        ...previous,
        seats,
        chain: [...previous.chain, previous.currentTarget],
        currentTarget: player,
        usedPlayerIds: [...previous.usedPlayerIds, player.id]
      };
      const updatedState = updateTurn(nextState, seats, seat.id);
      stateRef.current = updatedState;
      return updatedState;
    });
    if (!fromBot && seat.id === youSeatId) {
      setHumanCorrect((count) => count + 1);
    }
    markBubble(seat.id, player.name, "correct");
    playSound("correct");
    setGuess("");
    setShowSuggestions(false);
    setMessage(`${player.name} is live.`);
  }

  async function submitGuess(event: FormEvent) {
    event.preventDefault();
    await submitCurrentGuess();
  }

  async function submitCurrentGuess() {
    const value = guess.trim();
    if (!value || !isYourTurn || !currentSeat) return;
    setShowSuggestions(false);
    if (mode === "online" && socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ event: "guess", guess: value }));
      return;
    }
    await applyLocalGuess(value, false, {
      seatId: currentSeat.id,
      targetId: state.currentTarget.id,
      expiresAt: state.expiresAt
    });
  }

  const winner = state.seats.find((seat) => seat.id === state.winnerSeatId);

  return (
    <main className={`game-shell ${isYourTurn ? "your-turn" : "waiting-turn"}`}>
      <section className="score-rail">
        <div className="rail-title">
          <Crown size={18} />
          Players
        </div>
        {state.seats.map((seat) => (
          <div
            className={`seat-row ${seat.active ? "" : "is-out"} ${seat.id === state.currentSeatId ? "is-turn" : ""}`}
            key={seat.id}
          >
            <div className="seat-avatar-wrap">
              <div className="seat-avatar" aria-hidden="true">
                <span className="avatar-head" />
                <span className="avatar-body" />
              </div>
              {seat.id === state.currentSeatId || seatBubbles[seat.id] ? (
                <div className={`speech-bubble ${seatBubbles[seat.id]?.tone ?? "thinking"}`}>
                  {seatBubbles[seat.id]?.text ?? "..."}
                </div>
              ) : null}
            </div>
            <span className="seat-name">{seat.username}</span>
            <strong>{seat.correct}</strong>
          </div>
        ))}
      </section>

      <section className="play-area">
        <div className="timer-stack">
          <div className={`timer ${secondsLeft <= 5 ? "danger" : ""}`}>{secondsLeft}</div>
          <p>{currentSeat ? `${currentSeat.username}'s turn` : "Game complete"}</p>
        </div>

        <div className="target-player">
          <span>Name a teammate of:</span>
          <h1>{state.currentTarget.name}</h1>
        </div>

        {state.finished ? (
          <div className="winner-panel">
            <Trophy size={34} />
            <h2>{winner?.username ?? "Nobody"} wins</h2>
            <button className="primary-action" type="button" onClick={onExit}>
              Back home
            </button>
          </div>
        ) : (
          <form className="guess-form" onSubmit={submitGuess}>
            <div className={`input-wrap ${invalid ? "invalid" : ""} ${isYourTurn ? "" : "is-disabled"}`}>
              <Search size={19} />
              <input
                value={guess}
                disabled={!isYourTurn}
                onChange={(event) => {
                  setGuess(event.target.value);
                  setShowSuggestions(true);
                }}
                onFocus={() => setShowSuggestions(true)}
                placeholder={isYourTurn ? "Enter a teammate" : "Waiting for your turn"}
                autoComplete="off"
              />
            </div>
            {suggestions.length > 0 && isYourTurn && showSuggestions ? (
              <div className="suggestions">
                {suggestions.map((player) => (
                  <button
                    type="button"
                    key={player.id}
                    onClick={() => {
                      setGuess(player.name);
                      setShowSuggestions(false);
                    }}
                  >
                    {player.name}
                  </button>
                ))}
              </div>
            ) : null}
            <button className="submit-button" disabled={!isYourTurn} type="button" onClick={() => void submitCurrentGuess()}>
              Lock answer
            </button>
          </form>
        )}

        <p className="table-message">{message}</p>

        <div className="chain-strip">
          {state.chain.map((player, index) => (
            <div className="chain-card" key={`${player.id}-${index}`}>
              <span>{index + 1}</span>
              <strong>{player.name}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="rules-rail">
        <ShieldX size={22} />
        <h2>Elimination Rules</h2>
        <p>Wrong player, expired clock, and repeated chain names keep the turn moving.</p>
      </section>
    </main>
  );
}

export default function App() {
  const [view, setView] = useState<"home" | "queue" | "game">("home");
  const [allPlayers, setAllPlayers] = useState<PlayerSummary[]>([]);
  const [leaderboard, setLeaderboard] = useState<Leaderboard>(emptyLeaderboard);
  const [user, setUser] = useState<AppUser | null>(() => {
    const raw = localStorage.getItem("teammate-chain-user");
    return raw ? (JSON.parse(raw) as AppUser) : null;
  });
  const [initialState, setInitialState] = useState<RoomState | null>(null);
  const [mode, setMode] = useState<"ai" | "online">("ai");
  const [onlineSocket, setOnlineSocket] = useState<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    bootstrap(user?.id).then((payload) => {
      setAllPlayers(payload.allPlayers);
      setLeaderboard(payload.leaderboard);
    });
  }, [user?.id]);

  function persistUser(nextUser: AppUser) {
    setUser(nextUser);
    localStorage.setItem("teammate-chain-user", JSON.stringify(nextUser));
  }

  function playSound(name: SoundName) {
    const AudioCtor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtor) return;
    const context = audioContextRef.current ?? new AudioCtor();
    audioContextRef.current = context;
    if (context.state === "suspended") {
      void context.resume();
    }
    const now = context.currentTime;
    const gain = context.createGain();
    gain.connect(context.destination);
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(name === "tick" ? 0.025 : 0.08, now + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + (name === "tick" ? 0.08 : name === "win" ? 0.46 : 0.2));

    const oscillator = context.createOscillator();
    oscillator.connect(gain);
    oscillator.type = name === "wrong" ? "sawtooth" : "sine";
    oscillator.frequency.setValueAtTime(name === "correct" || name === "win" ? 660 : name === "wrong" ? 220 : 880, now);
    if (name === "correct") oscillator.frequency.exponentialRampToValueAtTime(990, now + 0.16);
    if (name === "win") {
      oscillator.frequency.setValueAtTime(660, now);
      oscillator.frequency.setValueAtTime(880, now + 0.18);
      oscillator.frequency.setValueAtTime(660, now + 0.32);
    }
    if (name === "wrong") oscillator.frequency.exponentialRampToValueAtTime(130, now + 0.18);
    oscillator.start(now);
    oscillator.stop(now + (name === "tick" ? 0.09 : name === "win" ? 0.48 : 0.22));
  }

  async function startAiGame() {
    playSound("tick");
    const starter = await randomStarter();
    onlineSocket?.close();
    setOnlineSocket(null);
    const seats = [
      makeSeat(user?.username ?? "You"),
      makeSeat("Scout 40", 0.4),
      makeSeat("Rotation 75", 0.75),
      makeSeat("Archivist 90", 0.9)
    ].sort(() => Math.random() - 0.5);
    setMode("ai");
    setInitialState({
      event: "state",
      seats,
      currentSeatId: seats[Math.floor(Math.random() * seats.length)].id,
      currentTarget: starter,
      chain: [],
      usedPlayerIds: [starter.id],
      expiresAt: Date.now() / 1000 + TURN_SECONDS,
      finished: false,
      youSeatId: seats.find((seat) => !seat.botAccuracy)?.id
    });
    setView("game");
  }

  async function handleGoogleLogin(credential: string) {
    const payload = await loginWithGoogle(credential);
    if (payload.user) persistUser(payload.user);
  }

  async function handleUsername(value: string) {
    if (!user) return;
    const payload = await updateUsername(user.id, value);
    if (payload.user) persistUser(payload.user);
  }

  if (view === "queue") {
    return (
      <QueueScreen
        user={user}
        onCancel={() => setView("home")}
        onStarted={(state, socket) => {
          setMode("online");
          setInitialState(state);
          setOnlineSocket(socket);
          setView("game");
        }}
      />
    );
  }

  if (view === "game" && initialState) {
    return (
      <Game
        initialState={initialState}
        allPlayers={allPlayers}
        user={user}
        mode={mode}
        onlineSocket={onlineSocket}
        playSound={playSound}
        onExit={() => {
          onlineSocket?.close();
          setOnlineSocket(null);
          setView("home");
        }}
        onStats={(nextUser, nextLeaderboard) => {
          persistUser(nextUser);
          setLeaderboard(nextLeaderboard);
        }}
      />
    );
  }

  return (
    <Home
      user={user}
      leaderboard={leaderboard}
      onQueue={() => {
        playSound("tick");
        setView("queue");
      }}
      onAi={startAiGame}
      onLogin={handleGoogleLogin}
      onUsername={handleUsername}
    />
  );
}
