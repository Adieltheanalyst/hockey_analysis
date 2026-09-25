from pathlib import Path
from typing import Optional
 
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
 
from . import excel, stats, store
from .models import (EVENT_TYPES, TEAMS, ClockSync, Event, EventPlayer,
                     Game, mmss, qualifier_names)
 
 
HERE = Path(__file__).parent
WEB = HERE / "web"
GAME_FILE = Path("game.json")
OUTPUT_DIR = Path("output")
 
app = FastAPI(title="Rink Tag")
 
# The game lives in memory while the server runs, and is written to disk
# after every change. If the server dies you lose nothing.
game: Game = store.load(GAME_FILE)
 
 
def persist() -> None:
    store.save(game, GAME_FILE)
 
 
# --------------------------------------------------------------------
# What the browser sends us. Pydantic checks these shapes for us, so a
# malformed request is rejected before it can touch the game.
# --------------------------------------------------------------------
 
class PlayerIn(BaseModel):
    team: str
    number: str
    role: str = ""
 
 
class EventIn(BaseModel):
    t: float
    code: str
    team: str
    players: list[PlayerIn] = Field(default_factory=list)
    quals: list[str] = Field(default_factory=list)
    flagged: bool = False
    note: str = ""
    clip: str = ""
 
 
class SyncIn(BaseModel):
    t: float
    period: str
    clock: str                      # "8:30" as it reads on the scoreboard
 
 
class PlayerEdit(BaseModel):
    team: str
    number: str
    position: str = ""
    note: str = ""
    confirmed: Optional[bool] = None
 
 
class RenameIn(BaseModel):
    team: str
    old_number: str
    new_number: str
 
 
class NameIn(BaseModel):
    name: str
 
 
# --------------------------------------------------------------------
# Turning our objects into plain dictionaries for the browser.
# --------------------------------------------------------------------
 
def event_out(e: Event) -> dict:
    return {
        "id": e.id,
        "t": round(e.t, 2),
        "time": mmss(e.t, True),
        "clock": e.clock,
        "period": e.period,
        "code": e.code,
        "detail": qualifier_names(e.code, e.quals),
        "team": e.team,
        "players": [{"team": p.team, "number": p.number, "role": p.role}
                    for p in e.players],
        "flagged": e.flagged,
        "note": e.note,
    }
 
 
def state_out() -> dict:
    return {
        "name": game.name,
        "events": [event_out(e) for e in game.events],
        "players": {
            team: [{"number": p.number, "position": p.position,
                    "note": p.note, "confirmed": p.confirmed}
                   for p in game.roster(team)]
            for team in TEAMS
        },
        "syncs": [{"t": s.t, "period": s.period,
                   "clock": mmss(s.seconds_left)} for s in game.syncs],
    }
 
 
# --------------------------------------------------------------------
# The endpoints.
# --------------------------------------------------------------------
 
@app.get("/api/config")
def config() -> dict:
    """Hotkeys and teams, read straight out of models.py."""
    return {"events": EVENT_TYPES, "teams": TEAMS}
 
 
@app.get("/api/state")
def read_state() -> dict:
    return state_out()
 
 
@app.post("/api/name")
def set_name(body: NameIn) -> dict:
    game.name = body.name
    persist()
    return {"name": game.name}
 
 
@app.post("/api/event")
def add_event(body: EventIn) -> dict:
    event = Event(
        t=body.t, code=body.code, team=body.team,
        players=[EventPlayer(p.team, p.number.upper(), p.role)
                 for p in body.players],
        quals=body.quals, flagged=body.flagged,
        note=body.note, clip=body.clip,
    )
    try:
        game.add_event(event)        # this is where a bad code is rejected
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    persist()
    return event_out(event)
 
 
@app.delete("/api/event/{event_id}")
def delete_event(event_id: int) -> dict:
    before = len(game.events)
    game.delete_event(event_id)
    if len(game.events) == before:
        raise HTTPException(status_code=404, detail="No such event")
    persist()
    return {"deleted": event_id}
 
 
@app.post("/api/event/{event_id}/note")
def set_note(event_id: int, body: NameIn) -> dict:
    for event in game.events:
        if event.id == event_id:
            event.note = body.name
            persist()
            return event_out(event)
    raise HTTPException(status_code=404, detail="No such event")
 
 
