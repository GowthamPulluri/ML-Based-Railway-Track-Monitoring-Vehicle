import cv2
import numpy as np
import time
import requests
import json
import threading
from ultralytics import YOLO

# ================= YOLO =================
model = YOLO("C:\\Users\\pullu\\Downloads\\best.pt")

# ================= API =================
API_URL = "https://script.google.com/macros/s/AKfycbz5c6s5MCS6WDGJo9ylDRUXgx4BvZeJPCr8VOcGZn-ncKsQdi0V3U2DiGM8enhUkgmW/exec"

# ================= CAMERA =================
ESPCAM_URL = "http://10.139.87.34:81/stream"
cap = cv2.VideoCapture(ESPCAM_URL)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("❌ Camera not working")
    exit()

print("📷 System Started")

# ================= GLOBAL =================
last_sent = 0
last_sent_defect = None
COOLDOWN = 5

last_gps_time = 0
cached_lat, cached_lng = 0, 0

last_defect_state = "no defect"
last_defect_time = time.time()
NO_DEFECT_DELAY = 2

# Limit threads (VERY IMPORTANT)
thread_limit = threading.Semaphore(2)


# ================= STATUS =================
def send_status(state):
    global last_defect_state

    if state == last_defect_state:
        return

    last_defect_state = state

    def task():
        try:
            requests.post(API_URL, json={
                "action": "status",
                "state": state
            }, timeout=5)
            print("STATUS:", state)
        except Exception as e:
            print("Status Error:", e)

    threading.Thread(target=task, daemon=True).start()


# ================= GPS =================
def get_cached_gps():
    global last_gps_time, cached_lat, cached_lng

    if time.time() - last_gps_time > 5:
        for _ in range(2):
            try:
                res = requests.get(API_URL + "?action=gps", timeout=5)
                data = json.loads(res.text)

                lat = float(data.get("lat", 0))
                lng = float(data.get("lng", 0))

                if lat != 0 and lng != 0:
                    cached_lat, cached_lng = lat, lng
                    last_gps_time = time.time()
                    return cached_lat, cached_lng

            except:
                time.sleep(0.3)

    return cached_lat, cached_lng


# ================= SEND DEFECT =================
def send_defect(defect):
    global last_sent, last_sent_defect

    # Prevent duplicate spam
    if defect == last_sent_defect and time.time() - last_sent < COOLDOWN:
        return

    lat, lng = get_cached_gps()

    if lat == 0 or lng == 0:
        print("⚠️ Skipping (No GPS)")
        return

    last_sent = time.time()
    last_sent_defect = defect

    payload = {
        "action": "add",
        "time": time.strftime("%d/%m/%Y %H:%M:%S"),
        "defect": defect,
        "lat": lat,
        "lng": lng,
        "status": "Pending"
    }

    try:
        requests.post(API_URL, json=payload, timeout=5)
        print(f"✅ SENT: {defect} | GPS: {lat},{lng}")
    except Exception as e:
        print("Send Error:", e)


# ================= ASYNC WRAPPER =================
def send_defect_async(defect):

    def task():
        with thread_limit:
            send_defect(defect)

    threading.Thread(target=task, daemon=True).start()


# ================= FIRE =================
def detect_fire(frame):

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower = np.array([5, 120, 120])
    upper = np.array([35, 255, 255])

    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    detected = False

    for cnt in contours:
        if cv2.contourArea(cnt) > 4000:
            detected = True

    if detected:
        send_defect_async("Fire")

    return frame, detected


# ================= DAMAGE =================
def detect_damage(frame):

    results = model(frame, verbose=False)

    detected = False

    for r in results:
        if r.boxes is None:
            continue

        for box in r.boxes:
            conf = float(box.conf[0])

            if conf < 0.6:
                continue

            detected = True

    if detected:
        send_defect_async("Track Damage")

    return frame, detected


# ================= MAIN LOOP =================
frame_count = 0

while True:

    ret, frame = cap.read()

    if not ret:
        print("⚠️ Camera disconnected... reconnecting")
        cap.release()
        time.sleep(1)
        cap = cv2.VideoCapture(ESPCAM_URL)
        continue

    frame = cv2.resize(frame, (400, 300))
    frame_count += 1

    defect_detected = False

    # DAMAGE (reduce load)
    if frame_count % 3 == 0:
        frame, d = detect_damage(frame)
        if d:
            defect_detected = True

    # FIRE
    frame, f = detect_fire(frame)
    if f:
        defect_detected = True

    # STATUS CONTROL
    if defect_detected:
        last_defect_time = time.time()
        send_status("defect")
    else:
        if time.time() - last_defect_time > NO_DEFECT_DELAY:
            send_status("no defect")

    cv2.imshow("SMART TRACK MONITOR", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()