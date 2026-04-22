import cv2
import mediapipe as mp
import requests
import threading
import time
import csv

# --- CONFIGURATION ---
ANDROID_IP = "192.168.0.121"  # UPDATE THIS TO YOUR PHONE IP
PORT = 8080

# --- Benchmark Trackers ---
metrics_lock = threading.Lock()
stats = {
    "frames_processed": 0,
    "total_proc_time": 0.0,
    "requests_sent": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "bytes_sent": 0,
    "rtt_times": []
}

def send_data_to_phone(eye, mouth):
    global stats
    url = f"http://{ANDROID_IP}:{PORT}/"
    params = {"eye": eye, "mouth": mouth}
    
    # NEW: Print the exact data and destination
    print(f"  [NET SEND] Target: {url} | Data: {params}")
    
    # Calculate approx HTTP GET payload size in bytes
    payload_str = f"GET /?eye={eye}&mouth={mouth} HTTP/1.1\r\nHost: {ANDROID_IP}:{PORT}\r\n\r\n"
    payload_size = len(payload_str.encode('utf-8'))
    
    start_net = time.time()
    try:
        # Sending the actual GET request
        requests.get(url, params=params, timeout=1.0)
        end_net = time.time()
        
        with metrics_lock:
            stats["successful_requests"] += 1
            stats["bytes_sent"] += payload_size
            stats["rtt_times"].append(end_net - start_net)
    except Exception as e:
        print(f"  [NET ERROR] Failed to reach phone: {e}")
        with metrics_lock:
            stats["failed_requests"] += 1
            stats["bytes_sent"] += payload_size

# --- MediaPipe Setup ---
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

TARGET_FEATURES = [
    "eyeBlinkLeft", "eyeBlinkRight", "eyeWideLeft", "eyeWideRight",
    "jawOpen", "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight"
]

# --- Setup CSV Logging ---
csv_file = open('benchmarks.csv', 'w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["Time_Sec", "FPS", "Avg_Proc_Latency_ms", "Network_Requests", "Bytes_Sent", "Avg_RTT_ms", "Success_Rate_Percent"])

cap = cv2.VideoCapture(0)
last_eye_state, last_mouth_state = "", ""

print(f"--- Starting Benchmarks ---")
print(f"Target Phone: {ANDROID_IP}:{PORT}")
print("Press 'q' to stop.\n")

start_time = time.time()
logging_timer = time.time()
seconds_elapsed = 0

while cap.isOpened():
    t_frame_start = time.time()
    
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1) 
    resized_frame = cv2.resize(frame, (640, 480))
    rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    
    result = landmarker.detect(mp_image)

    # Default Neutral States
    eye_state = "eyesNeutral.PNG"
    mouth_state = "mouthNeutral.PNG"

    if result.face_blendshapes:
        scores = {feature: 0.0 for feature in TARGET_FEATURES}
        for shape in result.face_blendshapes[0]:
            if shape.category_name in TARGET_FEATURES:
                scores[shape.category_name] = shape.score

        # Eye Logic
        if scores["eyeBlinkLeft"] > 0.5 and scores["eyeBlinkRight"] > 0.5: eye_state = "eyesClosed.PNG"
        elif scores["eyeWideLeft"] > 0.1 and scores["eyeWideRight"] > 0.1: eye_state = "eyesWide.PNG"
        elif scores["mouthSmileLeft"] > 0.5 and scores["mouthSmileRight"] > 0.5: eye_state = "eyesHappy.PNG" 

        # Mouth Logic
        if scores["jawOpen"] > 0.3 and (scores["mouthSmileLeft"] > 0.4 or scores["mouthSmileRight"] > 0.4): mouth_state = "mouthOpenSmile.PNG"
        elif scores["jawOpen"] > 0.3: mouth_state = "mouthOpen.PNG"
        elif scores["mouthSmileLeft"] > 0.4 or scores["mouthSmileRight"] > 0.4: mouth_state = "mouthSmile.PNG"
        elif scores["mouthFrownLeft"] > 0.1 or scores["mouthFrownRight"] > 0.1: mouth_state = "MouthFrown.PNG"

    # Only send data if the visual state has changed
    if eye_state != last_eye_state or mouth_state != last_mouth_state:
        # NEW: Local log of the trigger
        print(f"[TRIGGER] State changed to: Eye={eye_state}, Mouth={mouth_state}")
        
        with metrics_lock: stats["requests_sent"] += 1
        threading.Thread(target=send_data_to_phone, args=(eye_state, mouth_state)).start()
        last_eye_state, last_mouth_state = eye_state, mouth_state

    t_frame_end = time.time()
    
    with metrics_lock:
        stats["frames_processed"] += 1
        stats["total_proc_time"] += (t_frame_end - t_frame_start)

    # --- EVERY 1 SECOND: LOG METRICS ---
    if time.time() - logging_timer >= 1.0:
        seconds_elapsed += 1
        with metrics_lock:
            fps = stats["frames_processed"]
            avg_proc = (stats["total_proc_time"] / fps * 1000) if fps > 0 else 0
            reqs = stats["requests_sent"]
            bytes_s = stats["bytes_sent"]
            avg_rtt = (sum(stats["rtt_times"]) / len(stats["rtt_times"]) * 1000) if stats["rtt_times"] else 0
            
            total_attempts = stats["successful_requests"] + stats["failed_requests"]
            success_rate = (stats["successful_requests"] / total_attempts * 100) if total_attempts > 0 else 100

            # Write to CSV
            csv_writer.writerow([seconds_elapsed, fps, round(avg_proc, 2), reqs, bytes_s, round(avg_rtt, 2), round(success_rate, 2)])
            csv_file.flush() 
            
            print(f">>> SEC {seconds_elapsed} | FPS: {fps} | Proc: {avg_proc:.1f}ms | Wi-Fi: {bytes_s}B | RTT: {avg_rtt:.1f}ms | Success: {success_rate:.0f}%")

            # Reset stats for the next second interval
            stats = {
                "frames_processed": 0, "total_proc_time": 0.0, "requests_sent": 0, 
                "successful_requests": 0, "failed_requests": 0, "bytes_sent": 0, "rtt_times": []
            }
        
        logging_timer = time.time()

    cv2.imshow('VTuber Benchmarker', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
csv_file.close()
print("\nBenchmarks saved to benchmarks.csv. Session ended.")