from pathlib import Path
from rinktag.models import Game, Event, EventPlayer, ClockSync
from rinktag import excel
 
game = Game(name="Worked example")
game.syncs.append(ClockSync(t=0.0, period="1", seconds_left=900))
 
def onice(t, team, numbers):
    game.add_event(Event(t=t, code="ONICE", team=team, players=[
        EventPlayer(team, n, "onice") for n in numbers.split()]))
 
def tag(t, code, team, number=None, quals=None, flagged=False, note=""):
    players = [EventPlayer(team, number)] if number else []
    game.add_event(Event(t=t, code=code, team=team, players=players,
                         quals=quals or [], flagged=flagged, note=note))
 
onice(0, "by", "11 22 33"); onice(0, "gr", "77 98 32")
tag(15, "SOG", "by", "11")
tag(22, "MISS", "by", "22")
tag(30, "ENTRY", "by", "11", quals=["c"])
tag(35, "PASS", "by", "11", quals=["k"])
tag(38, "PASS", "by", "22", flagged=True, note="could not see who received it")
tag(40, "CHANCE", "by", "22", quals=["d"])
game.add_event(Event(t=45, code="GOAL", team="by", players=[
    EventPlayer("by", "22", "scorer"), EventPlayer("by", "11", "assist1")]))
game.add_event(Event(t=50, code="FO", team="gr", players=[
    EventPlayer("gr", "77", "won"), EventPlayer("by", "33", "lost")]))
onice(60, "by", "44 55 66")
tag(70, "SOG", "gr", "98")
tag(80, "TAKE", "by", "44")
game.add_event(Event(t=90, code="GOAL", team="gr",
                     players=[EventPlayer("gr", "98", "scorer")]))
tag(100, "GIVE", "by", "55")
 
game.add_player("by", "1", position="G", note="goalie")
game.add_player("gr", "30", position="G")
 
out = excel.build_workbook(game, Path("output/worked-example.xlsx"))
print("written:", out)