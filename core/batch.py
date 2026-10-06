import os
import shutil
import threading
from datetime import datetime

from core.renamer import build_name


class BatchJob(threading.Thread):
    def __init__(self, items, assignments, rename_template, backup, engine, on_event):
        super().__init__(daemon=True)
        self.items = items
        self.assignments = assignments
        self.rename_template = rename_template
        self.backup = backup
        self.engine = engine
        self.on_event = on_event

    def run(self):
        total = len(self.items)
        backup_dir = None
        if self.backup:
            backup_dir = os.path.join(
                os.path.expanduser("~"),
                "Documents",
                "MetadataStudio Backups",
                datetime.now().strftime("%Y-%m-%d_%H%M%S"),
            )
        for idx, item in enumerate(self.items):
            path = item["path"]
            renamed_to = None
            try:
                if backup_dir:
                    os.makedirs(backup_dir, exist_ok=True)
                    dst = os.path.join(backup_dir, os.path.basename(path))
                    if os.path.exists(dst):
                        dst = self._unique(dst)
                    shutil.copy2(path, dst)
                ok, msg = self.engine.write(path, self.assignments)
                if not ok:
                    raise RuntimeError(msg or "Error de ExifTool")
                if self.rename_template:
                    meta = self.engine.normalize(self.engine.read(path))
                    stem, ext = os.path.splitext(os.path.basename(path))
                    ext = ext.lstrip(".").lower() or "bin"
                    new_name = build_name(self.rename_template, meta, idx + 1, ext, stem)
                    if new_name.lower() != os.path.basename(path).lower():
                        new_path = self._unique(os.path.join(os.path.dirname(path), new_name))
                        os.rename(path, new_path)
                        item["path"] = new_path
                        item["name"] = os.path.basename(new_path)
                        renamed_to = item["name"]
                self.on_event({"type": "item", "index": idx, "status": "ok", "renamed": renamed_to})
            except Exception as e:
                self.on_event({"type": "item", "index": idx, "status": "error", "message": str(e)})
        self.on_event({"type": "done", "total": total})

    @staticmethod
    def _unique(path):
        if not os.path.exists(path):
            return path
        d, f = os.path.split(path)
        stem, ext = os.path.splitext(f)
        i = 1
        while True:
            cand = os.path.join(d, f"{stem} ({i}){ext}")
            if not os.path.exists(cand):
                return cand
            i += 1
