from __future__ import annotations

import json
import random
import re
from pathlib import Path

import pandas as pd
from pydantic import BaseModel


class PlayerSummary(BaseModel):
    id: int
    name: str


FALLBACK_PLAYERS = [
    PlayerSummary(id=893, name="Michael Jordan"),
    PlayerSummary(id=2544, name="LeBron James"),
    PlayerSummary(id=76003, name="Kareem Abdul-Jabbar"),
    PlayerSummary(id=201939, name="Stephen Curry"),
    PlayerSummary(id=977, name="Kobe Bryant"),
    PlayerSummary(id=1717, name="Dirk Nowitzki"),
    PlayerSummary(id=406, name="Shaquille O'Neal"),
    PlayerSummary(id=1495, name="Tim Duncan"),
    PlayerSummary(id=708, name="Kevin Garnett"),
    PlayerSummary(id=56, name="Gary Payton"),
    PlayerSummary(id=101108, name="Chris Paul"),
    PlayerSummary(id=201142, name="Kevin Durant"),
    PlayerSummary(id=201935, name="James Harden"),
    PlayerSummary(id=203507, name="Giannis Antetokounmpo"),
    PlayerSummary(id=203999, name="Nikola Jokic"),
    PlayerSummary(id=1629029, name="Luka Doncic"),
]

FALLBACK_TEAMMATES: dict[int, list[int]] = {
    2544: [101108, 201142, 201939, 203999],
    101108: [2544, 201935, 201142],
    201142: [201939, 101108, 201935, 2544],
    201939: [201142, 203507, 2544],
    201935: [201142, 101108],
    893: [977, 406],
    977: [893, 406],
    406: [893, 977, 708],
    1495: [708],
    708: [1495, 406],
    203999: [2544, 1629029],
    1629029: [203999],
    203507: [201939],
    76003: [56],
    56: [76003],
    1717: [101108],
}


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def last_name(value: str) -> str:
    parts = value.strip().split()
    return parts[-1] if parts else value


