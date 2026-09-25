from pathlib import Path
from typing import Optional 
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font,PatternFill,Side
from openpyxl.utils import get_column_letter
from . import stats
from .models import Game,TEAMS,mmss,other_teams,qualifier_names

FONT = "Arial"
HEAD_FILL= PatternFill("solid",fgColor="1f3B54")
HEAD_FONT = Font(name=FONT, bold=True,color="FFFFFF", size=10)
BODY_FONT= Font(name=FONT, size=10)
NOTE_FONT= Font(name=FONT, size=9,italic=True, color="666666")
THIN = Side(style="thin", color="BFBFBF")
BOX= Border(bottom=THIN)


CREDIT_COLUMNS = ["Event", "Video time", "Clock", "Period",
                  "Team","Player", "Stat", "Flagged", "Note"]

COL_TEAM = "E"
COL_PLAYER = "F"
COL_STAT = "G"

def credit_rows(game: Game)-> list[list]:
    rows: list[list] = []
    def add(event,team, number,stat):
        rows.append([
            event.id, mmss(event.t, True), event.clock, event.period,
            TEAMS[team]["short"], f"#{number}", stat,
        "yes" if event.flagged else "", event.note,
        ])
    for e in game.events:
        actor=e.first_player()
        if e.code == "GOAL":
            for person in e.players:
                if person.role == "scorer":
                    add(e, person.team, person.number, "GOAL")
                    add(e, person.team, person.number, "SOG")
                else:
                    add(e, person.team, person.number, "ASSIST")
        elif e.code in ("SOG", "MISS","BLOCK","GIVE","TAKE","PEN"):
            if actor:
                add(e,actor.team, actor.number, e.code)

        elif e.code == "CHANCE":
            if actor:
                add(e,actor.team,actor.number, "CHANCE")
                if e.has_qual("d"):
                    add(e, actor.team, actor.number, "CHANCE_HD")
        elif e.code == "FO":
            for person in e.players:
                stat = "FO_L" if person.role == "lost" else "FO_W"
                add(e, person.team, person.number, stat)
 
        elif e.code == "ENTRY":
            if actor:
                add(e, actor.team, actor.number,
                    "ENTRY_D" if e.has_qual("d") else "ENTRY_C")
 
        elif e.code == "EXIT":
            if actor:
                add(e, actor.team, actor.number,
                    "EXIT_CL" if e.has_qual("w") else "EXIT_C")
 
        elif e.code == "PASS":
            if actor:
                add(e, actor.team, actor.number, "PASS")
                if e.has_qual("k"):
                    add(e, actor.team, actor.number, "PASS_C")

    return rows

SKATER_COLUMNS = [
    ("Team",               "value",   lambda s: TEAMS[s.team]["short"]),
    ("Player",             "value",   lambda s: f"#{s.number}"),
    ("Pos",                "value",   lambda s: s.position),
    ("G",                  "count",   "GOAL"),
    ("A",                  "count",   "ASSIST"),
    ("P",                  "formula", "={G}{row}+{A}{row}"),
    ("SOG",                "count",   "SOG"),
    ("Missed",             "count",   "MISS"),
    ("Blocked",            "count",   "BLOCK"),
    ("Attempts",           "formula", "={SOG}{row}+{Missed}{row}+{Blocked}{row}"),
    ("Chances",            "count",   "CHANCE"),
    ("High danger",        "count",   "CHANCE_HD"),
    ("FO won",             "count",   "FO_W"),
    ("FO lost",            "count",   "FO_L"),
    ("FO %",               "formula",
     '=IFERROR({FO won}{row}/({FO won}{row}+{FO lost}{row}),"")'),
    ("Entries controlled", "count",   "ENTRY_C"),
    ("Entries dumped",     "count",   "ENTRY_D"),
    ("Exits controlled",   "count",   "EXIT_C"),
    ("Exits cleared",      "count",   "EXIT_CL"),
    ("Giveaways",          "count",   "GIVE"),
    ("Takeaways",          "count",   "TAKE"),
    ("Pass attempts",      "count",   "PASS"),
    ("Passes completed",   "count",   "PASS_C"),
    ("Pass %",             "formula",
     '=IFERROR({Passes completed}{row}/{Pass attempts}{row},"")'),
    ("Penalties",          "count",   "PEN"),
    ("TOI",                "value",   lambda s: s.toi),
    ("TOI (seconds)",      "value",   lambda s: round(s.toi_seconds, 1)),
    ("Shifts",             "value",   lambda s: s.shifts),
    ("On ice for",         "value",   lambda s: s.on_ice_for),
    ("On ice against",     "value",   lambda s: s.on_ice_against),
    ("Goal differential",  "formula", "={On ice for}{row}-{On ice against}{row}"),
]
 
