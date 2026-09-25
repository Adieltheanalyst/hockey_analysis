from dataclasses import dataclass, field
from typing import Optional
 
from .models import Game, Event, TEAMS, mmss, other_teams
 
 
# --------------------------------------------------------------------
# 1. Who was on the ice at a given moment?
#
#    Every ONICE event is a snapshot: "these players are out there now".
#    To answer "who was on at second 412?", find the most recent snapshot
#    for that team at or before 412.
# --------------------------------------------------------------------
 
def on_ice_at(game: Game, team: str, t: float) -> list[str]:
    """The jersey numbers on the ice for `team` at video second `t`."""
    snapshots = [e for e in game.events
                 if e.code == "ONICE" and e.team == team and e.t <= t + 0.001]
    if not snapshots:
        return []
    latest = max(snapshots, key=lambda e: e.t)
    return latest.numbers()
 
 
# --------------------------------------------------------------------
# 2. Time on ice and shift counts.
#
#    Walk the on-ice snapshots for one team in order. Each snapshot runs
#    until the next one. Everyone in it gets credited with that stretch.
#
#    A player starts a new SHIFT when they appear in a snapshot and were
#    not in the one before it. So a player who stays out across two
#    snapshots gets one shift, not two.
# --------------------------------------------------------------------
 
@dataclass
class Ice:
    seconds: float = 0.0
    shifts: int = 0
 
 
def ice_time(game: Game, end_time: Optional[float] = None) -> dict:
    """
    Returns {(team, number): Ice}.
 
    `end_time` closes off the last shift. Default is the time of the last
    event you logged, which is the best guess we have for the end of play.
    """
    if end_time is None:
        end_time = game.last_event_time()
 
    out: dict[tuple[str, str], Ice] = {}
 
    for team in TEAMS:
        snapshots = game.events_of("ONICE", team)
        previous: set[str] = set()
 
        for index, snapshot in enumerate(snapshots):
            # this snapshot lasts until the next one, or until play ends
            if index + 1 < len(snapshots):
                stop = snapshots[index + 1].t
            else:
                stop = max(end_time, snapshot.t)
            duration = max(0.0, stop - snapshot.t)
 
            current = set(snapshot.numbers())
            for number in current:
                entry = out.setdefault((team, number), Ice())
                entry.seconds += duration
                if number not in previous:      # they just came on
                    entry.shifts += 1
            previous = current
 
    return out
 
 
# --------------------------------------------------------------------
# 3. One player's line in the spreadsheet.
# --------------------------------------------------------------------
 
@dataclass
class Skater:
    team: str
    number: str
    position: str = ""
 
    goals: int = 0
    assists: int = 0
    shots_on_goal: int = 0      # includes their goals
    missed: int = 0
    blocked: int = 0
    chances: int = 0
    high_danger: int = 0
    faceoffs_won: int = 0
    faceoffs_lost: int = 0
    entries_controlled: int = 0
    entries_dumped: int = 0
    exits_controlled: int = 0
    exits_cleared: int = 0
    giveaways: int = 0
    takeaways: int = 0
    passes: int = 0
    passes_completed: int = 0
    penalties: int = 0
 
    toi_seconds: float = 0.0
    shifts: int = 0
    on_ice_for: int = 0         # goals scored while they were out there
    on_ice_against: int = 0
 
    # ---- numbers worked out from the ones above ----
 
    @property
    def points(self) -> int:
        return self.goals + self.assists
 
    @property
    def attempts(self) -> int:
        """Every shot directed at the net: on goal, missed or blocked."""
        return self.shots_on_goal + self.missed + self.blocked
 
    @property
    def differential(self) -> int:
        return self.on_ice_for - self.on_ice_against
 
    @property
    def faceoff_pct(self) -> Optional[float]:
        total = self.faceoffs_won + self.faceoffs_lost
        return self.faceoffs_won / total if total else None
 
    @property
    def pass_pct(self) -> Optional[float]:
        return self.passes_completed / self.passes if self.passes else None
 
    @property
    def toi(self) -> str:
        return mmss(self.toi_seconds)
 
 
@dataclass
class TeamTotals:
    team: str
    goals: int = 0
    shots_on_goal: int = 0
    missed: int = 0
    blocked: int = 0
    chances: int = 0
    high_danger: int = 0
    faceoffs_won: int = 0
    faceoffs_lost: int = 0
    entries_controlled: int = 0
    entries_dumped: int = 0
    exits_controlled: int = 0
    exits_cleared: int = 0
    giveaways: int = 0
    takeaways: int = 0
    passes: int = 0
    passes_completed: int = 0
    penalties: int = 0
 
    @property
    def attempts(self) -> int:
        return self.shots_on_goal + self.missed + self.blocked
 
 