class NBADataService:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self._all_players: list[PlayerSummary] | None = None
        self._top_scorers: list[PlayerSummary] | None = None
        self._teammate_cache_path = self.cache_dir / "teammates.json"
        self._teammate_cache: dict[str, list[int]] = self._load_teammate_cache()

    def _load_teammate_cache(self) -> dict[str, list[int]]:
        if self._teammate_cache_path.exists():
            return json.loads(self._teammate_cache_path.read_text(encoding="utf-8"))
        return {}

    def _save_teammate_cache(self) -> None:
        self._teammate_cache_path.write_text(json.dumps(self._teammate_cache, indent=2), encoding="utf-8")

    def get_all_players(self) -> list[PlayerSummary]:
        if self._all_players is not None:
            return self._all_players
        try:
            from nba_api.stats.endpoints import commonallplayers

            response = commonallplayers.CommonAllPlayers(is_only_current_season=0, timeout=20)
            frame = response.get_data_frames()[0]
            players = [
                PlayerSummary(id=int(row["PERSON_ID"]), name=str(row["DISPLAY_FIRST_LAST"]))
                for _, row in frame.iterrows()
                if pd.notna(row.get("PERSON_ID")) and row.get("DISPLAY_FIRST_LAST")
            ]
            self._all_players = sorted(players, key=lambda player: player.name)
        except Exception:
            self._all_players = sorted(FALLBACK_PLAYERS, key=lambda player: player.name)
        return self._all_players

    def get_top_scorers(self) -> list[PlayerSummary]:
        if self._top_scorers is not None:
            return self._top_scorers
        try:
            from nba_api.stats.endpoints import alltimeleadersgrids

            response = alltimeleadersgrids.AllTimeLeadersGrids(
                league_id="00",
                per_mode_simple="Totals",
                season_type="Regular Season",
                topx=75,
                timeout=20,
            )
            candidates: list[PlayerSummary] = []
            for frame in response.get_data_frames():
                columns = {column.upper(): column for column in frame.columns}
                id_col = columns.get("PLAYER_ID") or columns.get("PERSON_ID")
                name_col = columns.get("PLAYER_NAME") or columns.get("DISPLAY_FIRST_LAST")
                pts_col = columns.get("PTS")
                if id_col and name_col and pts_col:
                    candidates = [
                        PlayerSummary(id=int(row[id_col]), name=str(row[name_col]))
                        for _, row in frame.head(75).iterrows()
                        if pd.notna(row.get(id_col)) and row.get(name_col)
                    ]
                    break
            self._top_scorers = candidates or FALLBACK_PLAYERS
        except Exception:
            self._top_scorers = FALLBACK_PLAYERS
        return self._top_scorers

    def random_top_scorer(self) -> PlayerSummary:
        return random.choice(self.get_top_scorers())

    def find_player(self, value: str) -> PlayerSummary | None:
        needle = normalize_name(value)
        if not needle:
            return None
        players = self.get_all_players()
        exact = next((player for player in players if normalize_name(player.name) == needle), None)
        if exact:
            return exact
        return next(
            (
                player
                for player in players
                if normalize_name(last_name(player.name)) == needle or normalize_name(player.name).startswith(needle)
            ),
            None,
        )

    def suggest(self, value: str, limit: int = 8) -> list[PlayerSummary]:
        needle = normalize_name(value)
        if len(needle) < 2:
            return []
        matches = []
        for player in self.get_all_players():
            first, *rest = player.name.split()
            last = rest[-1] if rest else first
            haystacks = [normalize_name(player.name), normalize_name(first), normalize_name(last)]
            if any(haystack.startswith(needle) for haystack in haystacks) or any(needle in haystack for haystack in haystacks):
                matches.append(player)
            if len(matches) >= limit:
                break
        return matches

    def _player_seasons(self, player_id: int) -> list[tuple[int, str]]:
        from nba_api.stats.endpoints import playercareerstats

        response = playercareerstats.PlayerCareerStats(player_id=player_id, timeout=20)
        frame = response.get_data_frames()[0]
        rows: list[tuple[int, str]] = []
        for _, row in frame.iterrows():
            team_id = row.get("TEAM_ID")
            season_id = row.get("SEASON_ID")
            if pd.notna(team_id) and pd.notna(season_id) and int(team_id) > 0:
                rows.append((int(team_id), str(season_id)))
        return rows

    def _team_roster(self, team_id: int, season: str) -> list[PlayerSummary]:
        from nba_api.stats.endpoints import commonteamroster

        response = commonteamroster.CommonTeamRoster(team_id=team_id, season=season, timeout=20)
        frame = response.get_data_frames()[0]
        players = []
        for _, row in frame.iterrows():
            player_id = row.get("PLAYER_ID")
            name = row.get("PLAYER") or row.get("PLAYER_NAME")
            if pd.notna(player_id) and name:
                players.append(PlayerSummary(id=int(player_id), name=str(name)))
        return players

    def get_teammates(self, player_id: int) -> list[PlayerSummary]:
        cache_key = str(player_id)
        players_by_id = {player.id: player for player in self.get_all_players()}
        if cache_key in self._teammate_cache:
            return [
                players_by_id[player_id]
                for player_id in self._teammate_cache[cache_key]
                if player_id in players_by_id
            ]
        try:
            teammate_ids: set[int] = set()
            for team_id, season in self._player_seasons(player_id):
                for roster_player in self._team_roster(team_id, season):
                    if roster_player.id != player_id:
                        players_by_id[roster_player.id] = roster_player
                        teammate_ids.add(roster_player.id)
            self._teammate_cache[cache_key] = sorted(teammate_ids)
            self._save_teammate_cache()
            return [players_by_id[player_id] for player_id in sorted(teammate_ids) if player_id in players_by_id]
        except Exception:
            teammate_ids = FALLBACK_TEAMMATES.get(player_id, [])
            teammates: list[PlayerSummary] = []
            for teammate_id in teammate_ids:
                match = next((player for player in FALLBACK_PLAYERS if player.id == teammate_id), None)
                if match:
                    teammates.append(match)
            return teammates
