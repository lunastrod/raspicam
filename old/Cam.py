import json
from onvif import ONVIFCamera
import requests
import ffmpeg
import datetime
import os

import lxml.etree as etree

# --- Configuration ---
SECRET_FILE = 'camara.secret'
CAMERA="Camara2"
"""
{
  "Ejemplo": {
    "ip": "192.168.1.150",
    "port": 2020,
    "user": "user",
    "password": "password"
  }
}
"""
# ---------------------
class Cam:
    def __init__(self,name):
        self.output_dir = "img"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)


        self.extract_secret(name)
        print("ip:",self.ip," port:",self.port," user:",self.user," password:",self.password)
        self.cam = ONVIFCamera(self.ip, self.port, self.user, self.password)
        self.connect_camera()
        self.media_service = self.cam.create_media_service()
        self.profiles = self.media_service.GetProfiles()
        self.generate_uri()
        print(self.stream_uri)
        #self.events_service = self.cam.create_events_service()
        #self.print_event_xml()
        #self.suscribe_event('tns1:RuleEngine/CellMotionDetector/Motion','IsMotion')

    def extract_secret(self,name):
        try:
            with open(SECRET_FILE, 'r') as f:
                secrets = json.load(f)
                self.ip=secrets[name]["ip"]
                self.port=secrets[name]["port"]
                self.user=secrets[name]["user"]
                self.password=secrets[name]["password"]
                
        except FileNotFoundError:
            print(f"Error: Secret file '{SECRET_FILE}' not found in the current directory.")
            return
        except json.JSONDecodeError:
            print(f"Error: Secret file '{SECRET_FILE}' is not valid JSON.")
            return
        except Exception as e:
            print(f"Error parsing credentials from secret file: {e}")
            print("Ensure the file is exactly like: {\"myusername\": \"mypassword\"}")
            return

    def connect_camera(self):
        try:
            device_info = self.cam.devicemgmt.GetDeviceInformation()
            
            print(f"Model: {device_info.Model}",f" Firmware: {device_info.FirmwareVersion}")
        except Exception as e:
            print(f"Connection failed. Error: {e}")
            print("Please verify the IP, Port, Username, and Password, and check for WSDL errors.")

    def generate_uri(self):
        try:
            profile_token = self.profiles[0]["token"]

            params = self.media_service.create_type('GetStreamUri')
            params.ProfileToken = profile_token
            params.StreamSetup = {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'TCP'}}


            
            stream_uri_obj = self.media_service.GetStreamUri(params)
            raw_uri = stream_uri_obj.Uri
            raw_uri=raw_uri.split('rtsp://')
            self.stream_uri="rtsp://"+self.user+":"+self.password+"@"+raw_uri[1]             
        except Exception as e:
            print(f"Error retrieving snapshot URI: {e}")

    def take_picture(self):
        #pide video a la camara, el frame 0.5s despues es el que se guarda
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"image_{timestamp}.jpg")
        try:
            (
                ffmpeg
                .input(self.stream_uri,ss=0.5)
                .output(filename=filename,vframes=1,vcodec='mjpeg')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except Exception as e:
            print(f"Error taking picture: {e}")
        return filename
    """
    def print_event_xml(self):
        try:
            properties = self.events_service.GetEventProperties()
            rule_engine_element = properties.TopicSet._value_1[0]
            print(type(rule_engine_element))

            raw_xml_string = etree.tostring(
                rule_engine_element, 
                pretty_print=True, 
                encoding=str
            )
            print(raw_xml_string)
        except Exception as e:
            print(f"Error retrieving events: {e}")
    """
    """
    def suscribe_event(self, topic, attr):
            topic_expression = self.events_service.create_type('wsnt:TopicExpression')
            topic_expression.Dialect = 'http://www.onvif.org/ver10/tev/topicExpression/ConcreteSet'
            topic_expression._value_1 = topic
            topic_expression._attr_1 = attr
            sub_request = event_service.create_type('CreatePullPointSubscription')
            sub_request.InitialTerminationTime = 'PT5M'
            sub_request.Filter = sub_request.create_type('FilterType')
            sub_request.Filter.TopicExpression = topic_expression
            pull_point_response = event_service.CreatePullPointSubscription(sub_request)
            pull_point_manager = self.cam.create_pullpoint_service(
                pull_point_response.SubscriptionReference.Address
            )
            pull_request = pull_point_manager.create_type('PullMessages')
            pull_request.Timeout = 10
            pull_request.MessageLimit = 10
    """

            
    
def main():
    c=Cam(CAMERA)
    c.take_picture()

if __name__ == '__main__':
    main()