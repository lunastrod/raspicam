import json
import os
import datetime
import ffmpeg

from onvif import ONVIFCamera
from lxml import etree


# ============================================================
# CONFIGURACIÓN
# ============================================================

SECRET_FILE = "camara.secret"
CAMERA = "Camara2"

OUTPUT_DIR = "img"


# ============================================================
# CLASE CÁMARA
# ============================================================

class Cam:

    def __init__(self, name):

        self.output_dir = OUTPUT_DIR

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # ----------------------------------------------------
        # Credenciales
        # ----------------------------------------------------

        self.extract_secret(name)

        print("\n" + "=" * 70)
        print("CONECTANDO CON LA CÁMARA")
        print("=" * 70)

        print("IP      :", self.ip)
        print("Puerto  :", self.port)
        print("Usuario :", self.user)

        # ----------------------------------------------------
        # ONVIF
        # ----------------------------------------------------

        self.cam = ONVIFCamera(
            self.ip,
            self.port,
            self.user,
            self.password
        )

        print("Conexión ONVIF: OK")

        # ----------------------------------------------------
        # Device information
        # ----------------------------------------------------

        self.print_device_information()

        # ----------------------------------------------------
        # Services
        # ----------------------------------------------------

        self.print_services()

        # ----------------------------------------------------
        # Media
        # ----------------------------------------------------

        try:
            self.media_service = (
                self.cam.create_media_service()
            )

            self.profiles = (
                self.media_service.GetProfiles()
            )

            print("\nMedia Service: OK")
            print(
                "Perfiles encontrados:",
                len(self.profiles)
            )

        except Exception as e:

            print("\nERROR inicializando Media Service:")
            print(e)

            self.media_service = None
            self.profiles = []

        # ----------------------------------------------------
        # RTSP
        # ----------------------------------------------------

        self.stream_uri = None

        if self.media_service and self.profiles:
            self.generate_uri()

    # ========================================================
    # SECRET
    # ========================================================

    def extract_secret(self, name):

        with open(SECRET_FILE, "r") as f:
            secrets = json.load(f)

        if name not in secrets:
            raise Exception(
                f"La cámara '{name}' no existe en "
                f"'{SECRET_FILE}'"
            )

        camera = secrets[name]

        self.ip = camera["ip"]
        self.port = camera["port"]
        self.user = camera["user"]
        self.password = camera["password"]

    # ========================================================
    # DEVICE INFORMATION
    # ========================================================

    def print_device_information(self):

        print("\n" + "=" * 70)
        print("DEVICE INFORMATION")
        print("=" * 70)

        try:

            info = (
                self.cam.devicemgmt
                .GetDeviceInformation()
            )

            print("Manufacturer :", info.Manufacturer)
            print("Model        :", info.Model)
            print("Firmware     :", info.FirmwareVersion)
            print("Serial       :", info.SerialNumber)
            print("Hardware ID  :", info.HardwareId)

        except Exception as e:

            print("ERROR:")
            print(e)

    # ========================================================
    # SERVICES
    # ========================================================

    def print_services(self):

        print("\n" + "=" * 70)
        print("ONVIF SERVICES")
        print("=" * 70)

        try:

            services = (
                self.cam.devicemgmt.GetServices({
                    "IncludeCapability": True
                })
            )

            for i, service in enumerate(services):

                print("\n" + "-" * 70)
                print(f"SERVICE {i}")
                print("-" * 70)

                print("Namespace:")
                print(service.Namespace)

                print("\nXAddr:")
                print(service.XAddr)

                print("\nVersion:")
                print(service.Version)

        except Exception as e:

            print("ERROR:")
            print(e)

    # ========================================================
    # RTSP URI
    # ========================================================

    def generate_uri(self):

        try:

            profile_token = self.profiles[0].token

            params = (
                self.media_service
                .create_type("GetStreamUri")
            )

            params.ProfileToken = profile_token

            params.StreamSetup = {
                "Stream": "RTP-Unicast",
                "Transport": {
                    "Protocol": "TCP"
                }
            }

            response = (
                self.media_service
                .GetStreamUri(params)
            )

            raw_uri = response.Uri

            if raw_uri.startswith("rtsp://"):

                uri_without_scheme = (
                    raw_uri[len("rtsp://"):]
                )

                self.stream_uri = (
                    "rtsp://"
                    + self.user
                    + ":"
                    + self.password
                    + "@"
                    + uri_without_scheme
                )

            else:

                self.stream_uri = raw_uri

            safe_uri = self.stream_uri.replace(
                self.password,
                "********"
            )

            print("\n" + "=" * 70)
            print("RTSP STREAM")
            print("=" * 70)

            print(safe_uri)

        except Exception as e:

            print("ERROR obteniendo RTSP:")
            print(e)

    # ========================================================
    # IMPRIMIR XML DE EVENTOS
    # ========================================================

    def print_event_xml(self):

        print("\n" + "=" * 70)
        print("ONVIF EVENT TOPICS")
        print("=" * 70)

        try:

            events_service = (
                self.cam.create_events_service()
            )

            print("Event Service: OK")

        except Exception as e:

            print("ERROR creando Event Service:")
            print(e)
            return

        # ----------------------------------------------------
        # Obtener propiedades
        # ----------------------------------------------------

        try:

            properties = (
                events_service.GetEventProperties()
            )

        except Exception as e:

            print("ERROR en GetEventProperties:")
            print(e)
            return

        # ----------------------------------------------------
        # TopicSet
        # ----------------------------------------------------

        try:

            topic_set = properties.TopicSet

            elements = topic_set._value_1

            print("\nElementos encontrados:",
                  len(elements))

            for i, element in enumerate(elements):

                print("\n" + "-" * 70)
                print(f"TOPIC ROOT {i}")
                print("-" * 70)

                # Mostrar XML completo
                xml = etree.tostring(
                    element,
                    pretty_print=True,
                    encoding="unicode"
                )

                print(xml)

        except Exception as e:

            print("ERROR leyendo TopicSet:")
            print(e)

    # ========================================================
    # RECORRER TODOS LOS TOPICS
    # ========================================================

    def print_topics_recursive(self, element, level=0):

        indent = "    " * level

        # Nombre del elemento XML
        tag = etree.QName(element).localname

        print(indent + "- " + tag)

        # Recorrer hijos
        for child in element:

            if isinstance(child.tag, str):

                self.print_topics_recursive(
                    child,
                    level + 1
                )

    # ========================================================
    # LISTAR TOPICS
    # ========================================================

    def print_topics(self):

        print("\n" + "=" * 70)
        print("TOPICS DISPONIBLES")
        print("=" * 70)

        try:

            events_service = (
                self.cam.create_events_service()
            )

            properties = (
                events_service.GetEventProperties()
            )

            topic_set = properties.TopicSet

            elements = topic_set._value_1

            for element in elements:

                self.print_topics_recursive(element)

        except Exception as e:

            print("ERROR:")
            print(e)

    # ========================================================
    # HACER FOTO
    # ========================================================

    def take_picture(self):

        if not self.stream_uri:

            print("No existe URI RTSP.")

            return None

        timestamp = (
            datetime.datetime.now()
            .strftime("%Y%m%d_%H%M%S")
        )

        filename = os.path.join(
            self.output_dir,
            f"image_{timestamp}.jpg"
        )

        try:

            (
                ffmpeg
                .input(
                    self.stream_uri,
                    ss=0.5
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

            print(
                "Imagen guardada:",
                filename
            )

            return filename

        except Exception as e:

            print("ERROR tomando foto:")
            print(e)

            return None


# ============================================================
# MAIN
# ============================================================

def main():

    camera = Cam(CAMERA)

    # Mostrar XML completo de los eventos
    camera.print_event_xml()

    # Mostrar árbol de topics
    camera.print_topics()

    # Si quieres probar la captura:
    # camera.take_picture()


if __name__ == "__main__":
    main()
