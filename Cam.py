import glob
import json
import os
import time
import threading
from datetime import datetime

import ffmpeg
from onvif import ONVIFCamera


class Cam:

    STREAM_DIR = "stream"
    NUM_SEGMENTS = 2
    LEN_SEGMENT = 30
    SECRET_FILE = "camara.secret"

    def __init__(self, cam_name):

        self.cam_name = cam_name
        self.pullpoint = None

        # Segmentos que contienen algún evento.
        #
        # {
        #     "segment_2026-09-02_14-52-30.ts": {
        #         "tipo": "movimiento",
        #         "fecha": "2026-09-02_14-52-31"
        #     }
        # }
        #
        self.segmentos_con_evento = {}

        self.extraer_credenciales()

        os.makedirs(
            self.STREAM_DIR,
            exist_ok=True
        )

        print("Conectando con la cámara...")
        project_dir = os.path.dirname(os.path.abspath(__file__))
        venv_dir = os.path.join(project_dir, "venv")
        wsdl_matches = glob.glob(
            os.path.join( venv_dir, "lib", "python*", "site-packages", "wsdl" )
        )

        if not wsdl_matches:
            raise RuntimeError( f"No se encontró el directorio WSDL en {venv_dir}" )
        
        wsdl_dir = wsdl_matches[0]

        self.cam = ONVIFCamera(
            self.ip,
            self.port,
            self.user,
            self.password,
            wsdl_dir=wsdl_dir
        )

        print("Cámara conectada")

        # Stream 2:
        # Se utiliza para el buffer continuo
        self.RTSP_URL = (
            f"rtsp://{self.user}:{self.password}"
            f"@{self.ip}:554/stream2"
        )

        # Stream 1:
        # Se utiliza para sacar fotografías
        self.RTSP_URL_FOTO = (
            f"rtsp://{self.user}:{self.password}"
            f"@{self.ip}:554/stream1"
        )

        self.hilo_buffer = threading.Thread(
            target=self.mantener_buffer,
            daemon=True
        )

        self.hilo_buffer.start()

    def extraer_credenciales(self):

        with open(
            self.SECRET_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            config = json.load(f)

        camera = config[self.cam_name]

        self.ip = camera["ip"]
        self.port = camera["port"]
        self.user = camera["user"]
        self.password = camera["password"]

    def sacar_foto(
        self,
        utc_time,
        tipo_evento
    ):

        fecha_utc = datetime.fromisoformat(
            utc_time.replace(
                "Z",
                "+00:00"
            )
        )

        fecha_local = fecha_utc.astimezone()

        fecha = fecha_local.strftime(
            "%Y-%m-%d_%H-%M-%S"
        )

        filename = os.path.join(
            self.STREAM_DIR,
            f"{fecha}_{tipo_evento}.jpg"
        )

        print("Sacando foto:", filename)

        try:

            (
                ffmpeg
                .input(
                    self.RTSP_URL_FOTO,
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

            return True

        except ffmpeg.Error as e:

            print("Error sacando foto")

            if e.stderr:

                print(
                    e.stderr.decode(
                        errors="ignore"
                    )
                )

            return False

    def convertir_segmento(
        self,
        segmento,
        utc_time,
        tipo_evento
    ):

        fecha_utc = datetime.fromisoformat(
            utc_time.replace(
                "Z",
                "+00:00"
            )
        )

        fecha_local = fecha_utc.astimezone()

        fecha = fecha_local.strftime(
            "%Y-%m-%d_%H-%M-%S"
        )

        filename = os.path.join(
            self.STREAM_DIR,
            f"{fecha}_{tipo_evento}.mp4"
        )

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
                .run(
                    capture_stdout=True,
                    capture_stderr=True
                )
            )

            print("MP4 creado:", filename)

            return True

        except ffmpeg.Error as e:

            print("Error convirtiendo MP4")

            if e.stderr:

                print(
                    e.stderr.decode(
                        errors="ignore"
                    )
                )

            return False

    def mantener_buffer(self):

        print("Iniciando buffer...")

        print(
            f"Buffer: {self.NUM_SEGMENTS} "
            f"segmentos de {self.LEN_SEGMENT} segundos"
        )

        print(
            f"Duración total: "
            f"{self.NUM_SEGMENTS * self.LEN_SEGMENT} segundos"
        )

        print("Directorio:", self.STREAM_DIR)

        while True:

            try:

                (
                    ffmpeg
                    .input(
                        self.RTSP_URL,
                        rtsp_transport="udp"
                    )
                    .output(
                        os.path.join(
                            self.STREAM_DIR,
                            "segment_%Y-%m-%d_%H-%M-%S.ts"
                        ),
                        #vcodec="libx264",
                        #preset="ultrafast",
                        vcodec="copy",
                        acodec="copy",
                        f="segment",
                        strftime=1,
                        segment_time=self.LEN_SEGMENT
                    )
                    .run(
                        capture_stdout=True,
                        capture_stderr=True
                    )
                )

            except Exception as e:

                print("Error en buffer:", e)
                print("Reintentando...")

                time.sleep(2)

    def crear_pullpoint(self):

        while True:

            try:

                print("Creando PullPoint...")

                events = self.cam.create_events_service()

                subscription = (
                    events.CreatePullPointSubscription()
                )

                address = (
                    subscription
                    .SubscriptionReference
                    .Address
                )

                self.pullpoint = (
                    self.cam.create_pullpoint_service(
                        address
                    )
                )

                print("PullPoint creado")

                return

            except Exception as e:

                print(
                    "ERROR creando PullPoint:",
                    e
                )

                print(
                    "Reintentando en 2 segundos..."
                )

                time.sleep(2)

    def pull_messages(self, resultado):

        try:

            resultado["response"] = (
                self.pullpoint.PullMessages({
                    "Timeout": "PT1S",
                    "MessageLimit": 20
                })
            )

        except Exception as e:

            resultado["error"] = e

    def leer_eventos(self):

        resultado = {
            "response": None,
            "error": None
        }

        hilo = threading.Thread(
            target=self.pull_messages,
            args=(resultado,),
            daemon=True
        )

        hilo.start()

        hilo.join(5)

        if hilo.is_alive():

            raise TimeoutError(
                "PullMessages está bloqueado"
            )

        if resultado["error"] is not None:

            raise resultado["error"]

        response = resultado["response"]

        eventos = []

        for notification in response.NotificationMessage:

            message = notification.Message._value_1

            utc_time = message.get("UtcTime")

            items = message.xpath(
                ".//*[local-name()='SimpleItem']"
            )

            for item in items:

                name = item.get("Name")
                value = item.get("Value")

                if name == "IsMotion":

                    if value.lower() == "true":

                        eventos.append(
                            (
                                utc_time,
                                "movimiento"
                            )
                        )

                elif name == "IsPeople":

                    if value.lower() == "true":

                        eventos.append(
                            (
                                utc_time,
                                "persona"
                            )
                        )

        return eventos

    def obtener_segmento_de_evento(
        self,
        utc_time
    ):

        # ONVIF proporciona UTC.
        #
        # Ejemplo:
        #
        # 2026-09-02T11:15:23Z

        fecha_utc = datetime.fromisoformat(
            utc_time.replace(
                "Z",
                "+00:00"
            )
        )

        fecha_local = fecha_utc.astimezone()

        timestamp_evento = (
            fecha_local.timestamp()
        )

        segmentos = []

        for filename in os.listdir(
            self.STREAM_DIR
        ):

            if not filename.endswith(".ts"):
                continue

            if not filename.startswith("segment_"):
                continue

            try:

                texto_fecha = (
                    filename
                    .replace(
                        "segment_",
                        ""
                    )
                    .replace(
                        ".ts",
                        ""
                    )
                )

                fecha_segmento = datetime.strptime(
                    texto_fecha,
                    "%Y-%m-%d_%H-%M-%S"
                )

                timestamp_segmento = (
                    fecha_segmento
                    .astimezone()
                    .timestamp()
                )

                segmentos.append(
                    (
                        timestamp_segmento,
                        filename
                    )
                )

            except ValueError:

                continue

        segmentos.sort()

        segmento_encontrado = None

        for (
            timestamp_segmento,
            filename
        ) in segmentos:

            if (
                timestamp_segmento
                <= timestamp_evento
            ):

                segmento_encontrado = filename

            else:

                break

        return segmento_encontrado

    def limpiar_buffer(self):

        ahora = time.time()

        limite = (
            ahora
            - self.NUM_SEGMENTS
            * self.LEN_SEGMENT
        )

        for filename in os.listdir(
            self.STREAM_DIR
        ):

            if not filename.endswith(".ts"):
                continue

            if not filename.startswith("segment_"):
                continue

            try:

                texto_fecha = (
                    filename
                    .replace(
                        "segment_",
                        ""
                    )
                    .replace(
                        ".ts",
                        ""
                    )
                )

                fecha_segmento = datetime.strptime(
                    texto_fecha,
                    "%Y-%m-%d_%H-%M-%S"
                )

                timestamp_segmento = (
                    fecha_segmento
                    .astimezone()
                    .timestamp()
                )

            except ValueError:

                continue

            # Todavía está dentro del buffer
            if timestamp_segmento > limite:

                continue

            segmento = os.path.join(
                self.STREAM_DIR,
                filename
            )

            # -------------------------------------------------
            # SEGMENTO CON EVENTO
            # -------------------------------------------------

            if filename in self.segmentos_con_evento:

                datos_evento = (
                    self.segmentos_con_evento[filename]
                )

                tipo_evento = datos_evento["tipo"]
                utc_time = datos_evento["fecha"]

                print(
                    "Segmento con evento:",
                    filename
                )

                convertido = (
                    self.convertir_segmento(
                        segmento,
                        utc_time,
                        tipo_evento
                    )
                )

                if convertido:

                    del self.segmentos_con_evento[
                        filename
                    ]

                    try:

                        os.remove(segmento)

                        print(
                            "TS eliminado:",
                            segmento
                        )

                    except OSError as e:

                        print(
                            "Error eliminando TS:",
                            e
                        )

            # -------------------------------------------------
            # SEGMENTO SIN EVENTO
            # -------------------------------------------------

            else:

                #print("Segmento sin evento, eliminando:",filename)

                try:

                    os.remove(segmento)

                except OSError as e:

                    print(
                        "Error eliminando TS:",
                        e
                    )

    def procesar_solicitudes(self):

        foto_request = os.path.join(
            self.STREAM_DIR,
            "photo.request"
        )

        if os.path.exists(foto_request):

            try:

                utc_time = datetime.now().astimezone().isoformat()

                if self.sacar_foto(utc_time, "manual"):

                    os.remove(foto_request)

                    print("Solicitud de foto procesada")

            except Exception as e:

                print("Error procesando solicitud de foto:", e)

        video_request = os.path.join(
            self.STREAM_DIR,
            "video.request"
        )

        if os.path.exists(video_request):

            try:

                segmentos = [
                    os.path.join(self.STREAM_DIR, filename)
                    for filename in os.listdir(self.STREAM_DIR)
                    if (
                        filename.startswith("segment_")
                        and filename.endswith(".ts")
                    )
                ]

                segmentos.sort(key=os.path.getmtime)

                # El mÃ¡s reciente todavÃ­a puede estar escribiÃ©ndose.
                if len(segmentos) < 2:

                    print(
                        "No hay un segmento completado "
                        "para la solicitud de video"
                    )

                    return

                segmento = segmentos[-2]
                utc_time = datetime.now().astimezone().isoformat()

                if self.convertir_segmento(
                    segmento,
                    utc_time,
                    "manual"
                ):

                    os.remove(video_request)

                    print("Solicitud de video procesada")

            except Exception as e:

                print("Error procesando solicitud de video:", e)

    def vigilar(self):

        print("Iniciando vigilancia...")

        self.crear_pullpoint()

        while True:

            try:

                eventos = self.leer_eventos()

                for (
                    utc_time,
                    tipo_evento
                ) in eventos:

                    #print(f"EVENTO: {utc_time} - "f"{tipo_evento}")

                    segmento = (
                        self.obtener_segmento_de_evento(
                            utc_time
                        )
                    )

                    if segmento is None:

                        print(
                            "No se encontró el segmento "
                            "correspondiente"
                        )

                        continue

                    #print("Segmento del evento:",segmento)

                    # Si ya hay un evento en este segmento,
                    # persona tiene prioridad sobre movimiento.
                    if segmento in self.segmentos_con_evento:

                        evento_anterior = (
                            self.segmentos_con_evento[
                                segmento
                            ]
                        )

                        if (
                            evento_anterior["tipo"]
                            == "persona"
                        ):

                            continue

                        if (
                            tipo_evento
                            == "persona"
                        ):

                            self.segmentos_con_evento[
                                segmento
                            ] = {
                                "tipo": "persona",
                                "fecha": utc_time
                            }

                    else:

                        self.segmentos_con_evento[
                            segmento
                        ] = {
                            "tipo": tipo_evento,
                            "fecha": utc_time
                        }

                    self.sacar_foto(
                        utc_time,
                        tipo_evento
                    )

                self.procesar_solicitudes()

                # Aprovechamos el hilo de vigilancia
                # para mantener el buffer circular.
                self.limpiar_buffer()

            except Exception as e:

                print(
                    "Error en vigilancia:",
                    e
                )

                print(
                    "Recreando PullPoint..."
                )

                time.sleep(2)

                self.crear_pullpoint()
