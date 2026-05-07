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
    PlayerSummary(id=2548, name="Dwyane Wade"),
    PlayerSummary(id=202681, name="Kyrie Irving"),
    PlayerSummary(id=203076, name="Anthony Davis"),
    PlayerSummary(id=201566, name="Russell Westbrook"),
    PlayerSummary(id=1626164, name="Devin Booker"),
    PlayerSummary(id=202691, name="Klay Thompson"),
    PlayerSummary(id=203110, name="Draymond Green"),
    PlayerSummary(id=2738, name="Andre Iguodala"),
    PlayerSummary(id=203954, name="Joel Embiid"),
    PlayerSummary(id=937, name="Scottie Pippen"),
    PlayerSummary(id=23, name="Dennis Rodman"),
    PlayerSummary(id=2200, name="Pau Gasol"),
    PlayerSummary(id=965, name="Derek Fisher"),
    PlayerSummary(id=1938, name="Manu Ginobili"),
    PlayerSummary(id=2225, name="Tony Parker"),
    PlayerSummary(id=202695, name="Kawhi Leonard"),
    PlayerSummary(id=1718, name="Paul Pierce"),
    PlayerSummary(id=951, name="Ray Allen"),
    PlayerSummary(id=200765, name="Rajon Rondo"),
    PlayerSummary(id=1627750, name="Jamal Murray"),
    PlayerSummary(id=203932, name="Aaron Gordon"),
    PlayerSummary(id=1629008, name="Michael Porter Jr."),
    PlayerSummary(id=1628973, name="Jalen Brunson"),
    PlayerSummary(id=203081, name="Damian Lillard"),
    PlayerSummary(id=201950, name="Jrue Holiday"),
    PlayerSummary(id=203114, name="Khris Middleton"),
    PlayerSummary(id=201933, name="Blake Griffin"),
    PlayerSummary(id=201599, name="DeAndre Jordan"),
    PlayerSummary(id=203482, name="Kelly Olynyk"),
    PlayerSummary(id=1641705, name="Victor Wembanyama"),
    PlayerSummary(id=77142, name="Magic Johnson"),
    PlayerSummary(id=600015, name="Oscar Robertson"),
]

TOP_SCORER_FALLBACK_NAMES = [
    "LeBron James",
    "Kareem Abdul-Jabbar",
    "Karl Malone",
    "Kobe Bryant",
    "Michael Jordan",
    "Dirk Nowitzki",
    "Wilt Chamberlain",
    "Kevin Durant",
    "Shaquille O'Neal",
    "Carmelo Anthony",
    "Moses Malone",
    "Elvin Hayes",
    "Hakeem Olajuwon",
    "Oscar Robertson",
    "Dominique Wilkins",
    "Tim Duncan",
    "Paul Pierce",
    "John Havlicek",
    "Kevin Garnett",
    "Vince Carter",
    "James Harden",
    "Alex English",
    "Reggie Miller",
    "Jerry West",
    "Patrick Ewing",
    "Ray Allen",
    "Allen Iverson",
    "Russell Westbrook",
    "Charles Barkley",
    "Stephen Curry",
    "Robert Parish",
    "Adrian Dantley",
    "Dwyane Wade",
    "Elgin Baylor",
    "Clyde Drexler",
    "Gary Payton",
    "Larry Bird",
    "Hal Greer",
    "Chris Paul",
    "DeMar DeRozan",
    "Walt Bellamy",
    "Pau Gasol",
    "Bob Pettit",
    "David Robinson",
    "George Gervin",
    "LaMarcus Aldridge",
    "Mitch Richmond",
    "Joe Johnson",
    "Kemba Walker",
    "Tom Chambers",
    "Antawn Jamison",
    "John Stockton",
    "Bernard King",
    "Clifford Robinson",
    "Walter Davis",
    "Terry Cummings",
    "Paul George",
    "Bob Lanier",
    "Eddie Johnson",
    "Gail Goodrich",
    "Reggie Theus",
    "Dale Ellis",
    "Scottie Pippen",
    "Chet Walker",
    "Isiah Thomas",
    "Bob McAdoo",
    "Zach Randolph",
    "Kevin McHale",
    "Magic Johnson",
    "Mark Aguirre",
    "Shawn Marion",
    "Glen Rice",
    "World Free",
    "Kyrie Irving",
    "Julius Erving",
]

FALLBACK_TEAMMATES: dict[int, list[int]] = {
    2544: [2548, 202681, 203076, 406],
    201142: [201939, 201935, 201566, 1626164, 101108, 202681],
    201939: [201142, 202691, 203110, 2738, 101108],
    201935: [201142, 101108, 201566, 203954],
    893: [937, 23],
    977: [406, 2200, 965],
    406: [977, 2548, 2544, 708],
    1495: [1938, 2225, 202695],
    708: [1718, 951, 200765, 406],
    203999: [1627750, 203932, 1629008],
    1629029: [202681, 1628973],
    203507: [203081, 201950, 203114],
    101108: [201935, 1626164, 201933, 201939],
    76003: [77142, 600015],
    201933: [201599],
    201599: [201933],
    203482: [1641705],
    1641705: [203482],
    56: [],
    1717: [],
}

