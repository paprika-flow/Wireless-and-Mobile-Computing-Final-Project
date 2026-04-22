import requests
import time

ANDROID_IP = "192.168.1.37"  # your phone IP
PORT = 8080

def send_color(color: str):
    url = f"http://{ANDROID_IP}:{PORT}/"
    try:
        response = requests.get(url, params={"color": color})
        if response.status_code == 200:
            print(f"Sent color {color} successfully")
        else:
            print(f"Failed to send color {color}, status: {response.status_code}")
    except Exception as e:
        print(f"Error sending color: {e}")

if __name__ == "__main__":
    colors = ["RED", "GREEN", "YELLOW", "BLUE", "BLACK"]
    for color in colors:
        send_color(color)
        time.sleep(1.5)  # ⬅️ adjust this (seconds)