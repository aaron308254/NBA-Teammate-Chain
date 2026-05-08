from __future__ import annotations

import asyncio
import base64
import json
import os
import random
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .nba_data import NBADataService, PlayerSummary, normalize_name


APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "teammate_chain.sqlite3"
TURN_SECONDS = 15

app = FastAPI(title="NBA Teammate Chain API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "https://aaron308254.github.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nba = NBADataService(APP_DIR / "cache")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT,
                username TEXT NOT NULL,
                avatar_url TEXT,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                correct_answers INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()


init_db()


class ValidateGuessRequest(BaseModel):
    current_player_id: int
    guess: str
    used_player_ids: list[int] = []
    current_only: bool = False


class GoogleAuthRequest(BaseModel):
    credential: str
    username: str | None = None


class UsernameRequest(BaseModel):
    user_id: str
    username: str


class StatsRequest(BaseModel):
    user_id: str
    won: bool
    correct_answers: int = 0


def decode_google_credential(credential: str) -> dict[str, Any]:
    parts = credential.split(".")
    if len(parts) < 2:
        raise ValueError("Invalid Google credential")
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    decoded = base64.urlsafe_b64decode(payload.encode("utf-8"))
    return json.loads(decoded)


def public_user(row: sqlite3.Row, rank: int | None = None) -> dict[str, Any]:
    wins = int(row["wins"])
    losses = int(row["losses"])
    total = wins + losses
    return {
        "id": row["id"],
        "username": row["username"],
        "avatarUrl": row["avatar_url"],
        "wins": wins,
        "losses": losses,
        "correctAnswers": int(row["correct_answers"]),
        "winPercentage": round((wins / total) * 100, 1) if total else 0,
        "rank": rank,
    }


def upsert_google_user(payload: dict[str, Any], username: str | None) -> dict[str, Any]:
    user_id = f"google:{payload['sub']}"
    email = payload.get("email")
    avatar_url = payload.get("picture")
    default_username = username or payload.get("name") or (email.split("@")[0] if email else "Hooper")
    with db() as conn:
        existing = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if existing:
            if username:
                conn.execute("UPDATE users SET username = ? WHERE id = ?", (username.strip()[:24], user_id))
            conn.execute("UPDATE users SET email = ?, avatar_url = ? WHERE id = ?", (email, avatar_url, user_id))
        else:
            conn.execute(
                "INSERT INTO users (id, email, username, avatar_url, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, email, default_username.strip()[:24], avatar_url, int(time.time())),
            )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return public_user(row)


def leaderboard_response(user_id: str | None = None) -> dict[str, Any]:
    with db() as conn:
        top_rows = conn.execute(
            "SELECT * FROM users ORDER BY wins DESC, correct_answers DESC, username ASC LIMIT 10"
        ).fetchall()
        all_rows = conn.execute(
            "SELECT * FROM users ORDER BY wins DESC, correct_answers DESC, username ASC"
        ).fetchall()

    ranked = [public_user(row, index + 1) for index, row in enumerate(all_rows)]
    top_ids = {row["id"] for row in top_rows}
    me = None
    if user_id:
        me = next((row for row in ranked if row["id"] == user_id), None)
    return {
        "top": [public_user(row, index + 1) for index, row in enumerate(top_rows)],
        "me": me if me and me["id"] not in top_ids else None,
    }


@app.get("/api/bootstrap")
def bootstrap(user_id: str | None = None) -> dict[str, Any]:
    return {
        "allPlayers": [player.model_dump() for player in nba.get_all_players()],
        "currentPlayers": [player.model_dump() for player in nba.get_current_players()],
        "leaderboard": leaderboard_response(user_id),
    }


@app.get("/api/random-starter")
def random_starter(currentOnly: bool = False) -> dict[str, Any]:
    return nba.random_top_scorer(currentOnly).model_dump()


@app.get("/api/suggest")
def suggest(q: str) -> dict[str, Any]:
    return {"players": [player.model_dump() for player in nba.suggest(q)]}


@app.get("/api/teammates/{player_id}")
def teammates(player_id: int, used: str = "") -> dict[str, Any]:
    used_ids = {int(item) for item in used.split(",") if item.strip().isdigit()}
    players = [player for player in nba.get_teammates(player_id) if player.id not in used_ids]
    return {"players": [player.model_dump() for player in players]}


@app.get("/api/bot-answer/{player_id}")
def bot_answer(player_id: int, used: str = "", currentOnly: bool = False) -> dict[str, Any]:
    used_ids = {int(item) for item in used.split(",") if item.strip().isdigit()}
    player = nba.random_scoring_teammate(player_id, used_ids, current_only=currentOnly)
    return {"player": player.model_dump() if player else None}


@app.get("/api/debug/player-seasons")
def debug_player_seasons(q: str, refresh: bool = False) -> dict[str, Any]:
    player = nba.resolve_player(q)
    if not player:
        return {"error": "unknown_player", "query": q}
    return nba.debug_player_seasons(player.id, refresh)


@app.get("/api/debug/teammate-check")
def debug_teammate_check(player1: str, player2: str, refresh: bool = False) -> dict[str, Any]:
    first = nba.resolve_player(player1)
    second = nba.resolve_player(player2)
    if not first or not second:
        return {
            "error": "unknown_player",
            "player1": first.model_dump() if first else None,
            "player2": second.model_dump() if second else None,
        }
    return nba.debug_teammate_check(first.id, second.id, refresh)


@app.get("/api/debug/bot-answer/{player_id}")
def debug_bot_answer(player_id: int, used: str = "", samples: int = 8, currentOnly: bool = False) -> dict[str, Any]:
    used_ids = {int(item) for item in used.split(",") if item.strip().isdigit()}
    return nba.debug_bot_answer(player_id, used_ids, samples, currentOnly)


@app.post("/api/debug/warm-cache")
def debug_warm_cache(limit: int = 40) -> dict[str, Any]:
    return nba.warm_bot_cache(limit)


@app.post("/api/validate")
def validate_guess(request: ValidateGuessRequest) -> dict[str, Any]:
    match = nba.find_player(request.guess)
    if not match:
        return {"valid": False, "reason": "unknown_player"}
    if request.current_only and not nba.is_current_player(match.id):
        return {"valid": False, "reason": "not_current", "player": match.model_dump()}
    if match.id in set(request.used_player_ids):
        return {"valid": False, "reason": "repeat", "player": match.model_dump()}
    valid_teammate = (
        nba.are_current_mode_teammates(request.current_player_id, match.id)
        if request.current_only
        else nba.are_regular_season_teammates(request.current_player_id, match.id)
    )
    if not valid_teammate:
        return {"valid": False, "reason": "not_teammate", "player": match.model_dump()}
    return {"valid": True, "player": match.model_dump()}


@app.post("/api/auth/google")
async def google_auth(request: GoogleAuthRequest) -> dict[str, Any]:
    payload = decode_google_credential(request.credential)
    aud = payload.get("aud")
    expected_aud = os.getenv("GOOGLE_CLIENT_ID")
    if expected_aud and aud != expected_aud:
        return {"error": "Google client id mismatch"}
    return {"user": upsert_google_user(payload, request.username)}


@app.post("/api/me/username")
async def update_username(request: UsernameRequest) -> dict[str, Any]:
    username = request.username.strip()[:24]
    if len(username) < 2:
        return {"error": "Username must be at least 2 characters"}
    with db() as conn:
        conn.execute("UPDATE users SET username = ? WHERE id = ?", (username, request.user_id))
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (request.user_id,)).fetchone()
    return {"user": public_user(row)}


