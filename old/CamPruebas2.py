import json
from lxml import etree
from onvif import ONVIFCamera


SECRET_FILE = "camara.secret"
CAMERA_NAME = "Camara2"


# ============================================================
# LEER CONFIGURACIÓN
# ============================================================

with open(SECRET_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

camera = config[CAMERA_NAME]


# ============================================================
# CONECTAR
# ============================================================

print("Conectando...")

cam = ONVIFCamera(
    camera["ip"],
    camera["port"],
    camera["user"],
    camera["password"]
)

print("Conexión ONVIF OK")


# ============================================================
# SERVICIO DE EVENTOS
# ============================================================

events = cam.create_events_service()

print("Servicio de eventos OK")


# ============================================================
# SUSCRIPCIÓN
# ============================================================

subscription = events.CreatePullPointSubscription()

address = subscription.SubscriptionReference.Address

pullpoint = cam.create_pullpoint_service(address)

print("Suscripción OK")
print()
print("ESPERANDO EVENTOS...")
print("Provoca movimiento delante de la cámara.")
print("Ctrl+C para salir.")
print()


# ============================================================
# ESCUCHAR
# ============================================================

while True:

    try:

        response = pullpoint.PullMessages({
            "Timeout": "PT10S",
            "MessageLimit": 20
        })

        for notification in response.NotificationMessage:

            print()
            print("=" * 80)
            print("NOTIFICACIÓN RECIBIDA")
            print("=" * 80)

            # ------------------------------------------------
            # Imprimir la estructura Python completa
            # ------------------------------------------------

            print("\n--- OBJETO PYTHON ---")
            print(notification)

            # ------------------------------------------------
            # TOPIC
            # ------------------------------------------------

            print("\n--- TOPIC ---")
            print(notification.Topic)

            # ------------------------------------------------
            # MESSAGE
            # ------------------------------------------------

            print("\n--- MESSAGE ---")
            print(notification.Message)

            # ------------------------------------------------
            # XML DEL MESSAGE
            # ------------------------------------------------

            try:

                xml = notification.Message._value_1

                print("\n--- MESSAGE XML ---")

                print(
                    etree.tostring(
                        xml,
                        pretty_print=True,
                        encoding="unicode"
                    )
                )

            except Exception as e:

                print("No se pudo convertir Message a XML:")
                print(e)

            print("=" * 80)

    except KeyboardInterrupt:

        print("\nPrograma terminado.")
        break

    except Exception as e:

        print("ERROR:")
        print(e)