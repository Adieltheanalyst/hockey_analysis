from dataclasses import dataclass, field ,asdict
from typing import Optional


TEAMS = {
    "by": {"name":"Black/Yellow","short": "B/Y"},
    "gr": {"name":"Green","short":"GRN"},
}

def other_teams(team: str)-> str:
    """Given one team key, return the other one."""
    return "gr" if team == "by" else "by"


EVENT_TYPES={
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

BY_CODE = {v["code"]: {**v, "key": k} for k,v in EVENT_TYPES.items()}

def qualifier_names(code:str, quals: list[str]) -> str:
    """Turn ['c'] on an ENTRY into the words 'controlled'."""
    definition = BY_CODE.get(code,{})
    lookup=definition.get("quals",{})
    return ", ".join(lookup.get(q,q) for q in quals)

@dataclass
class Player:
    team:str
    number:str
    position: str = ""
    note: str=""
    confirmed: bool = False

    def label(self) -> str:
        return f"#{self.number}"

@dataclass
class EventPlayer:
    team: str
    number: str
    role: str = ""

@dataclass
class Event:
    t: float
    code: str
    team: str
    players: list[EventPlayer] = field(default_factory=list)
    quals: list[str] = field(default_factory=list)
    period:str = "1"
    clock: str=""
    flagged:bool= False
    note:str =""
    clip: str=""
    id:int=0


    def first_player(self) -> Optional[EventPlayer]:
        """The player who did the thing. None for on-ice sets and notes."""

        return self.players[0] if self.players else None

    def numbers(self)-> list[str]:
        return [p.number for p in self.players]

    def has_qual(self,q:str)-> bool:
        return q in self.quals


@dataclass
class ClockSync:
    t:float
    period: str
    seconds_left : int


@dataclass
class Game:
    name:str = "Test game"
    players: list[Player] = field(default_factory=list)
    events: list[Event]= field(default_factory=list)
    syncs: list[ClockSync]=field(default_factory=list)

    _next_id: int =1

    def find_player(self, team:str, number:str) -> Optional[Player]:
        number=str(number).upper()
        for p in self.players:
            if p.team==team and p.number.upper() == number:
                return p
        return None

    def add_player(self,team:str, number:str, position:str="",
                   note: str = "") -> Player:
        existing = self.find_player(team,number)
        if existing:
            return existing
        player = Player(team=team, number=str(number).upper(),
                        position=position, note=note)
        self.players.append(player)
        return player

    def rename_player(self, team:str, old_number:str, new_number:str)-> None:

        old_number=str(old_number).upper()
        new_number=str(new_number).upper()
        player=self.find_player(team,old_number)
        if not player:
            raise ValueError(f"No player {old_number} on team {team}")
        player.number = new_number
        player.confirmed = True
        for event in self.events:
            for ep in event.players:
                if ep.team == team and ep.number.upper() == old_number:
                    ep.number = new_number

    def roster(self,team:str) -> list[Player]:
        """Players on one team, number first, placeholders last."""
        def sort_key(p:Player):
            return (0, int(p.number)) if p.number.isdigit() else (1,0,p.number)
        return sorted([p for p in self.players if p.team == team], key=sort_key)

    def add_event(self,event:Event)-> Event:
        event.id=self._next_id
        self._next_id += 1
        if not event.clock:
            event.clock = self.clock_at(event.t)
        event.period = self.period_at(event.t) or self.event.period

        for ep in event.players:
            self.add_player(ep.team,ep.number)
        self.events.append(event)
        self.events.sort(key=lambda e: e.t)
        return event

    def delete_event(self,event_id:int) -> None:
        self.events =[e for e in self.events if e.id != event_id]

    def events_of(self, code:str, team:Optional[str]=None)-> list[Event]:
        out = [e for e in self.events if e.code == code]
        if team:
            out =[e for e in out if e.team==team]
        return sorted(out,key=lambda e: e.t)

    def last_event_time(self)-> float:
        return max((e.t for e in self.events), default=0.0)

    def _sync_before(self, t: float)-> Optional[ClockSync]:
        earlier =[s for s in self.syncs if s.t <= t+0.001]
        return max(earlier,key=lambda s: s.t) if earlier else None

    def clock_at(self, t: float)-> str:



        sync=self._sync_before(t)
        if not sync:
            return ""
        left =max(0,sync.seconds_left -(t-sync.t))
        return f"{int(left//60)}:{int(left % 60):02d}"

    def period_at(self,t: float)-> str:
        sync = self._sync_before(t)
        return sync.period if sync else "1"

    def period_at(self,t:float)-> str:
        sync=self._sync_before(t)
        return sync.period if sync else "1"

    def to_dict(self)-> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict)-> "Game":
        game = Game(name=data.get("name","Test game"),
                    _next_id=data.get("_next_id",1))

        game.players=[Player(**p) for p in data.get("players",[])]
        game.syncs=[ClockSync(**s) for s in data.get("syncs",[])]
        for raw in data.get("events",[]):
            raw=dict(raw)
            raw["players"]= [EventPlayer(**ep) for ep in raw.get("players",[])]
            game.events.append(Event(**raw))
        game.events.sort(key=lambda e: e.t)
        return game


def mmss(seconds:float,tenths:bool=False) -> str:
    """125.4 seconds -> '2:05.4' or '2:05'."""
    seconds=max(0.0, float(seconds))
    minutes=int(seconds//60)
    rest = seconds-minutes *60
    if tenths:
        return f"{minutes}:{rest:04.1f}"
    return f"{minutes}: {int(rest):02d}"
