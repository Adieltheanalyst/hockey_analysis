import json 
import os 
import shutil
from datetime import datetime
from pathlib import Path
from models import Game 

DEFAULT_PATH =Path("game.json")
BACKUP_COUNT=5

def save(game: Game, path:Path= DEFAULT_PATH) -> Path:
    path=Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        _rotate_backups(path)

    temp=path.with_suffix(path.suffix+".tmp")
    with temp.open("w", encoding="utf-8") as fh:
        json.dump(game.to_dict(), fh, indent=2, ensure_ascii=False)
        fh.flush()
        os.fsync(fh.fileno())
    temp.replace(path)
    return path

def load(path: Path=DEFAULT_PATH)-> Game:
    path=Path(path)
    if not path.exists():
        return Game()
    with path.open(encoding="utf-8") as fh:
        return Game.from_dict(json.load(fh))

def _rotate_backups(path:Path)->None:

    oldest=path.with_suffix(path.suffix+f".bak{BACKUP_COUNT}")
    if oldest.exists():
        oldest.unlink()

    for n in range(BACKUP_COUNT -1, 0,-1):
        older =path.with_suffix(path.suffix + f".bak{n +1}")
        if older.exists():
            older.replace(path.with_suffix(path.suffix + f".bak{n+1}"))
    shutil.copy2(path,path.with_suffix(path.suffix + ".bak1"))

def snapshot(game: Game, folder: Path= Path("snapshots")) -> Path:

    folder =Path(folder)
    folder.mkdir(parents=True, exists_ok=True)
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name="".join(c if c.isalnum() else "-" for c in game.name).strip("-")
    path=folder / f"{safe_name or 'game'}-{stamp}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(game.to_dict(), fh, indent=2, ensure_ascii=False)
    return path