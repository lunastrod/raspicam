import time
import threading
import urllib.request

import Cam
import CameraBot


HEARTBEAT_URL = "https://hc-ping.com/9076e5c1-bd8e-41ca-9b67-810e14df4bf7"
HEARTBEAT_INTERVAL = 120  # seconds


def heartbeat():
    while True:
        try:
            urllib.request.urlopen(HEARTBEAT_URL, timeout=10)
            print("Heartbeat sent")
        except Exception as e:
            print(f"Heartbeat failed: {e}")

        time.sleep(HEARTBEAT_INTERVAL)


def main():

    # Start heartbeat in the background
    heartbeat_thread = threading.Thread(
        target=heartbeat,
        daemon=True
    )
    heartbeat_thread.start()

    cam = Cam.Cam("Camara1")

    bot = CameraBot.CameraBot("Bot1")
    bot.start_thread()

    cam.vigilar()

    print("Camara iniciada")
    print("Bot iniciado")

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()