import os
import queue
import threading
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")
BUCKET = "turret_media"


class Uploader:
    def __init__(self):
        self.enabled = bool(SUPABASE_URL and SUPABASE_KEY)
        if not self.enabled:
            print("Uploader off (no .env found)")
            return
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.q = queue.Queue(maxsize=100)
        threading.Thread(target=self._worker, daemon=True).start()
    
    def send(self, event_type, conf, cx, cy, raw_path=None, ann_path=None):
        if not self.enabled:
            return
        try:
            self.q.put.nowait({
                "event_type": event_type, "conf": conf, "cx": cx, "cy": cy,
                "raw_path": raw_path, "ann_path": ann_path,
            })
        except queue.Full:
            print("Upload queue full, skipping event")

    def _upload_file(self, local_path):
        if not local_path:
            return None
        remote_path = f"{datetime.now():%Y-%m-%d}/{os.path.basename(local_path)}"
        with open(local_path, "rb") as f:
            self.client.storage.from_(BUCKET).upload(
                remote_path, f.read(), {"content-type": "image/jpeg"}
            )
        return remote_path

    def _worker(self):
        while True:
            ev = self.q.get()
            try:
                snapshot = self._upload_file(ev["raw_path"])
                annotated = self._upload_file(ev["ann_path"])
                self.client.table("events").insert({
                    "event_type": ev["event_type"],
                    "confidence": round(ev["conf"], 2),
                    "cx": ev["cx"],
                    "cy": ev["cy"],
                    "snapshot_path": snapshot,
                    "annotated_path": annotated,
                }).execute()
                print(f"UPLOADED {ev['event_type']}")
            except Exception as e:
                print("Upload failed:", e)