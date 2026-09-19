import time

import Cam
import CameraBot


def main():

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