# --------------------------------------------------------------------
# 4. The main pass over the events.
#
#    One loop, one event at a time. For each event we ask: who gets
#    credited, and which counter goes up? Everything else in the project
#    reads the result of this function.
# --------------------------------------------------------------------
 
def build(game: Game, end_time: Optional[float] = None):
    """
    Returns (skaters, teams) where
        skaters is {(team, number): Skater}
        teams   is {team: TeamTotals}
    """
    skaters: dict[tuple[str, str], Skater] = {}
    teams = {team: TeamTotals(team=team) for team in TEAMS}
 
    def skater(team: str, number: str) -> Skater:
        key = (team, number)
        if key not in skaters:
            player = game.find_player(team, number)
            skaters[key] = Skater(team=team, number=number,
                                  position=player.position if player else "")
        return skaters[key]
 
    for event in game.events:
        total = teams[event.team]
        actor = event.first_player()
 
        if event.code == "GOAL":
            # a goal is also a shot on goal, for the team and the scorer
            total.goals += 1
            total.shots_on_goal += 1
            for person in event.players:
                line = skater(person.team, person.number)
                if person.role == "scorer":
                    line.goals += 1
                    line.shots_on_goal += 1
                else:
                    line.assists += 1
 
        elif event.code == "SOG":
            total.shots_on_goal += 1
            if actor:
                skater(actor.team, actor.number).shots_on_goal += 1
 
        elif event.code == "MISS":
            total.missed += 1
            if actor:
                skater(actor.team, actor.number).missed += 1
 
        elif event.code == "BLOCK":
            total.blocked += 1
            if actor:
                skater(actor.team, actor.number).blocked += 1
 
        elif event.code == "CHANCE":
            total.chances += 1
            if event.has_qual("d"):
                total.high_danger += 1
            if actor:
                line = skater(actor.team, actor.number)
                line.chances += 1
                if event.has_qual("d"):
                    line.high_danger += 1
 
        elif event.code == "FO":
            # a faceoff names two players on opposite teams
            for person in event.players:
                line = skater(person.team, person.number)
                if person.role == "lost":
                    line.faceoffs_lost += 1
                    teams[person.team].faceoffs_lost += 1
                else:
                    line.faceoffs_won += 1
                    teams[person.team].faceoffs_won += 1
 
        elif event.code == "ENTRY":
            dumped = event.has_qual("d")
            if dumped:
                total.entries_dumped += 1
            else:
                total.entries_controlled += 1
            if actor:
                line = skater(actor.team, actor.number)
                if dumped:
                    line.entries_dumped += 1
                else:
                    line.entries_controlled += 1
 
        elif event.code == "EXIT":
            cleared = event.has_qual("w")
            if cleared:
                total.exits_cleared += 1
            else:
                total.exits_controlled += 1
            if actor:
                line = skater(actor.team, actor.number)
                if cleared:
                    line.exits_cleared += 1
                else:
                    line.exits_controlled += 1
 
        elif event.code == "GIVE":
            total.giveaways += 1
            if actor:
                skater(actor.team, actor.number).giveaways += 1
 
        elif event.code == "TAKE":
            total.takeaways += 1
            if actor:
                skater(actor.team, actor.number).takeaways += 1
 
        elif event.code == "PASS":
            total.passes += 1
            completed = event.has_qual("k")
            if completed:
                total.passes_completed += 1
            if actor:
                line = skater(actor.team, actor.number)
                line.passes += 1
                if completed:
                    line.passes_completed += 1
 
        elif event.code == "PEN":
            total.penalties += 1
            if actor:
                skater(actor.team, actor.number).penalties += 1
 
        # ONICE and NOTE add no counts of their own; ONICE is used below
 
    # ---- on-ice goal differential ----
    for goal in game.events_of("GOAL"):
        for team in TEAMS:
            for number in on_ice_at(game, team, goal.t):
                line = skater(team, number)
                if team == goal.team:
                    line.on_ice_for += 1
                else:
                    line.on_ice_against += 1
 
    # ---- ice time and shifts ----
    for (team, number), ice in ice_time(game, end_time).items():
        line = skater(team, number)
        line.toi_seconds = ice.seconds
        line.shifts = ice.shifts
 
    # ---- make sure every rostered player has a row, even an empty one ----
    for player in game.players:
        skater(player.team, player.number)
 
    return skaters, teams
 
 