TEAM_ROWS = [
    ("Goals",              "count",   "GOAL"),
    ("Shots on goal",      "count",   "SOG"),
    ("Missed",             "count",   "MISS"),
    ("Blocked",            "count",   "BLOCK"),
    ("Shot attempts",      "sum",     ("Shots on goal", "Missed", "Blocked")),
    ("Scoring chances",    "count",   "CHANCE"),
    ("High-danger chances", "count",  "CHANCE_HD"),
    ("Faceoffs won",       "count",   "FO_W"),
    ("Faceoffs lost",      "count",   "FO_L"),
    ("Entries controlled", "count",   "ENTRY_C"),
    ("Entries dumped",     "count",   "ENTRY_D"),
    ("Exits controlled",   "count",   "EXIT_C"),
    ("Exits cleared",      "count",   "EXIT_CL"),
    ("Giveaways",          "count",   "GIVE"),
    ("Takeaways",          "count",   "TAKE"),
    ("Pass attempts",      "count",   "PASS"),
    ("Passes completed",   "count",   "PASS_C"),
    ("Penalties",          "count",   "PEN"),
]

def _header(ws, labels: list[str], row: int = 1) -> None:
    for column, label in enumerate(labels, start=1):
        cell = ws.cell(row=row, column=column, value=label)
        cell.font = HEAD_FONT
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center",
                                   wrap_text=True)
    ws.freeze_panes=f"A{row+1}"

def _widths(ws, widths:dict) -> None:
    for column, width in widths.items():
        ws.column_dimensions[column].width=width


def _plain(ws,first_row: int = 2) -> None:
    for row in ws.iter_rows(min_row=first_row):
        for cell in row:
            cell.font = BODY_FONT
            cell.border = BOX

def _note(ws, row: int, text: str) -> None:
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = NOTE_FONT

def _countifs(stat: str, team_cell: Optional[str] = None,
              player_cell: Optional[str] = None) -> str:
    parts = [f"Credits!${COL_STAT}:${COL_STAT},\"{stat}\""]
    if team_cell:
        parts.insert(0, f"Credits!${COL_TEAM}:${COL_TEAM},{team_cell}")
    if player_cell:
        parts.insert(1, f"Credits!${COL_PLAYER}:${COL_PLAYER},{player_cell}")
    return "=COUNTIFS(" + ",".join(parts) + ")"

def _sheet_definitions(wb, game: Game) -> None:
    ws = wb.create_sheet("Definitions")
    _header(ws, ["Statistic", "Definition used for this game"])
    for statistic, meaning in stats.DEFINITIONS:
        ws.append([statistic, meaning])
    _plain(ws)
    for row in ws.iter_rows(min_row=2, min_col=2, max_col=2):
        row[0].alignment = Alignment(wrap_text=True, vertical="top")
    _widths(ws, {"A": 26, "B": 92})
    last = ws.max_row + 2
    _note(ws, last,
          "Every number in this workbook comes from the Event log and the "
          "Credits sheet. Summary cells are live formulas, so deleting a "
          "disputed event updates the totals.")
    _note(ws, last + 1,
          "Time on ice, shift counts and on-ice goal differential are "
          "calculated from the on-ice sets and written as values.")

def _sheet_credits(wb, game: Game) -> None:
    ws = wb.create_sheet("Credits")
    _header(ws, CREDIT_COLUMNS)
    for row in credit_rows(game):
        ws.append(row)
    _plain(ws)
    _widths(ws, {"A": 8, "B": 11, "C": 8, "D": 7, "E": 7,
                 "F": 9, "G": 12, "H": 9, "I": 40})
    ws.auto_filter.ref = f"A1:I{max(ws.max_row, 1)}"


