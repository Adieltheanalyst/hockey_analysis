# Rink Tag

Hockey video coding: tag events while you watch, get an Excel workbook out.

## Setup (once)

    python -m venv .venv
    .venv\Scripts\activate          # Windows
    pip install -r requirements.txt

## Every session

    uvicorn rinktag.api:app --reload

Open http://127.0.0.1:8000, load the game video, start tagging.
Your work saves to `game.json` after every single event.

## What lives where

    rinktag/models.py   what a player and an event are; the hotkey list
    rinktag/store.py    saving to game.json, backups, snapshots
    rinktag/stats.py    the statistics engine and the written definitions
    rinktag/excel.py    the workbook the client receives
    rinktag/api.py      the HTTP endpoints the browser calls
    rinktag/web/        the page: video player and hotkeys only

## Hotkeys

    S shot on goal      A missed       B blocked      G goal
    H scoring chance    F faceoff      E zone entry   X zone exit
    V giveaway          T takeaway     P pass         N penalty
    L on-ice set        O observation

    Tab   switch team          Space  play/pause      arrows  seek
    While a tag is open: digits type the number, C/D/W/K set qualifiers,
    / unknown player, ? flag for review, Enter save, Esc cancel.

## Workflow that works

1. First pass at 2x: log on-ice sets (L) and goals only. That builds the
   roster and the plus/minus backbone.
2. Second pass: shots, chances, faceoffs.
3. Third pass: entries, exits, giveaways, takeaways.
4. Last pass: passes. Slowest, so leave it until the rest is solid.
5. Log a final on-ice set at the buzzer so the last shift is not cut short.
6. Export the workbook, read the Definitions tab, edit anything you would
   have coded differently.