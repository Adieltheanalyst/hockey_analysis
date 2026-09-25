import json
import os
import shutil
from datetime import datetime
from pathlib import Path
 
from .models import Game
 
 
DEFAULT_PATH = Path("game.json")
BACKUP_COUNT = 5
 
 
def save(game: Game, path: Path = DEFAULT_PATH) -> Path:
    """
    Write the game to disk safely.
 
    We write to a temporary file first, then rename it over the real one.
    A rename is atomic: it either happens completely or not at all. So a
    crash halfway through can never leave you with a half-written file
    where your events used to be.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
 
    if path.exists():
        _rotate_backups(path)
 
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as fh:
        json.dump(game.to_dict(), fh, indent=2, ensure_ascii=False)
        fh.flush()
        os.fsync(fh.fileno())     # force it out of the OS cache to the disk
    temp.replace(path)            # the atomic step
    return path
 
 
def load(path: Path = DEFAULT_PATH) -> Game:
    """Read a game back. Returns an empty game if the file isn't there."""
    path = Path(path)
    if not path.exists():
        return Game()
    with path.open(encoding="utf-8") as fh:
        return Game.from_dict(json.load(fh))
 
 
def _rotate_backups(path: Path) -> None:
    """
    Keep the last few versions next to the file, newest first:
        game.json.bak1  (the version just replaced)
        game.json.bak2  ... and so on
    """
    oldest = path.with_suffix(path.suffix + f".bak{BACKUP_COUNT}")
    if oldest.exists():
        oldest.unlink()
    for n in range(BACKUP_COUNT - 1, 0, -1):
        older = path.with_suffix(path.suffix + f".bak{n}")
        if older.exists():
            older.replace(path.with_suffix(path.suffix + f".bak{n + 1}"))
    shutil.copy2(path, path.with_suffix(path.suffix + ".bak1"))
 
 
def snapshot(game: Game, folder: Path = Path("snapshots")) -> Path:
    """
    A named, dated copy you keep on purpose — before a risky edit, or
    when you finish a period. Different from a backup: backups rotate
    away, snapshots stay until you delete them.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = "".join(c if c.isalnum() else "-" for c in game.name).strip("-")
    path = folder / f"{safe_name or 'game'}-{stamp}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(game.to_dict(), fh, indent=2, ensure_ascii=False)
    return path