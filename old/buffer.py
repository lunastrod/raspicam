import json
import os
import threading
import time
import ffmpeg


STREAM_DIR = "stream"
NUM_SEGMENTS = 2
LEN_SEGMENT = 10

os.makedirs(STREAM_DIR, exist_ok=True)


SECRET_FILE = "camara.secret"
CAMERA_NAME = "Camara2"

with open(SECRET_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

camera = config[CAMERA_NAME]


RTSP_URL = (
    f"rtsp://{camera['user']}:{camera['password']}"
    f"@{camera['ip']}:554/stream2"
)



def mantener_buffer():

    print("Iniciando buffer...")
    print(f"Buffer: {NUM_SEGMENTS} segmentos de {LEN_SEGMENT} segundos")
    print(f"Duración total: {NUM_SEGMENTS * LEN_SEGMENT} segundos")
    print("Directorio:", STREAM_DIR)

    while True:

        try:

            (
                ffmpeg
                .input(
                    RTSP_URL,
                    rtsp_transport="udp"
                )
                .output(
                    os.path.join(
                        STREAM_DIR,
                        "segment_%02d.ts"
                    ),
                    vcodec="libx264",
                    preset="ultrafast",
                    f="segment",
                    segment_time=LEN_SEGMENT,
                    segment_wrap=NUM_SEGMENTS
                )
                .run(
                    capture_stdout=True,
                    capture_stderr=True
                )
            )

            #mandar una señal o algo al hilo principal para indicar que se ha creado un segmento nuevo

        except Exception as e:

            print("Error en buffer:", e)
            print("Reintentando...")




def convertir_ultimo_segmento():

    archivos = [
        os.path.join(STREAM_DIR, f)
        for f in os.listdir(STREAM_DIR)
        if f.endswith(".ts")
    ]

    archivos.sort(key=os.path.getmtime)
    segmento = None
    try:
        segmento = archivos[-2]
    except IndexError:
        return

    filename = "output" + ".mp4"

    print("Convirtiendo:", segmento)
    print("Destino:", filename)

    try:
        (
            ffmpeg
            .input(segmento)
            .output(
                filename,
                vcodec="copy",
                acodec="aac",
                movflags="+faststart"
            )
            .overwrite_output()
            .run()
        )

        print("MP4 creado:", filename)

    except ffmpeg.Error as e:

        print("Error convirtiendo MP4")

        if e.stderr:
            print(e.stderr.decode(errors="ignore"))


def sacar_foto(filename):

    print("Sacando foto:", filename)

    (
        ffmpeg
        .input(
            RTSP_URL,
            rtsp_transport="tcp"
        )
        .output(
            filename,
            vframes=1,
            vcodec="mjpeg"
        )
        .overwrite_output()
        .run(
            capture_stdout=True,
            capture_stderr=True
        )
    )

    print("Foto guardada:", filename)

def main():
    hilo_buffer = threading.Thread(
        target=mantener_buffer,
        daemon=True
    )

    hilo_buffer.start()

    print("Buffer iniciado")

    while True:

        time.sleep(LEN_SEGMENT)

        filename = os.path.join(
            STREAM_DIR,
            f"video_{int(time.time())}.mp4"
        )

        convertir_ultimo_segmento()


if __name__ == "__main__":
    main()