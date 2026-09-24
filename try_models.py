from rinktag.models import Game, Event, EventPlayer,ClockSync,mmss,qualifier_names

game=Game(name="Black/Yellow vs Green - test")

game.syncs.append(ClockSync(t=0.0, period="1", seconds_left=900))

game.add_event(Event(t=0.0, code="ONICE", team="by", players=[
    EventPlayer("by", "11", "onice"),
    EventPlayer("by","22", "onice"),
    EventPlayer("by","A","onice"), # number not readable yet 
]))
game.add_event(Event(t=0.0, code="ONICE", team="gr", players=[
    EventPlayer("gr", "77", "onice"),
    EventPlayer("gr", "98", "onice"),
]))

game.add_event(Event(t=42.0, code="SOG", team="by",
                     players=[EventPlayer("by", "11")]))

game.add_event(Event(t=55.5, code="ENTRY", team="by", quals=["c"],
                     players=[EventPlayer("by", "A")],
                     flagged=True, note="screened by the referee"))

game.add_event(Event(t=70.0, code="GOAL", team="by", players=[
    EventPlayer("by", "22", "scorer"),
    EventPlayer("by", "11", "assist1"),
]))
 
# --- a faceoff won by #77, lost by #22 ---
game.add_event(Event(t=75.0, code="FO", team="gr", players=[
    EventPlayer("gr", "77", "won"),
    EventPlayer("by", "22", "lost"),
]))
 
 
print(f"\n{game.name}")
print(f"{len(game.events)} events, {len(game.players)} players known\n")
 
print("EVENT LOG")
print(f"{'video':>7}  {'clock':>5}  {'event':<7} {'team':<4} {'players':<16} note")
for e in game.events:
    quals = qualifier_names(e.code, e.quals)
    tail = " ".join(x for x in [quals, ("FLAGGED" if e.flagged else ""), e.note] if x)
    print(f"{mmss(e.t, True):>7}  {e.clock:>5}  {e.code:<7} {e.team:<4} "
          f"{' '.join('#' + n for n in e.numbers()):<16} {tail}")
 
print("\nROSTER before the rename")
for p in game.roster("by"):
    print("   B/Y", p.label())
 
# --- later in the game you finally read the jersey: A is actually 17 ---
game.rename_player("by", "A", "17")
 
print("\nROSTER after renaming A -> 17")
for p in game.roster("by"):
    print("   B/Y", p.label())
 
print("\nThe entry event now reads:",
      [f"#{n}" for n in game.events_of("ENTRY")[0].numbers()])
 
# --- saving and reloading gives back the same thing ---
copy = Game.from_dict(game.to_dict())
print("\nRound trip through a dictionary kept",
      len(copy.events), "events and", len(copy.players), "players")
print("Clock at 70s:", copy.clock_at(70.0), "in period", copy.period_at(70.0))