@app.get("/api/leaderboard")
async def leaderboard(user_id: str | None = None) -> dict[str, Any]:
    return leaderboard_response(user_id)


@app.post("/api/stats")
async def update_stats(request: StatsRequest) -> dict[str, Any]:
    with db() as conn:
        conn.execute(
            """
            UPDATE users
            SET wins = wins + ?, losses = losses + ?, correct_answers = correct_answers + ?
            WHERE id = ?
            """,
            (1 if request.won else 0, 0 if request.won else 1, max(0, request.correct_answers), request.user_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (request.user_id,)).fetchone()
    return {"user": public_user(row), "leaderboard": leaderboard_response(request.user_id)}


@dataclass
class Seat:
    id: str
    username: str
    user_id: str | None
    active: bool = True
    correct: int = 0
    eliminated_reason: str | None = None


@dataclass
class Room:
    id: str
    sockets: dict[str, WebSocket]
    seats: list[Seat]
    current_target: PlayerSummary
    used_player_ids: set[int]
    current_only: bool = False
    chain: list[PlayerSummary] = field(default_factory=list)
    turn_index: int = 0
    expires_at: float = 0
    timer_task: asyncio.Task[Any] | None = None
    finished: bool = False

    def active_seats(self) -> list[Seat]:
        return [seat for seat in self.seats if seat.active]

    def current_seat(self) -> Seat:
        for _ in range(len(self.seats)):
            seat = self.seats[self.turn_index % len(self.seats)]
            if seat.active:
                return seat
            self.turn_index = (self.turn_index + 1) % len(self.seats)
        return self.seats[0]

    def advance_turn(self) -> None:
        if len(self.active_seats()) <= 1:
            return
        for _ in range(len(self.seats)):
            self.turn_index = (self.turn_index + 1) % len(self.seats)
            if self.seats[self.turn_index].active:
                return


waiting: list[tuple[WebSocket, Seat, bool]] = []
rooms: dict[str, Room] = {}


def room_payload(room: Room, event: str = "state", message: str | None = None) -> dict[str, Any]:
    return {
        "event": event,
        "roomId": room.id,
        "message": message,
        "seats": [seat.__dict__ for seat in room.seats],
        "currentSeatId": room.current_seat().id if not room.finished else None,
        "currentTarget": room.current_target.model_dump(),
        "chain": [player.model_dump() for player in room.chain],
        "usedPlayerIds": list(room.used_player_ids),
        "gameMode": "current" if room.current_only else "all",
        "expiresAt": room.expires_at,
        "finished": room.finished,
        "winnerSeatId": room.active_seats()[0].id if room.finished and room.active_seats() else None,
    }


async def broadcast(room: Room, payload: dict[str, Any]) -> None:
    for seat_id, socket in list(room.sockets.items()):
        await socket.send_json({**payload, "youSeatId": seat_id})


async def finish_room(room: Room) -> None:
    room.finished = True
    if room.timer_task:
        room.timer_task.cancel()
    winner = room.active_seats()[0] if room.active_seats() else None
    with db() as conn:
        for seat in room.seats:
            if seat.user_id:
                conn.execute(
                    """
                    UPDATE users
                    SET wins = wins + ?, losses = losses + ?, correct_answers = correct_answers + ?
                    WHERE id = ?
                    """,
                    (1 if winner and seat.id == winner.id else 0, 0 if winner and seat.id == winner.id else 1, seat.correct, seat.user_id),
                )
        conn.commit()
    await broadcast(room, room_payload(room, "game_over"))


async def start_room_timer(room: Room) -> None:
    if room.timer_task:
        room.timer_task.cancel()
    room.expires_at = time.time() + TURN_SECONDS
    await broadcast(room, room_payload(room))

    async def expire() -> None:
        await asyncio.sleep(TURN_SECONDS)
        if room.finished:
            return
        seat = room.current_seat()
        seat.active = False
        seat.eliminated_reason = "time"
        if len(room.active_seats()) <= 1:
            await finish_room(room)
            return
        room.advance_turn()
        await start_room_timer(room)

    room.timer_task = asyncio.create_task(expire())


async def create_room(group: list[tuple[WebSocket, Seat, bool]], current_only: bool) -> None:
    random.shuffle(group)
    room = Room(
        id=str(uuid.uuid4()),
        sockets={seat.id: socket for socket, seat, _ in group},
        seats=[seat for _, seat, _ in group],
        current_target=nba.random_top_scorer(current_only),
        used_player_ids=set(),
        current_only=current_only,
        turn_index=random.randrange(4),
    )
    room.used_player_ids.add(room.current_target.id)
    rooms[room.id] = room
    await start_room_timer(room)


@app.websocket("/ws/queue")
async def queue_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    seat = Seat(
        id=str(uuid.uuid4()),
        username=websocket.query_params.get("username") or "Player",
        user_id=websocket.query_params.get("userId"),
    )
    current_only = websocket.query_params.get("currentOnly", "").lower() in {"1", "true", "yes"}
    waiting.append((websocket, seat, current_only))
    try:
        queued_same_mode = [entry for entry in waiting if entry[2] == current_only]
        await websocket.send_json(
            {
                "event": "queued",
                "queued": len(queued_same_mode),
                "needed": 4,
                "youSeatId": seat.id,
                "gameMode": "current" if current_only else "all",
            }
        )
        if len(queued_same_mode) >= 4:
            group = queued_same_mode[:4]
            group_ids = {queued_seat.id for _, queued_seat, _ in group}
            waiting[:] = [entry for entry in waiting if entry[1].id not in group_ids]
            await create_room(group, current_only)
        while True:
            payload = await websocket.receive_json()
            room = next((candidate for candidate in rooms.values() if seat.id in candidate.sockets), None)
            if not room or room.finished:
                continue
            if payload.get("event") != "guess" or room.current_seat().id != seat.id:
                continue
            guess = str(payload.get("guess", ""))
            turn_target_id = room.current_target.id
            turn_expires_at = room.expires_at
            match = nba.find_player(guess)
            if not match:
                if (
                    room.finished
                    or room.current_seat().id != seat.id
                    or room.current_target.id != turn_target_id
                    or room.expires_at != turn_expires_at
                    or time.time() > turn_expires_at
                ):
                    continue
                seat.active = False
                seat.eliminated_reason = "unknown"
            elif match.id in room.used_player_ids:
                await websocket.send_json({"event": "repeat", "player": match.model_dump()})
                continue
            elif room.current_only and not nba.is_current_player(match.id):
                if (
                    room.finished
                    or room.current_seat().id != seat.id
                    or room.current_target.id != turn_target_id
                    or room.expires_at != turn_expires_at
                    or time.time() > turn_expires_at
                ):
                    continue
                seat.active = False
                seat.eliminated_reason = "not_current"
            elif not nba.are_regular_season_teammates(room.current_target.id, match.id):
                if (
                    room.finished
                    or room.current_seat().id != seat.id
                    or room.current_target.id != turn_target_id
                    or room.expires_at != turn_expires_at
                    or time.time() > turn_expires_at
                ):
                    continue
                seat.active = False
                seat.eliminated_reason = "wrong"
            else:
                if (
                    room.finished
                    or room.current_seat().id != seat.id
                    or room.current_target.id != turn_target_id
                    or room.expires_at != turn_expires_at
                    or time.time() > turn_expires_at
                ):
                    continue
                room.chain.append(room.current_target)
                room.used_player_ids.add(match.id)
                room.current_target = match
                seat.correct += 1
            if len(room.active_seats()) <= 1:
                await finish_room(room)
                continue
            room.advance_turn()
            await start_room_timer(room)
    except WebSocketDisconnect:
        waiting[:] = [
            (socket, queued_seat, queued_current_only)
            for socket, queued_seat, queued_current_only in waiting
            if queued_seat.id != seat.id
        ]
        room = next((candidate for candidate in rooms.values() if seat.id in candidate.sockets), None)
        if room and not room.finished:
            seat.active = False
            seat.eliminated_reason = "disconnect"
            if len(room.active_seats()) <= 1:
                await finish_room(room)
            else:
                room.advance_turn()
                await start_room_timer(room)