FALLBACK_PLAYER_SEASONS: dict[int, set[tuple[int, str]]] = {
    2544: {(1610612747, "2018-19"), (1610612747, "2019-20"), (1610612747, "2024-25")},
    201142: {(1610612744, "2016-17"), (1610612756, "2023-24")},
    201939: {(1610612744, "2016-17"), (1610612744, "2024-25")},
    201935: {(1610612745, "2017-18"), (1610612751, "2021-22")},
    101108: {(1610612745, "2017-18"), (1610612756, "2023-24")},
    977: {(1610612747, "2000-01")},
    406: {(1610612747, "2000-01"), (1610612738, "2010-11")},
    708: {(1610612738, "2010-11")},
    203507: {(1610612744, "2024-25")},
}

MANUAL_PLAYER_SEASONS: dict[int, set[tuple[int, str]]] = {
    201933: {
        (1610612746, "2009-10"),
        (1610612746, "2010-11"),
        (1610612746, "2011-12"),
        (1610612746, "2012-13"),
        (1610612746, "2013-14"),
        (1610612746, "2014-15"),
        (1610612746, "2015-16"),
        (1610612746, "2016-17"),
        (1610612746, "2017-18"),
    },
    201599: {
        (1610612746, "2008-09"),
        (1610612746, "2009-10"),
        (1610612746, "2010-11"),
        (1610612746, "2011-12"),
        (1610612746, "2012-13"),
        (1610612746, "2013-14"),
        (1610612746, "2014-15"),
        (1610612746, "2015-16"),
        (1610612746, "2016-17"),
        (1610612746, "2017-18"),
    },
    203482: {(1610612759, "2025-26")},
    1641705: {(1610612759, "2025-26")},
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
        self._season_cache_path = self.cache_dir / "player_seasons.json"
        self._scoring_cache_path = self.cache_dir / "team_scoring.json"
        self._teammate_cache: dict[str, list[int]] = self._load_teammate_cache()
        self._season_cache: dict[str, list[list[int | str]]] = self._load_json_cache(self._season_cache_path)
        self._scoring_cache: dict[str, list[dict[str, int | float | str]]] = self._load_json_cache(self._scoring_cache_path)

    def _load_json_cache(self, path: Path) -> dict:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _load_teammate_cache(self) -> dict[str, list[int]]:
        return self._load_json_cache(self._teammate_cache_path)

    def _save_teammate_cache(self) -> None:
        self._teammate_cache_path.write_text(json.dumps(self._teammate_cache, indent=2), encoding="utf-8")

    def _save_season_cache(self) -> None:
        self._season_cache_path.write_text(json.dumps(self._season_cache, indent=2), encoding="utf-8")

    def _save_scoring_cache(self) -> None:
        self._scoring_cache_path.write_text(json.dumps(self._scoring_cache, indent=2), encoding="utf-8")

    def get_all_players(self) -> list[PlayerSummary]:
        if self._all_players is not None:
            return self._all_players
        try:
            from nba_api.stats.static import players as static_players

            frame = pd.DataFrame(static_players.get_players())
            players = [
                PlayerSummary(id=int(row["id"]), name=str(row["full_name"]))
                for _, row in frame.iterrows()
                if pd.notna(row.get("id")) and row.get("full_name")
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
            self._top_scorers = candidates or self._fallback_top_scorers()
        except Exception:
            self._top_scorers = self._fallback_top_scorers()
        return self._top_scorers

    def _fallback_top_scorers(self) -> list[PlayerSummary]:
        by_name = {normalize_name(player.name): player for player in self.get_all_players()}
        players = [by_name[normalize_name(name)] for name in TOP_SCORER_FALLBACK_NAMES if normalize_name(name) in by_name]
        return players or FALLBACK_PLAYERS

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

    def _manual_player_seasons(self, player_id: int) -> set[tuple[int, str]]:
        return set(FALLBACK_PLAYER_SEASONS.get(player_id, set())) | set(MANUAL_PLAYER_SEASONS.get(player_id, set()))

    def _player_seasons(self, player_id: int) -> list[tuple[int, str]]:
        cache_key = str(player_id)
        manual = self._manual_player_seasons(player_id)
        if cache_key in self._season_cache:
            cached = {(int(team_id), str(season)) for team_id, season in self._season_cache[cache_key]}
            return sorted(cached | manual)
        from nba_api.stats.endpoints import playercareerstats

        try:
            response = playercareerstats.PlayerCareerStats(player_id=player_id, timeout=12)
            frame = response.get_data_frames()[0]
            rows: set[tuple[int, str]] = set()
            for _, row in frame.iterrows():
                team_id = row.get("TEAM_ID")
                season_id = row.get("SEASON_ID")
                if pd.notna(team_id) and pd.notna(season_id) and int(team_id) > 0:
                    rows.add((int(team_id), str(season_id)))
            rows |= manual
            self._season_cache[cache_key] = [[team_id, season] for team_id, season in sorted(rows)]
            self._save_season_cache()
            return sorted(rows)
        except Exception:
            return sorted(manual)

    def are_regular_season_teammates(self, first_player_id: int, second_player_id: int) -> bool:
        try:
            first = set(self._player_seasons(first_player_id))
            second = set(self._player_seasons(second_player_id))
            return bool(first & second)
        except Exception:
            return bool(
                FALLBACK_PLAYER_SEASONS.get(first_player_id, set())
                & FALLBACK_PLAYER_SEASONS.get(second_player_id, set())
            )

    def _team_roster(self, team_id: int, season: str) -> list[PlayerSummary]:
        from nba_api.stats.endpoints import commonteamroster

        response = commonteamroster.CommonTeamRoster(team_id=team_id, season=season, timeout=5)
        frame = response.get_data_frames()[0]
        players = []
        for _, row in frame.iterrows():
            player_id = row.get("PLAYER_ID")
            name = row.get("PLAYER") or row.get("PLAYER_NAME")
            if pd.notna(player_id) and name:
                players.append(PlayerSummary(id=int(player_id), name=str(name)))
        return players

    def _team_scoring_players(self, team_id: int, season: str) -> list[dict[str, int | float | str]]:
        cache_key = f"{team_id}:{season}"
        if cache_key in self._scoring_cache:
            return self._scoring_cache[cache_key]
        from nba_api.stats.endpoints import leaguedashplayerstats

        response = leaguedashplayerstats.LeagueDashPlayerStats(
            per_mode_detailed="PerGame",
            season=season,
            season_type_all_star="Regular Season",
            team_id_nullable=team_id,
            timeout=5,
        )
        frame = response.get_data_frames()[0]
        rows: list[dict[str, int | float | str]] = []
        for _, row in frame.iterrows():
            player_id = row.get("PLAYER_ID")
            name = row.get("PLAYER_NAME")
            points = row.get("PTS")
            if pd.notna(player_id) and name and pd.notna(points):
                rows.append({"id": int(player_id), "name": str(name), "points": float(points)})
        self._scoring_cache[cache_key] = rows
        self._save_scoring_cache()
        return rows

    def _players_by_id(self) -> dict[int, PlayerSummary]:
        return {player.id: player for player in self.get_all_players()}

    def _fallback_regular_teammates(self, player_id: int, used_player_ids: set[int]) -> list[PlayerSummary]:
        players_by_id = self._players_by_id()
        return [
            players_by_id[teammate_id]
            for teammate_id in FALLBACK_TEAMMATES.get(player_id, [])
            if teammate_id not in used_player_ids and teammate_id in players_by_id
        ]

    def _cached_regular_teammates(self, player_id: int, used_player_ids: set[int]) -> list[PlayerSummary]:
        seasons = {tuple(row) for row in self._season_cache.get(str(player_id), [])}
        if not seasons:
            return []
        players_by_id = self._players_by_id()
        teammates: list[PlayerSummary] = []
        for cached_id, cached_seasons in self._season_cache.items():
            teammate_id = int(cached_id)
            if teammate_id == player_id or teammate_id in used_player_ids or teammate_id not in players_by_id:
                continue
            if seasons & {tuple(row) for row in cached_seasons}:
                teammates.append(players_by_id[teammate_id])
        return teammates

    def _cached_scoring_teammates(
        self, player_id: int, used_player_ids: set[int], min_points: float
    ) -> list[PlayerSummary]:
        candidates: dict[int, PlayerSummary] = {}
        for team_id, season in self._season_cache.get(str(player_id), []):
            for player in self._scoring_cache.get(f"{team_id}:{season}", []):
                candidate_id = int(player["id"])
                if candidate_id == player_id or candidate_id in used_player_ids or float(player["points"]) <= min_points:
                    continue
                candidates[candidate_id] = PlayerSummary(id=candidate_id, name=str(player["name"]))
        return list(candidates.values())

    def random_scoring_teammate(self, player_id: int, used_player_ids: set[int], min_points: float = 7.0) -> PlayerSummary | None:
        cached_scoring = self._cached_scoring_teammates(player_id, used_player_ids, min_points)
        if cached_scoring:
            return random.choice(cached_scoring)

        fallback = self._fallback_regular_teammates(player_id, used_player_ids)
        if fallback:
            return random.choice(fallback)

        cached_regular = self._cached_regular_teammates(player_id, used_player_ids)
        if cached_regular:
            return random.choice(cached_regular)

        try:
            seasons = self._player_seasons(player_id)
            random.shuffle(seasons)
            for team_id, season in seasons[:1]:
                candidates = [
                    PlayerSummary(id=int(player["id"]), name=str(player["name"]))
                    for player in self._team_scoring_players(team_id, season)
                    if int(player["id"]) != player_id
                    and int(player["id"]) not in used_player_ids
                    and float(player["points"]) > min_points
                ]
                if candidates:
                    return random.choice(candidates)
        except Exception:
            pass

        fallback = self._fallback_regular_teammates(player_id, used_player_ids)
        return random.choice(fallback) if fallback else None

    def get_teammates(self, player_id: int) -> list[PlayerSummary]:
        cache_key = str(player_id)
        players_by_id = self._players_by_id()
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
