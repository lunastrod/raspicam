import json
import os
import ffmpeg


STREAM_DIR = "stream"

# Número de segmentos que queremos conservar
NUM_SEGMENTS = 3

# Crear directorio si no existe
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



print("Iniciando buffer...")
print(f"Buffer: {NUM_SEGMENTS} segmentos de 10 segundos")
print(f"Duración total: {NUM_SEGMENTS * 10} segundos")
print("Directorio:", STREAM_DIR)

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
        segment_time=10,
        segment_wrap=NUM_SEGMENTS
    )
    .run()
)