from dataclasses import dataclass, field, asdict
from typing import Optional
 
 
# --------------------------------------------------------------------
# 1. The two teams in this game.
#    We use short keys ("by", "gr") everywhere in the code, and look up
#    the display names only when we show something to a human.
# --------------------------------------------------------------------
 
TEAMS = {
    "by": {"name": "Black/Yellow", "short": "B/Y"},
    "gr": {"name": "Green", "short": "GRN"},
}
 
 
def other_teams(team: str) -> str:
    """Given one team key, return the other one."""
    return "gr" if team == "by" else "by"
 
 
# --------------------------------------------------------------------
# 2. Every statistic we can tag, in one place.
#
#    key       the keyboard key you press while watching
#    code      the short name stored in the data and shown in Excel
#    label     what a human calls it
#    flow      how many players the event asks for:
#                "one"     a single player
#                "goal"    scorer, then assist 1, then assist 2
#                "faceoff" winner, then loser
#                "onice"   a whole line of players at once
#                "note"    no player, just text
#    quals     optional extra keys that describe the event
#
#    To add a new statistic later, you add one entry here. You do not
#    touch any other file.
# --------------------------------------------------------------------
 
EVENT_TYPES = {
    "s": {"code": "SOG",    "label": "Shot on goal",   "flow": "one"},
    "a": {"code": "MISS",   "label": "Shot missed",    "flow": "one"},
    "b": {"code": "BLOCK",  "label": "Shot blocked",   "flow": "one"},
    "g": {"code": "GOAL",   "label": "Goal",           "flow": "goal"},
    "h": {"code": "CHANCE", "label": "Scoring chance", "flow": "one",
          "quals": {"d": "high danger"}},
    "f": {"code": "FO",     "label": "Faceoff won",    "flow": "faceoff"},
    "e": {"code": "ENTRY",  "label": "Zone entry",     "flow": "one",
          "quals": {"c": "controlled", "d": "dump-in"}},
    "x": {"code": "EXIT",   "label": "Zone exit",      "flow": "one",
          "quals": {"c": "controlled", "w": "clear/chip"}},
    "v": {"code": "GIVE",   "label": "Giveaway",       "flow": "one"},
    "t": {"code": "TAKE",   "label": "Takeaway",       "flow": "one"},
    "p": {"code": "PASS",   "label": "Pass attempt",   "flow": "one",
          "quals": {"k": "completed", "s": "led to shot"}},
    "n": {"code": "PEN",    "label": "Penalty",        "flow": "one"},
    "l": {"code": "ONICE",  "label": "On-ice set",     "flow": "onice"},
    "o": {"code": "NOTE",   "label": "Observation",    "flow": "note"},
}
 
# The same information the other way round: code -> definition.
# Handy when we read an event back and want to know its qualifiers.
BY_CODE = {v["code"]: {**v, "key": k} for k, v in EVENT_TYPES.items()}
 
 
def qualifier_names(code: str, quals: list[str]) -> str:
    """Turn ['c'] on an ENTRY into the words 'controlled'."""
    definition = BY_CODE.get(code, {})
    lookup = definition.get("quals", {})
    return ", ".join(lookup.get(q, q) for q in quals)
 
 
# --------------------------------------------------------------------
# 3. A player.
#
#    `number` is a string, not an int, on purpose. Early in the game you
#    will not be able to read every jersey, so you need to be able to
#    write down "A" or "B" as a placeholder and rename it later.
# --------------------------------------------------------------------
 
@dataclass
class Player:
    team: str                 # "by" or "gr"
    number: str               # "11", or a placeholder like "A"
    position: str = ""        # "F", "D", "G", or blank
    note: str = ""            # "white stick tape", "tallest on the line"
    confirmed: bool = False   # did you actually read the number?
 
    def label(self) -> str:
        return f"#{self.number}"
 
 
# --------------------------------------------------------------------
# 4. A player's part in one event.
#
#    role tells us WHY this player is attached to the event:
#      ""        the player who did the thing (a shot, a giveaway)
#      "scorer"  / "assist1" / "assist2"   on a goal
#      "won" / "lost"                      on a faceoff
#      "onice"                             one of the players on the ice
# --------------------------------------------------------------------
 
@dataclass
class EventPlayer:
    team: str
    number: str
    role: str = ""
 
 
# --------------------------------------------------------------------
# 5. An event: one thing that happened, at one moment.
#
#    t       seconds into the video file. This is our source of truth,
#            because it is the only time we can measure exactly.
#    clock   the game clock, worked out from your sync points. It can be
#            blank, and that is fine.
#    flagged you could not read it clearly and want to review it later.
#            This is the honesty switch: we flag instead of guessing.
# --------------------------------------------------------------------
 
@dataclass
class Event:
    t: float
    code: str
    team: str
    players: list[EventPlayer] = field(default_factory=list)
    quals: list[str] = field(default_factory=list)
    period: str = "1"
    clock: str = ""
    flagged: bool = False
    note: str = ""
    clip: str = ""            # which video file this came from
    id: int = 0               # filled in by the Game when it is added
 
    # --- small helpers the rest of the project will use ---
 
    def first_player(self) -> Optional[EventPlayer]:
        """The player who did the thing. None for on-ice sets and notes."""
        return self.players[0] if self.players else None
 
    def numbers(self) -> list[str]:
        return [p.number for p in self.players]
 
    def has_qual(self, q: str) -> bool:
        return q in self.quals
 
 
