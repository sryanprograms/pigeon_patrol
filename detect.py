import cv2
from ultralytics import YOLO

VIDEO_PATH = "data/pigeons.mov"
BIRD_CLASS=14 #coco class id for bird
CONF_THRESHOLD=0.3 #tune later

model = YOLO("yolo11n.pt")
cap=cv2.VideoCapture(VIDEO_PATH)

AQUA = (255, 200, 0)
WHITE = (255, 255, 255)

def draw_scope(frame, cx, cy, size, conf, color=AQUA):
    r = size
    aa = cv2.LINE_AA                     # smooth, anti-aliased lines

    # Soft see-through fill inside the ring
    overlay = frame.copy()
    cv2.circle(overlay, (cx, cy), r, color, -1, aa)
    cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)

    # Thin outer ring
    cv2.circle(frame, (cx, cy), r, color, 2, aa)

    # Short tick marks at 12, 3, 6 and 9 o'clock instead of a full crosshair
    tick = max(6, r // 4)
    cv2.line(frame, (cx, cy - r), (cx, cy - r + tick), color, 2, aa)
    cv2.line(frame, (cx, cy + r), (cx, cy + r - tick), color, 2, aa)
    cv2.line(frame, (cx - r, cy), (cx - r + tick, cy), color, 2, aa)
    cv2.line(frame, (cx + r, cy), (cx + r - tick, cy), color, 2, aa)

    # Small center dot
    cv2.circle(frame, (cx, cy), 3, WHITE, -1, aa)

    # Rounded-looking label above the ring
    label = f"pigeon {conf:.0%}"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    lx, ly = cx - tw // 2, cy - r - 10
    cv2.rectangle(frame, (lx - 6, ly - th - 6), (lx + tw + 6, ly + 4), color, -1)
    cv2.putText(frame, label, (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1, aa)

while True:
    ok,frame=cap.read()
    if not ok:
        break

    # Run yolo on this frame, birds only
    results=model(frame, classes=[BIRD_CLASS], conf=CONF_THRESHOLD, verbose=False)

    for box in results[0].boxes:
        x1,y1,x2,y2=box.xyxy[0].tolist()
        conf=float(box.conf)

        #compute the center of the box
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        
        size = int(max(x2 - x1, y2 - y1) / 2) + 10   # scope scales with the bird
        draw_scope(frame, cx, cy, size, conf)

        #print (cx,cy,conf)
        print(f"({cx:.2f}, {cy:.2f}, {conf:.2f})")

    cv2.imshow("Pigeon Patrol", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): #press q to quit
        break

cap.release()
cv2.destroyAllWindows()