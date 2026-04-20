import cv2
import numpy as np
import tensorflow as tf
from collections import deque

# Load model
model_path = r'C:\Users\pullu\OneDrive\Desktop\Main project\railway_defect_model (1).h5'
model = tf.keras.models.load_model(model_path)

class_names = {0: "Non-Defected", 1: "Defected", 2: "Surroundings"}

# Camera
cap = cv2.VideoCapture(1)
if not cap.isOpened():
    print("Cannot open camera"); exit()

# Sliding window params (tune for speed/accuracy)
WINDOW = 96    # patch size
STEP = 48      # step size (overlap). larger -> fewer patches -> faster
MODEL_SIZE = (224, 224)

# Detection params
CONF_THRESH = 0.88   # raise to reduce false positives
BATCH_SIZE = 32      # number of patches predicted at once
MIN_AREA = 500       # ignore tiny merged boxes (pixels)
# temporal smoothing: require detection present in N recent frames
REQUIRED_FRAMES = 2
recent_detections = deque(maxlen=REQUIRED_FRAMES)

def preprocess_patch(patch):
    p = cv2.resize(patch, MODEL_SIZE)
    p = p.astype('float32') / 255.0
    p = np.expand_dims(p, axis=(0, -1))  # shape (1,224,224,1)
    return p

def batch_predict(patches_np):
    # patches_np shape -> (N,224,224,1)
    preds = model.predict(patches_np, verbose=0)
    return preds  # shape (N,3) expected

def merge_boxes_via_mask(boxes, img_shape):
    '''
    boxes: list of (x,y,w,h)
    returns list of merged bounding rects
    '''
    if not boxes:
        return []
    mask = np.zeros((img_shape[0], img_shape[1]), dtype=np.uint8)
    for (x,y,w,h) in boxes:
        cv2.rectangle(mask, (x,y), (x+w, y+h), 255, -1)
    # optional morphological closing to join nearby boxes
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15,15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    # find contours and bounding rects
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    merged = []
    for cnt in contours:
        x,y,w,h = cv2.boundingRect(cnt)
        if w*h >= MIN_AREA:
            merged.append((x,y,w,h))
    return merged

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    coords = []
    patches = []

    # Collect patches and coordinates
    for y in range(0, h - WINDOW + 1, STEP):
        for x in range(0, w - WINDOW + 1, STEP):
            patch = gray[y:y+WINDOW, x:x+WINDOW]
            coords.append((x,y,WINDOW,WINDOW))
            p = cv2.resize(patch, MODEL_SIZE).astype('float32')/255.0
            patches.append(p)

            # if batch full, predict
            if len(patches) >= BATCH_SIZE:
                batch = np.stack(patches, axis=0)[..., np.newaxis]  # (B,224,224,1)
                preds = batch_predict(batch)
                # attach preds back to coords area by area
                if 'all_preds' in locals():
                    all_preds = np.vstack((all_preds, preds))
                else:
                    all_preds = preds
                patches = []

    # remaining patches
    if patches:
        batch = np.stack(patches, axis=0)[..., np.newaxis]
        preds = batch_predict(batch)
        if 'all_preds' in locals():
            all_preds = np.vstack((all_preds, preds))
        else:
            all_preds = preds

    # Evaluate predictions and collect defect boxes
    defect_boxes = []
    if 'all_preds' in locals():
        for i, pred in enumerate(all_preds):
            cls = int(np.argmax(pred))
            conf = float(pred[cls])
            if cls == 1 and conf >= CONF_THRESH:
                defect_boxes.append(coords[i])
        # cleanup for next frame
        del all_preds

    # Merge boxes (mask + contours)
    merged = merge_boxes_via_mask(defect_boxes, gray.shape)

    # store merged boxes for temporal smoothing
    recent_detections.append(merged)

    # Aggregate detections across recent frames: keep boxes that appear in >= REQUIRED_FRAMES frames
    if REQUIRED_FRAMES > 1 and len(recent_detections) == REQUIRED_FRAMES:
        # simple majority intersection: build mask for each frame and AND them
        masks = []
        for det_list in recent_detections:
            m = np.zeros_like(gray, dtype=np.uint8)
            for (x,y,ww,hh) in det_list:
                cv2.rectangle(m, (x,y), (x+ww,y+hh), 255, -1)
            masks.append(m)
        # intersection mask (areas detected in all frames)
        intersect = masks[0]
        for m in masks[1:]:
            intersect = cv2.bitwise_and(intersect, m)
        # find contours on intersected mask
        final_contours, _ = cv2.findContours(intersect, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        final_boxes = []
        for cnt in final_contours:
            x,y,ww,hh = cv2.boundingRect(cnt)
            if ww*hh >= MIN_AREA:
                final_boxes.append((x,y,ww,hh))
    else:
        final_boxes = merged

    # Draw final boxes
    for (x,y,ww,hh) in final_boxes:
        cv2.rectangle(frame, (x,y), (x+ww, y+hh), (0,0,255), 2)
        cv2.putText(frame, "Defect", (x, y-8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

    cv2.imshow("Real-Time Railway Defect Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
