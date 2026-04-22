import cv2
import mediapipe as mp

# --- 1. MediaPipe Setup ---
BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path='face_landmarker.task'),
    running_mode=VisionRunningMode.IMAGE,
    output_face_blendshapes=True,
    num_faces=1
)
landmarker = FaceLandmarker.create_from_options(options)

# --- 2. Target Features ---
TARGET_FEATURES = [
    "eyeBlinkLeft", "eyeBlinkRight",
    "eyeWideLeft", "eyeWideRight",
    "jawOpen",
    "mouthSmileLeft", "mouthSmileRight",
    "mouthFrownLeft", "mouthFrownRight"
]

# --- 3. Webcam Loop ---
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1) # Mirror the image
    h, w, _ = frame.shape # Get actual frame dimensions for scaling landmarks
    
    resized_frame = cv2.resize(frame, (640, 480))
    rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    
    result = landmarker.detect(mp_image)

    # Default states (Neutral)
    eye_state = "eyesNeutral.PNG"
    mouth_state = "mouthNeutral.PNG"

    # Ensure we have both blendshapes AND landmarks
    if result.face_blendshapes and result.face_landmarks:
        # --- EXTRACT BLENDSHAPES ---
        scores = {feature: 0.0 for feature in TARGET_FEATURES}
        for shape in result.face_blendshapes[0]:
            if shape.category_name in TARGET_FEATURES:
                scores[shape.category_name] = shape.score

        # --- EYE STATE LOGIC ---
        if scores["eyeBlinkLeft"] > 0.5 and scores["eyeBlinkRight"] > 0.5:
            eye_state = "eyesClosed.PNG"
        elif scores["eyeWideLeft"] > 0.1 and scores["eyeWideRight"] > 0.1:
            eye_state = "eyesWide.PNG"
        elif scores["mouthSmileLeft"] > 0.5 and scores["mouthSmileRight"] > 0.5:
            eye_state = "eyesHappy.PNG"

        # --- MOUTH STATE LOGIC ---
        if scores["jawOpen"] > 0.3 and (scores["mouthSmileLeft"] > 0.4 or scores["mouthSmileRight"] > 0.4):
            mouth_state = "mouthOpenSmile.PNG"
        elif scores["jawOpen"] > 0.3:
            mouth_state = "mouthOpen.PNG"
        elif scores["mouthSmileLeft"] > 0.4 or scores["mouthSmileRight"] > 0.4:
            mouth_state = "mouthSmile.PNG"
        elif scores["mouthFrownLeft"] > 0.1 or scores["mouthFrownRight"] > 0.1:
            mouth_state = "MouthFrown.PNG"

        # --- BOUNDING BOX LOGIC ---
        landmarks = result.face_landmarks[0]
        
        # MediaPipe landmarks are normalized [0.0 to 1.0]. Multiply by width/height to get pixels.
        x_min = int(min(landmarks, key=lambda l: l.x).x * w)
        y_min = int(min(landmarks, key=lambda l: l.y).y * h)
        x_max = int(max(landmarks, key=lambda l: l.x).x * w)
        y_max = int(max(landmarks, key=lambda l: l.y).y * h)
        
        # Add a little padding so the box isn't directly on the skin
        padding = 20
        x_min = max(0, x_min - padding)
        y_min = max(0, y_min - padding)
        x_max = min(w, x_max + padding)
        y_max = min(h, y_max + padding)
        
        # Draw the bounding box (Green)
        cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

        # --- DYNAMIC TEXT PLACEMENT ---
        # Place text above the face, UNLESS the face is too close to the top edge, then put it below.
        text_y_start = y_min - 40 if y_min > 80 else y_max + 30
        
        # Draw text anchored to the x_min of the bounding box
        cv2.putText(frame, f"EYES: {eye_state}", (x_min, text_y_start), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(frame, f"MOUTH: {mouth_state}", (x_min, text_y_start + 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    else:
        # Fallback UI if tracking is lost momentarily
        cv2.putText(frame, "SEARCHING FOR FACE...", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    cv2.imshow('VTuber State Tester', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()