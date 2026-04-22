Low Latency Video Call using Avatars
Overview

This project replaces traditional video calls with animated avatars to reduce latency, bandwidth usage, and improve user privacy. Instead of streaming video, it sends lightweight facial feature data over WiFi.

How It Works
Capture webcam input and extract facial features (MediaPipe)
Send feature data as JSON over WiFi
Reconstruct expressions as an avatar on a phone

Key Features
~24ms latency (~41 FPS)
~300 bytes/sec data usage
Privacy-friendly (no video stream)
Limitations
Local network only
Requires lighting and close distance (~5 ft)
Future Work
More facial features + audio
Internet support
iOS version
