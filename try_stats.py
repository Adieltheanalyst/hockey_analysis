from rinktag.models import Game, Event, EventPlayer, ClockSync, mmss, TEAMS
from rinktag import stats
 
 
game = Game(name="Worked example")
game.syncs.append(ClockSync(t=0.0, period="1", seconds_left=900))
 
 
def onice(t, team, numbers):
    game.add_event(Event(t=t, code="ONICE", team=team, players=[
        EventPlayer(team, n, "onice") for n in numbers.split()
    ]))
 
 
def tag(t, code, team, number=None, quals=None, role=""):
    players = [EventPlayer(team, number, role)] if number else []
    game.add_event(Event(t=t, code=code, team=team,
                         players=players, quals=quals or []))
 
 
# --- first line out, both teams ---
onice(0, "by", "11 22 33")
onice(0, "gr", "77 98 32")
 
tag(15, "SOG", "by", "11")
tag(22, "MISS", "by", "22")
tag(30, "ENTRY", "by", "11", quals=["c"])
tag(35, "PASS", "by", "11", quals=["k"])       # completed
tag(38, "PASS", "by", "22")                    # not completed
 
# a goal for B/Y at 45s: #22 scores, #11 assists
game.add_event(Event(t=45, code="GOAL", team="by", players=[
    EventPlayer("by", "22", "scorer"),
    EventPlayer("by", "11", "assist1"),
]))
 
# faceoff after the goal: green #77 wins it, B/Y #33 loses it
game.add_event(Event(t=50, code="FO", team="gr", players=[
    EventPlayer("gr", "77", "won"),
    EventPlayer("by", "33", "lost"),
]))
 
# --- line change at 60s for B/Y only ---
onice(60, "by", "44 55 66")
tag(70, "SOG", "gr", "98")
tag(80, "TAKE", "by", "44")
 
# green scores at 90s, against B/Y's second line
game.add_event(Event(t=90, code="GOAL", team="gr", players=[
    EventPlayer("gr", "98", "scorer"),
]))
tag(100, "GIVE", "by", "55")
 
 
skaters, teams = stats.build(game)
 
print(f"\n{game.name} — {len(game.events)} events\n")
 
# ------------------------------------------------------------------
print("HOW TIME ON ICE IS WORKED OUT")
for team in TEAMS:
    sets = game.events_of("ONICE", team)
    for i, s in enumerate(sets):
        stop = sets[i + 1].t if i + 1 < len(sets) else game.last_event_time()
        print(f"  {TEAMS[team]['short']:<4} {mmss(s.t, True):>6} -> {mmss(stop, True):>6} "
              f"= {stop - s.t:5.1f}s to {' '.join('#' + n for n in s.numbers())}")
print(f"  (play is treated as ending at the last event, {mmss(game.last_event_time(), True)})\n")
 
# ------------------------------------------------------------------
print("SKATERS")
header = f"{'':<5}{'PL':<5}{'G':>2}{'A':>3}{'P':>3}{'SOG':>5}{'ATT':>5}{'FOW':>5}{'FOL':>5}{'TOI':>7}{'SH':>4}{'+/-':>5}"
print(header)
for (team, number), s in sorted(skaters.items()):
    print(f"{TEAMS[team]['short']:<5}{'#' + number:<5}{s.goals:>2}{s.assists:>3}{s.points:>3}"
          f"{s.shots_on_goal:>5}{s.attempts:>5}{s.faceoffs_won:>5}{s.faceoffs_lost:>5}"
          f"{s.toi:>7}{s.shifts:>4}{s.differential:>+5}")
 
# ------------------------------------------------------------------
print("\nTEAM TOTALS")
print(f"{'':<22}{'B/Y':>6}{'GRN':>6}")
rows = [("Goals", "goals"), ("Shots on goal", "shots_on_goal"),
        ("Shot attempts", "attempts"), ("Faceoffs won", "faceoffs_won"),
        ("Entries controlled", "entries_controlled"),
        ("Pass attempts", "passes"), ("Passes completed", "passes_completed"),
        ("Giveaways", "giveaways"), ("Takeaways", "takeaways")]
for label, attr in rows:
    print(f"{label:<22}{getattr(teams['by'], attr):>6}{getattr(teams['gr'], attr):>6}")
 
# ------------------------------------------------------------------
print("\nGOALIES")
for g in stats.goalies(game):
    pct = f"{g.save_pct:.3f}" if g.save_pct is not None else "-"
    print(f"  {TEAMS[g.team]['name']:<14} {g.names:<16} "
          f"shots {g.shots_against}  saves {g.saves}  GA {g.goals_against}  sv% {pct}")
 
# ------------------------------------------------------------------
print("\nCHECK THE ARITHMETIC YOURSELF")
by11 = skaters[("by", "11")]
print(f"  #11 was on from 0.0s to 60.0s        -> TOI {by11.toi}, {by11.shifts} shift")
print(f"  #11 shot once and scored none        -> SOG {by11.shots_on_goal}, goals {by11.goals}")
print(f"  #11 was on for the goal at 45s       -> on-ice for {by11.on_ice_for}, "
      f"against {by11.on_ice_against}, differential {by11.differential:+d}")
by55 = skaters[("by", "55")]
print(f"  #55 came on at 60s, green scored 90s -> differential {by55.differential:+d}")
gr98 = skaters[("gr", "98")]
print(f"  green #98 scored and shot once       -> SOG {gr98.shots_on_goal} "
      f"(one shot + one goal), goals {gr98.goals}")