# --------------------------------------------------------------------
# 5. Goalies.
#
#    We do not tag saves. A save is simply a shot on goal against that
#    did not go in, so tagging it as well would double-count. Working it
#    out instead means the goalie numbers can never disagree with the
#    skater numbers.
# --------------------------------------------------------------------
 
@dataclass
class Goalie:
    team: str
    names: str = ""
    shots_against: int = 0
    goals_against: int = 0
 
    @property
    def saves(self) -> int:
        return self.shots_against - self.goals_against
 
    @property
    def save_pct(self) -> Optional[float]:
        return self.saves / self.shots_against if self.shots_against else None
 
 
def goalies(game: Game) -> list[Goalie]:
    out = []
    for team in TEAMS:
        opponent = other_teams(team)
        shots = 0
        goals = 0
        for event in game.events:
            if event.team != opponent:
                continue
            if event.code in ("SOG", "GOAL"):
                shots += 1          # a goal is a shot on goal
            if event.code == "GOAL":
                goals += 1
        keepers = [p.label() for p in game.roster(team) if p.position == "G"]
        out.append(Goalie(team=team,
                          names=", ".join(keepers) or "not identified",
                          shots_against=shots,
                          goals_against=goals))
    return out
 
 
# --------------------------------------------------------------------
# 6. Counting what you could not see.
#
#    Flagged events are the ones you could not read with confidence.
#    Reporting how many there are, per statistic, is what separates an
#    honest dataset from a guessed one.
# --------------------------------------------------------------------
 
def flagged_summary(game: Game) -> dict:
    """{code: (flagged_count, total_count)} for every code you used."""
    out: dict[str, list[int]] = {}
    for event in game.events:
        row = out.setdefault(event.code, [0, 0])
        row[1] += 1
        if event.flagged:
            row[0] += 1
    return {code: tuple(counts) for code, counts in out.items()}
 
 
# --------------------------------------------------------------------
# 7. The definitions that go in the spreadsheet.
#    Andrew asked for consistent definitions. These are them, and they
#    live next to the code that implements them so the two cannot drift.
# --------------------------------------------------------------------
 
DEFINITIONS = [
    ("Shot on goal",
     "A shot that would enter the net if the goalie did not stop it. "
     "Goals are counted as shots on goal."),
    ("Shot attempt",
     "Every shot directed at the net: on goal, missed and blocked."),
    ("Scoring chance",
     "An unblocked attempt from the home-plate area in front of the net, "
     "or any clear opportunity from close range."),
    ("High-danger chance",
     "A scoring chance from the inner slot, off a rebound, or created by "
     "a pass across the slot."),
    ("Assist",
     "Up to two players who touched the puck before the goal without the "
     "other team gaining control in between."),
    ("Faceoff",
     "Credited to the player whose team gains clear possession from the "
     "draw. The losing player is recorded where the number is readable."),
    ("Zone entry - controlled",
     "The puck crosses the offensive blue line carried or passed with "
     "possession retained."),
    ("Zone entry - dump-in",
     "The puck is shot or chipped into the offensive zone without "
     "possession."),
    ("Zone exit - controlled",
     "The puck leaves the defensive zone with possession retained."),
    ("Zone exit - clear/chip",
     "The puck leaves the defensive zone without possession retained, "
     "including icings."),
    ("Giveaway",
     "An unforced loss of possession: a missed pass, a failed clear, "
     "losing the puck under no real pressure."),
    ("Takeaway",
     "Possession taken from an opponent by stick check, body position "
     "or intercepting a pass."),
    ("Pass attempt / completed",
     "A deliberate pass to a teammate; completed when that teammate "
     "gains control of the puck."),
    ("On-ice set",
     "The players recorded on the ice after each line change. Time on "
     "ice, shift counts and on-ice goal differential all come from these."),
    ("Time on ice",
     "The sum of the stretches in which a player appears in the on-ice "
     "set. An estimate, limited by how clearly numbers read on video."),
    ("Shift",
     "Counted when a player appears in an on-ice set having not been in "
     "the previous one."),
    ("On-ice goal differential",
     "Goals for minus goals against while the player was on the ice. "
     "Not adjusted for power play or short-handed situations, because "
     "strength cannot be judged reliably from this camera angle."),
    ("Goalie save percentage",
     "Saves divided by shots on goal against, where goals count as "
     "shots on goal. Saves are worked out, not tagged separately."),
    ("Flagged",
     "An event the video did not allow a confident read of. Flagged "
     "events are recorded and counted, never guessed."),
]