def _sheet_event_log(wb, game: Game) -> None:
    ws = wb.create_sheet("Event log")
    _header(ws, ["Event", "Video time", "Clock", "Period", "Event type",
                 "Detail", "Team", "Players", "Flagged", "Note", "Clip"])
    for e in game.events:
        players = " ".join(
            f"#{p.number}" + (f" ({p.role})" if p.role and p.role != "onice" else "")
            for p in e.players
        )
        ws.append([e.id, mmss(e.t, True), e.clock, e.period, e.code,
                   qualifier_names(e.code, e.quals), TEAMS[e.team]["short"],
                   players, "yes" if e.flagged else "", e.note, e.clip])
    _plain(ws)
    _widths(ws, {"A": 8, "B": 11, "C": 8, "D": 7, "E": 11, "F": 14,
                 "G": 7, "H": 34, "I": 9, "J": 34, "K": 18})
    ws.auto_filter.ref = f"A1:K{max(ws.max_row, 1)}"
 
 
def _sheet_team(wb, game: Game) -> None:
    ws = wb.create_sheet("Team totals")
    _header(ws, ["Statistic", TEAMS["by"]["name"], TEAMS["gr"]["name"]])
    row_of: dict[str, int] = {}
 
    for index, (label, kind, spec) in enumerate(TEAM_ROWS, start=2):
        ws.cell(row=index, column=1, value=label)
        row_of[label] = index
        for offset, team in enumerate(("by", "gr")):
            column = get_column_letter(2 + offset)
            if kind == "count":
                short = TEAMS[team]["short"]
                value = _countifs(spec, team_cell=f'"{short}"')
            else:  # a sum of other rows in the same column
                value = "=" + "+".join(f"{column}{row_of[name]}" for name in spec)
            ws.cell(row=index, column=2 + offset, value=value)
 
    _plain(ws)
    _widths(ws, {"A": 24, "B": 16, "C": 16})
    last = ws.max_row + 2
    _note(ws, last, "Every cell is a COUNTIFS over the Credits sheet — "
                    "click one to see how it is built.")

def _sheet_skaters(wb, game: Game, skaters: dict) -> None:
    ws = wb.create_sheet("Skaters")
    labels = [c[0] for c in SKATER_COLUMNS]
    _header(ws, labels)
 
    # which column letter each label lives in, so formulas can name them
    letter_of = {label: get_column_letter(i + 1)
                 for i, label in enumerate(labels)}
 
    def sort_key(item):
        (team, number), _ = item
        digits = number.isdigit()
        return (0 if team == "by" else 1, 0 if digits else 1,
                int(number) if digits else 0, number)
 
    row = 2
    for (team, number), skater in sorted(skaters.items(), key=sort_key):
        short = TEAMS[team]["short"]
        for index, (label, kind, spec) in enumerate(SKATER_COLUMNS, start=1):
            if kind == "count":
                value = _countifs(spec, team_cell=f'"{short}"',
                                  player_cell=f'"#{number}"')
            elif kind == "formula":
                value = spec.format(row=row, **letter_of)
            else:
                value = spec(skater)
            ws.cell(row=row, column=index, value=value)
        row += 1
 
    _plain(ws)
    for column in ("O", "X"):          # FO % and Pass %
        for cell in ws[column][1:]:
            cell.number_format = "0.0%"
    _widths(ws, {get_column_letter(i + 1): (9 if i > 2 else 13)
                 for i in range(len(labels))})
    ws.auto_filter.ref = f"A1:{get_column_letter(len(labels))}{max(ws.max_row, 1)}"
    last = ws.max_row + 2
    _note(ws, last,
          "Counted columns are live COUNTIFS formulas over the Credits sheet. "
          "TOI, shifts and on-ice goals come from the on-ice sets.")

def _sheet_goalies(wb, game: Game) -> None:
    ws = wb.create_sheet("Goalies")
    _header(ws, ["Team", "Goalie", "Shots against", "Saves",
                 "Goals against", "Save %"])
    for row, goalie in enumerate(stats.goalies(game), start=2):
        opponent_short = TEAMS[other_teams(goalie.team)]["short"]
        ws.cell(row=row, column=1, value=TEAMS[goalie.team]["name"])
        ws.cell(row=row, column=2, value=goalie.names)
        ws.cell(row=row, column=3,
                value=_countifs("SOG", team_cell=f'"{opponent_short}"'))
        ws.cell(row=row, column=4, value=f"=C{row}-E{row}")
        ws.cell(row=row, column=5,
                value=_countifs("GOAL", team_cell=f'"{opponent_short}"'))
        ws.cell(row=row, column=6, value=f'=IFERROR(D{row}/C{row},"")')
        ws.cell(row=row, column=6).number_format = "0.000"
    _plain(ws)
    _widths(ws, {"A": 16, "B": 20, "C": 14, "D": 10, "E": 14, "F": 10})
    _note(ws, ws.max_row + 2,
          "Saves are worked out, not tagged: a save is a shot on goal "
          "against that did not go in. Goals count as shots on goal.")