@app.post("/api/sync")
def add_sync(body: SyncIn) -> dict:
    parts = body.clock.strip().split(":")
    if len(parts) != 2 or not all(p.strip().isdigit() for p in parts):
        raise HTTPException(status_code=400,
                            detail="Clock must look like 8:30")
    seconds = int(parts[0]) * 60 + int(parts[1])
    game.syncs.append(ClockSync(t=body.t, period=body.period,
                                seconds_left=seconds))
    game.syncs.sort(key=lambda s: s.t)
 
    # events logged after this point now have a better clock estimate
    for event in game.events:
        event.clock = game.clock_at(event.t)
        event.period = game.period_at(event.t)
 
    persist()
    return {"t": body.t, "period": body.period, "clock": mmss(seconds)}
 
 
@app.post("/api/player")
def upsert_player(body: PlayerEdit) -> dict:
    player = game.add_player(body.team, body.number)
    if body.position:
        player.position = body.position
    if body.note:
        player.note = body.note
    if body.confirmed is not None:
        player.confirmed = body.confirmed
    persist()
    return {"team": player.team, "number": player.number,
            "position": player.position, "note": player.note,
            "confirmed": player.confirmed}
 
 
@app.post("/api/player/rename")
def rename_player(body: RenameIn) -> dict:
    try:
        game.rename_player(body.team, body.old_number, body.new_number)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    persist()
    return state_out()
 
 
@app.get("/api/stats")
def live_stats() -> dict:
    """A small live view for the side panel while you work."""
    skaters, teams = stats.build(game)
    rows = []
    for (team, number), s in skaters.items():
        rows.append({
            "team": team, "number": number,
            "g": s.goals, "a": s.assists, "sog": s.shots_on_goal,
            "att": s.attempts, "fow": s.faceoffs_won, "fol": s.faceoffs_lost,
            "toi": s.toi, "shifts": s.shifts, "diff": s.differential,
        })
    rows.sort(key=lambda r: (r["team"], -r["g"], -r["sog"], r["number"]))
    return {
        "skaters": rows,
        "teams": {t: {"goals": v.goals, "sog": v.shots_on_goal,
                      "attempts": v.attempts, "chances": v.chances,
                      "give": v.giveaways, "take": v.takeaways}
                  for t, v in teams.items()},
        "goalies": [{"team": g.team, "shots": g.shots_against,
                     "saves": g.saves, "ga": g.goals_against,
                     "pct": round(g.save_pct, 3) if g.save_pct else None}
                    for g in stats.goalies(game)],
        "flagged": stats.flagged_summary(game),
        "onice": {team: stats.on_ice_at(game, team, game.last_event_time())
                  for team in TEAMS},
    }
 
 
@app.post("/api/export")
def export() -> dict:
    safe = "".join(c if c.isalnum() else "-" for c in game.name).strip("-")
    path = OUTPUT_DIR / f"{safe or 'game'}.xlsx"
    excel.build_workbook(game, path)
    return {"path": str(path.resolve()), "events": len(game.events)}
 
 
@app.post("/api/snapshot")
def snapshot() -> dict:
    path = store.snapshot(game)
    return {"path": str(path.resolve())}
 
 
# --------------------------------------------------------------------
# Serving the page itself.
#
# If this section is missing from your file, "/" returns 404 and the
# browser shows nothing. The print below runs when uvicorn imports this
# module, so the console tells you straight away whether the page was
# found.
# --------------------------------------------------------------------
 
PAGE = WEB / "index.html"
print(f"[rinktag] page: {PAGE}  (found: {PAGE.exists()})")
 
if not WEB.exists():
    WEB.mkdir(parents=True, exist_ok=True)
 
app.mount("/static", StaticFiles(directory=WEB), name="static")
 
 
@app.get("/health")
def health() -> dict:
    """Quick check that the server and the page file are both in place."""
    return {"ok": True, "page": str(PAGE), "page_found": PAGE.exists(),
            "events": len(game.events), "game_file": str(GAME_FILE.resolve())}
 
 
@app.get("/", include_in_schema=False)
def home():
    if not PAGE.exists():
        raise HTTPException(
            status_code=500,
            detail=(f"index.html is not at {PAGE}. Put the page there — "
                    f"the folder must be rinktag/web/index.html, spelled "
                    f"exactly like that."),
        )
    return FileResponse(PAGE)
 
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("rinktag.api:app", host="127.0.0.1", port=8000, reload=True)