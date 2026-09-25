rom fastapi.testclient import TestClient
from rinktag.api import app
 
c = TestClient(app)
 
print("config:", list(c.get("/api/config").json()["events"])[:5], "...")
 
# clock sync, then a small sequence
c.post("/api/sync", json={"t":0, "period":"1", "clock":"15:00"})
c.post("/api/event", json={"t":0, "code":"ONICE", "team":"by",
    "players":[{"team":"by","number":n,"role":"onice"} for n in ["11","22","33"]]})
c.post("/api/event", json={"t":0, "code":"ONICE", "team":"gr",
    "players":[{"team":"gr","number":n,"role":"onice"} for n in ["77","98"]]})
r = c.post("/api/event", json={"t":15, "code":"SOG", "team":"by",
    "players":[{"team":"by","number":"11"}]})
print("added:", r.json()["code"], r.json()["time"], "clock", r.json()["clock"])
 
c.post("/api/event", json={"t":45, "code":"GOAL", "team":"by", "players":[
    {"team":"by","number":"22","role":"scorer"},{"team":"by","number":"A","role":"assist1"}]})
c.post("/api/event", json={"t":50, "code":"ENTRY", "team":"by", "quals":["c"],
    "players":[{"team":"by","number":"A"}], "flagged":True, "note":"screened"})
 
bad = c.post("/api/event", json={"t":60, "code":"Entry", "team":"by"})
print("typo rejected:", bad.status_code, bad.json()["detail"][:44], "...")
 
c.post("/api/player/rename", json={"team":"by","old_number":"A","new_number":"17"})
state = c.get("/api/state").json()
print("after rename, entry event players:",
      [p["number"] for e in state["events"] if e["code"]=="ENTRY" for p in e["players"]])
 
stats = c.get("/api/stats").json()
print("live teams:", stats["teams"])
print("on ice:", stats["onice"])
print("flagged:", stats["flagged"])
 
ev_id = [e["id"] for e in state["events"] if e["code"]=="SOG"][0]
print("delete:", c.delete(f"/api/event/{ev_id}").json())
 
print("export:", c.post("/api/export").json())
print("page loads:", c.get("/").status_code, len(c.get("/").content), "bytes")