import sys
import csv
import os
import time
from datetime import datetime

import cv2
from ultralytics import YOLO

SOURCE = sys.argv[1] if len(sys.argv) > 1 else "data/pigeons.mov"
BIRD_CLASS = 14         # COCO class id for bird
CONF_THRESHOLD = 0.3    # tune later

SHOW_WINDOW = False     # False on the Pi (no screen), True on your Mac
frame_count = 0
fps_start = time.time()

CONFIRM_FRAMES = 5      # frames in a row needed to confirm
MAX_JUMP = 150           # pixels: farther than this = probably a different bird
BURST_SEC = 0.5         # how long each spray lasts
COOLDOWN_SEC = 1.0      # wait after a spray before it can fire again
LOG_PATH = "shots.csv"

AQUA = (255, 200, 0)
YELLOW = (80, 220, 255)
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)

SNAPSHOT_DIR = "snapshots"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

streak = 0              # how many frames in a row we've seen the bird
last_center = None      # where the bird was last frame
state = "IDLE"          # IDLE, TRACKING, FIRING, COOLDOWN
state_start = time.time()

model = YOLO("yolo11n.pt")

if SOURCE == "camera":
    from picamera2 import Picamera2          # only exists on the Pi
    picam = Picamera2()
    config = picam.create_video_configuration(main={"size": (1280, 720), "format": "RGB888"})
    picam.configure(config)
    picam.start()
    time.sleep(1)                            # let the camera warm up

    def read_frame():
        return True, picam.capture_array()
else:
    cap = cv2.VideoCapture(SOURCE)

    def read_frame():
        return cap.read()


class MockTurret:
    """Stand-in for the real turret. Same methods, just prints."""

    def aim(self, cx, cy):
        print(f"AIM at ({cx}, {cy})")

    def fire(self, on):
        print("SPLASH ON" if on else "SPLASH OFF")


turret = MockTurret()


def draw_marker(frame, cx, cy, size):
    # Thin, faint ring for birds that aren't the current target
    cv2.circle(frame, (cx, cy), size, GRAY, 1, cv2.LINE_AA)
    cv2.circle(frame, (cx, cy), 2, GRAY, -1, cv2.LINE_AA)


def distance(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def box_center(box):
    x1, y1, x2, y2 = box.xyxy[0].tolist()
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


def log_shot(cx, cy, conf, raw_image, annotated_image):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    raw_path = os.path.join(SNAPSHOT_DIR, f"shot_{ts}.jpg")
    ann_path = os.path.join(SNAPSHOT_DIR, f"shot_{ts}_annotated.jpg")
    cv2.imwrite(raw_path, raw_image)
    cv2.imwrite(ann_path, annotated_image)

    new_file = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["timestamp", "cx", "cy", "confidence", "snapshot", "annotated"])
        writer.writerow([datetime.now().isoformat(timespec="seconds"), cx, cy, round(conf, 2), raw_path, ann_path])


def draw_scope(frame, cx, cy, size, conf, color=AQUA):
    r = size
    aa = cv2.LINE_AA

    overlay = frame.copy()
    cv2.circle(overlay, (cx, cy), r, color, -1, aa)
    cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)

    cv2.circle(frame, (cx, cy), r, color, 2, aa)

    tick = max(6, r // 4)
    cv2.line(frame, (cx, cy - r), (cx, cy - r + tick), color, 2, aa)
    cv2.line(frame, (cx, cy + r), (cx, cy + r - tick), color, 2, aa)
    cv2.line(frame, (cx - r, cy), (cx - r + tick, cy), color, 2, aa)
    cv2.line(frame, (cx + r, cy), (cx + r - tick, cy), color, 2, aa)

    cv2.circle(frame, (cx, cy), 3, WHITE, -1, aa)

    label = f"pigeon {conf:.0%}"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    lx, ly = cx - tw // 2, cy - r - 10
    cv2.rectangle(frame, (lx - 6, ly - th - 6), (lx + tw + 6, ly + 4), color, -1)
    cv2.putText(
        frame, label, (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1, aa
    )


while True:
    ok, frame = read_frame()
    raw = frame.copy()  # clean frame, no overlays, for training data later
    if not ok:
        break

    results = model(frame, classes=[BIRD_CLASS], conf=CONF_THRESHOLD, verbose=False)
    boxes = results[0].boxes
    confirmed = False  # reset every frame

    # ---------- Tracking ----------
    if len(boxes) == 0:
        streak = 0
        last_center = None
    else:
        if last_center is None:
            # No target yet: start with the most confident bird
            best = max(boxes, key=lambda b: float(b.conf))
        else:
            # Already tracking: stick with the bird closest to where we last saw it
            best = min(boxes, key=lambda b: distance(box_center(b), last_center))

        x1, y1, x2, y2 = best.xyxy[0].tolist()
        conf = float(best.conf)
        cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)

        if last_center is None or distance((cx, cy), last_center) > MAX_JUMP:
            streak = 1
        else:
            streak += 1

        last_center = (cx, cy)
        confirmed = streak >= CONFIRM_FRAMES

        color = YELLOW if confirmed else AQUA
        size = int(max(x2 - x1, y2 - y1) / 2) + 10

        # Faint ring on every bird the model sees
        for b in boxes:
            bx, by = box_center(b)
            draw_marker(frame, bx, by, 12)

        draw_scope(frame, cx, cy, size, conf, color)

    # ---------- State machine ----------
    now = time.time()

    if state in ("IDLE", "TRACKING"):
        state = "TRACKING" if streak > 0 else "IDLE"
        if confirmed:
            turret.aim(cx, cy)
            turret.fire(True)
            log_shot(cx, cy, conf, raw, frame)
            state, state_start = "FIRING", now

    elif state == "FIRING":
        if now - state_start >= BURST_SEC:
            turret.fire(False)
            state, state_start = "COOLDOWN", now

    elif state == "COOLDOWN":
        if now - state_start >= COOLDOWN_SEC:
            state = "IDLE"
            streak = 0  # must re-confirm before the next shot

    # ---------- On-screen status ----------
    if state == "TRACKING":
        status = f"TRACKING  {min(streak, CONFIRM_FRAMES)}/{CONFIRM_FRAMES}"
    else:
        status = state
    status_color = AQUA if state == "FIRING" else WHITE
    cv2.putText(frame, status, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2, cv2.LINE_AA)

    # FPS readout every 30 frames
    frame_count += 1
    if frame_count % 30 == 0:
        fps = 30 / (time.time() - fps_start)
        print(f"FPS: {fps:.1f}")
        fps_start = time.time()

    if SHOW_WINDOW:
        cv2.imshow("Pigeon Patrol", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

if SOURCE == "camera":
    picam.stop()
else:
    cap.release()

cv2.destroyAllWindows()