# --------------------------------------------------------------------
# 6. A clock sync point.
#
#    The tool cannot read the scoreboard, so you tell it: "at 412.5
#    seconds into the video, the scoreboard said 8:30 in period 2".
#    From there it counts down. Because the game clock stops at every
#    whistle and the video does not, you re-sync often.
# --------------------------------------------------------------------
 
@dataclass
class ClockSync:
    t: float                  # video seconds
    period: str               # "1", "2", "3", "OT"
    seconds_left: int         # clock in seconds, so 8:30 -> 510
 
 
# --------------------------------------------------------------------
# 7. The whole game: roster + events + clock syncs.
#
#    This object is what we save to disk and what the stats engine
#    reads. Keeping it in one place means saving is one line of code.
# --------------------------------------------------------------------
 
@dataclass
class Game:
    name: str = "Test game"
    players: list[Player] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    syncs: list[ClockSync] = field(default_factory=list)
    _next_id: int = 1
 
    # ---- roster ----
 
    def find_player(self, team: str, number: str) -> Optional[Player]:
        number = str(number).upper()
        for p in self.players:
            if p.team == team and p.number.upper() == number:
                return p
        return None
 
    def add_player(self, team: str, number: str, position: str = "",
                   note: str = "") -> Player:
        """Get the player, or create them if this is a new number."""
        existing = self.find_player(team, number)
        if existing:
            return existing
        player = Player(team=team, number=str(number).upper(),
                        position=position, note=note)
        self.players.append(player)
        return player
 
    def rename_player(self, team: str, old_number: str, new_number: str) -> None:
        """
        Turn placeholder "A" into the real "#17" everywhere at once:
        on the roster AND on every event already logged for them.
        """
        old_number = str(old_number).upper()
        new_number = str(new_number).upper()
        player = self.find_player(team, old_number)
        if not player:
            raise ValueError(f"No player {old_number} on team {team}")
        player.number = new_number
        player.confirmed = True
        for event in self.events:
            for ep in event.players:
                if ep.team == team and ep.number.upper() == old_number:
                    ep.number = new_number
 
    def roster(self, team: str) -> list[Player]:
        """Players on one team, numbers first, placeholders last."""
        def sort_key(p: Player):
            return (0, int(p.number)) if p.number.isdigit() else (1, 0, p.number)
        return sorted([p for p in self.players if p.team == team], key=sort_key)
 
    # ---- events ----
 
    def add_event(self, event: Event) -> Event:
        # Fail loudly on a typo. If "Entry" slips in instead of "ENTRY",
        # nothing downstream will ever find that event again, and you
        # will not notice until the numbers come out wrong.
        if event.code not in BY_CODE:
            raise ValueError(
                f"Unknown event code {event.code!r}. "
                f"Valid codes: {', '.join(sorted(BY_CODE))}"
            )
        event.id = self._next_id
        self._next_id += 1
        if not event.clock:
            event.clock = self.clock_at(event.t)
        event.period = self.period_at(event.t) or event.period
        # make sure everyone named in the event exists on the roster
        for ep in event.players:
            self.add_player(ep.team, ep.number)
        self.events.append(event)
        self.events.sort(key=lambda e: e.t)
        return event
 
    def delete_event(self, event_id: int) -> None:
        self.events = [e for e in self.events if e.id != event_id]
 
    def events_of(self, code: str, team: Optional[str] = None) -> list[Event]:
        out = [e for e in self.events if e.code == code]
        if team:
            out = [e for e in out if e.team == team]
        return sorted(out, key=lambda e: e.t)
 
    def last_event_time(self) -> float:
        return max((e.t for e in self.events), default=0.0)
 
    # ---- clock ----
 
    def _sync_before(self, t: float) -> Optional[ClockSync]:
        earlier = [s for s in self.syncs if s.t <= t + 0.001]
        return max(earlier, key=lambda s: s.t) if earlier else None
 
    def clock_at(self, t: float) -> str:
        """
        Estimate the game clock at video second t, counting down from the
        most recent sync point. Assumes the clock was running, so re-sync
        after every whistle to keep this honest.
        """
        sync = self._sync_before(t)
        if not sync:
            return ""
        left = max(0, sync.seconds_left - (t - sync.t))
        return f"{int(left // 60)}:{int(left % 60):02d}"
 
    def period_at(self, t: float) -> str:
        sync = self._sync_before(t)
        return sync.period if sync else "1"
 
    # ---- saving ----
 
    def to_dict(self) -> dict:
        return asdict(self)
 
    @staticmethod
    def from_dict(data: dict) -> "Game":
        game = Game(name=data.get("name", "Test game"),
                    _next_id=data.get("_next_id", 1))
        game.players = [Player(**p) for p in data.get("players", [])]
        game.syncs = [ClockSync(**s) for s in data.get("syncs", [])]
        for raw in data.get("events", []):
            raw = dict(raw)
            raw["players"] = [EventPlayer(**ep) for ep in raw.get("players", [])]
            game.events.append(Event(**raw))
        game.events.sort(key=lambda e: e.t)
        return game
 
 
# --------------------------------------------------------------------
# 8. Small time helper used all over the project.
# --------------------------------------------------------------------
 
def mmss(seconds: float, tenths: bool = False) -> str:
    """125.4 seconds -> '2:05.4' or '2:05'."""
    seconds = max(0.0, float(seconds))
    minutes = int(seconds // 60)
    rest = seconds - minutes * 60
    if tenths:
        return f"{minutes}:{rest:04.1f}"
    return f"{minutes}:{int(rest):02d}"