import cv2
import pytesseract
import re
import threading
import time

# Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class VideoStream:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.ret, self.frame = self.cap.read()
        self.stopped = False
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if not ret:
                continue
            with self.lock:
                self.frame = frame

    def read(self):
        with self.lock:
            return self.frame.copy()

    def stop(self):
        self.stopped = True
        self.cap.release()


def ocr_worker(roi):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    text = pytesseract.image_to_string(
        thresh,
        config="--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789"
    )
    numbers = re.findall(r"\d+", text)
    return " ".join(numbers) if numbers else ""

def main():
    vs = VideoStream(0)
    frame_count = 0
    latest_detected = ""
    ocr_result_lock = threading.Lock()

    def ocr_thread_func(roi_crop):
        nonlocal latest_detected
        detected = ocr_worker(roi_crop)
        if detected:
            with ocr_result_lock:
                latest_detected = detected

    ocr_thread = None

    while True:
        frame = vs.read()
        if frame is None:
            print("⚠️ Frame grab failed, skipping...")
            continue

        frame = cv2.resize(frame, (400, 300))

        # Define ROI
        y1, y2, x1, x2 = 100, 250, 100, 300
        roi = frame[y1:y2, x1:x2]

        frame_count += 1
        # Run OCR every 10 frames, and only if previous OCR thread finished
        if frame_count % 10 == 0:
            if (ocr_thread is None) or (not ocr_thread.is_alive()):
                ocr_thread = threading.Thread(target=ocr_thread_func, args=(roi,))
                ocr_thread.daemon = True
                ocr_thread.start()

        # Draw ROI rectangle
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Show latest OCR detection
        with ocr_result_lock:
            if latest_detected:
                cv2.putText(frame, latest_detected, (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1,
                            (0, 255, 0), 2, cv2.LINE_AA)

        cv2.imshow("Number Detection (Press q to quit)", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    vs.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