def _sheet_goals(wb, game: Game) -> None:
    ws = wb.create_sheet("Goals")
    _header(ws, ["Video time", "Clock", "Period", "Team", "Scorer",
                 "Assists", f"On ice — {TEAMS['by']['short']}",
                 f"On ice — {TEAMS['gr']['short']}", "Note"])
    for goal in game.events_of("GOAL"):
        scorer = ""
        assists = []
        for person in goal.players:
            if person.role == "scorer":
                scorer = f"#{person.number}"
            else:
                assists.append(f"#{person.number}")
        ws.append([
            mmss(goal.t, True), goal.clock, goal.period,
            TEAMS[goal.team]["name"], scorer, ", ".join(assists),
            " ".join(f"#{n}" for n in stats.on_ice_at(game, "by", goal.t)),
            " ".join(f"#{n}" for n in stats.on_ice_at(game, "gr", goal.t)),
            goal.note,
        ])
    _plain(ws)
    _widths(ws, {"A": 11, "B": 8, "C": 7, "D": 16, "E": 9, "F": 14,
                 "G": 24, "H": 24, "I": 30})

def _sheet_confidence(wb, game:Game) -> None:
    ws = wb.create_sheet("Confidence")
    _header(ws, ["Event type", "Logged", "Flagged for review",
                 "Share flagged", "What limits it"])
 
    limits = {
        "ONICE": "Far-side jersey numbers at the bench are small on this camera.",
        "PASS": "Rapid passing sequences are the hardest events to attribute.",
        "FO": "The losing player is often obscured at the dot.",
    }
    summary = stats.flagged_summary(game)
    for code in sorted(summary):
        flagged, total = summary[code]
        row = ws.max_row + 1
        ws.cell(row=row, column=1, value=code)
        ws.cell(row=row, column=2, value=total)
        ws.cell(row=row, column=3, value=flagged)
        percent = ws.cell(row=row, column=4, value=f"=IFERROR(C{row}/B{row},\"\")")
        percent.number_format = "0.0%"
        ws.cell(row=row, column=5, value=limits.get(code, ""))
 
    _plain(ws)
    _widths(ws, {"A": 14, "B": 10, "C": 18, "D": 14, "E": 64})
    _note(ws, ws.max_row + 2,
          "A flagged event was logged but could not be read with confidence. "
          "Flagged events are never guessed; filter the Event log on the "
          "Flagged column to review each one against the video.")
 
 
def _sheet_roster(wb, game: Game) -> None:
    ws = wb.create_sheet("Roster")
    _header(ws, ["Team", "Number", "Position", "Number confirmed on video",
                 "Note"])
    for team in TEAMS:
        for player in game.roster(team):
            ws.append([TEAMS[team]["name"], player.label(), player.position,
                       "yes" if player.confirmed else "", player.note])
    _plain(ws)
    _widths(ws, {"A": 16, "B": 10, "C": 10, "D": 24, "E": 40})

SHEET_ORDER = ["Definitions", "Team totals", "Skaters", "Goalies", "Goals",
               "Confidence", "Event log", "Credits", "Roster"]
 
 
def build_workbook(game: Game, path: Path,
                   end_time: Optional[float] = None) -> Path:
    """Write the full deliverable and return where it went."""
    skaters, _teams = stats.build(game, end_time)
 
    wb = Workbook()
    wb.remove(wb.active)                 # drop the default empty sheet
 
    _sheet_definitions(wb, game)
    _sheet_team(wb, game)
    _sheet_skaters(wb, game, skaters)
    _sheet_goalies(wb, game)
    _sheet_goals(wb, game)
    _sheet_confidence(wb, game)
    _sheet_event_log(wb, game)
    _sheet_credits(wb, game)
    _sheet_roster(wb, game)
 
    wb._sheets.sort(key=lambda ws: SHEET_ORDER.index(ws.title))
 
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path