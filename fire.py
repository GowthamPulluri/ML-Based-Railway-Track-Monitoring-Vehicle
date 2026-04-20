import cv2
import numpy as np
from collections import deque

# ----------------------------
# Camera Stream
# ----------------------------
cap = cv2.VideoCapture("http://172.16.205.2:81/stream")   # ESP32 stream
# cap = cv2.VideoCapture(0)  # for webcam

if not cap.isOpened():
    print("Could not open camera stream")
    exit()

print("Camera started...")

# ----------------------------
# Flicker detection settings
# ----------------------------
FLICKER_HISTORY = 4
FLICKER_THRESHOLD = 2   # tune this value

# Dictionary storing flicker history per contour
flicker_db = {}  # id → deque of intensities

kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
prev_gray = None

while True:
    ret, frame = cap.read()
    if not ret:
        print("Frame error, retrying...")
        continue

    frame = cv2.resize(frame, (640, 480))
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # ----------------------------
    # FIRE COLOR MASK ONLY
    # ----------------------------
    lower_fire = np.array([0, 40, 140])
    upper_fire = np.array([35, 255, 255])
    fire_mask = cv2.inRange(hsv, lower_fire, upper_fire)

    fire_mask = cv2.morphologyEx(fire_mask, cv2.MORPH_OPEN, kernel)
    fire_mask = cv2.morphologyEx(fire_mask, cv2.MORPH_CLOSE, kernel)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # ----------------------------
    # FIND FIRE-LIKE REGIONS
    # ----------------------------
    contours, _ = cv2.findContours(fire_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    fire_detected = False

    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area < 2000:  # ignore small blobs
            continue

        x, y, w, h = cv2.boundingRect(cnt)

        # ----------------------------
        # FLICKER DETECTION
        # ----------------------------
        roi_gray = gray[y:y+h, x:x+w]
        if roi_gray.size == 0:
            continue

        mean_intensity = np.mean(roi_gray)

        # assign contour ID based on index
        if i not in flicker_db:
            flicker_db[i] = deque(maxlen=FLICKER_HISTORY)

        flicker_db[i].append(mean_intensity)

        # brightness variation
        variation = np.std(flicker_db[i]) if len(flicker_db[i]) >= 3 else 0

        # Fire = High flicker
        is_fire = variation > FLICKER_THRESHOLD

        # Draw bounding box
        color = (0, 0, 255) if is_fire else (0, 255, 255)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

        text = f"Var:{variation:.1f}"
        cv2.putText(frame, text, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        if is_fire:
            fire_detected = True

    # ----------------------------
    # PRINT RESULT
    # ----------------------------
    if fire_detected:
        print("🔥 FIRE DETECTED (flicker confirmed)")
    else:
        print("No Fire")

    # ----------------------------
    # SHOW WINDOWS
    # ----------------------------
    cv2.imshow("Fire Detection", frame)
    cv2.imshow("Fire Mask", fire_mask)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
