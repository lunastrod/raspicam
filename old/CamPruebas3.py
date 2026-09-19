import json
import time
import threading

from onvif import ONVIFCamera

def obtener_stream_urls(cam):
    media = cam.create_media_service()
    profiles = media.GetProfiles()
    stream_urls = []

    for profile in profiles:

        stream = media.GetStreamUri({
            "StreamSetup": {
                "Stream": "RTP-Unicast",
                "Transport": {
                    "Protocol": "RTSP"
                }
            },
            "ProfileToken": profile.token
        })

        stream_urls.append(stream.Uri)

    return stream_urls

def crear_pullpoint(cam):

    while True:

        try:
            print("Creando PullPoint...")

            events = cam.create_events_service()

            subscription = events.CreatePullPointSubscription()

            address = subscription.SubscriptionReference.Address

            pullpoint = cam.create_pullpoint_service(address)

            print("PullPoint creado")

            return pullpoint

        except Exception as e:

            print("ERROR creando PullPoint:", e)
            print("Reintentando en 2 segundos...")

            time.sleep(2)


def pull_messages(pullpoint, resultado):

    try:

        resultado["response"] = pullpoint.PullMessages({
            "Timeout": "PT1S",
            "MessageLimit": 20
        })

    except Exception as e:

        resultado["error"] = e


def leer_eventos(pullpoint):

    resultado = {
        "response": None,
        "error": None
    }

    hilo = threading.Thread(
        target=pull_messages,
        args=(pullpoint, resultado),
        daemon=True
    )

    hilo.start()

    hilo.join(5)

    if hilo.is_alive():
        raise TimeoutError("PullMessages está bloqueado")

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

            if name in ("IsMotion", "IsPeople"):

                if value.lower() == "true":
                    eventos.append(
                        (utc_time, name, value)
                    )

    return eventos


SECRET_FILE = "camara.secret"
CAMERA_NAME = "Camara2"

with open(SECRET_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

camera = config[CAMERA_NAME]

print("Conectando...")

cam = ONVIFCamera(
    camera["ip"],
    camera["port"],
    camera["user"],
    camera["password"]
)

print("Conexión OK")

print("URL del stream:", obtener_stream_urls(cam))


pullpoint = crear_pullpoint(cam)


while True:

    try:

        eventos = leer_eventos(pullpoint)

        for utc_time, name, value in eventos:
            print(f"{utc_time} - {name} = {value}")

        print("Esperando eventos...")

    except Exception as e:

        print("ERROR:", e)
        print("El PullPoint puede haberse desconectado.")

        time.sleep(2)

        pullpoint = crear_pullpoint(cam)