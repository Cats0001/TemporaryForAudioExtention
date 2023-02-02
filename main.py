import time
import sys
import pyaudio
import websocket
import requests
from base64 import b64encode

HOST = "rust.gdodge.dev"
AUTH = "keyHere"
AUTH_URL = "https://rust.gdodge.dev/socket_auth"


class AudioStreamer:
    def __init__(self, host, auth, auth_url):
        self.auth_url = auth_url
        self.host = host
        self.auth = auth
        self.CHUNK = 1024 * 4

        self.ws = self.configure_websocket()
        self.p, self.stream = self.start_microphone_stream()

    def configure_websocket(self):
        payload = {
            "key": self.auth
        }
        auth_req = requests.post(self.auth_url, data=payload)

        if auth_req.status_code != 200:
            raise Exception(f'Authentication failed w/ status {auth_req.status_code}')

        socket_key = auth_req.cookies["X-Authorization"]

        ws = websocket.WebSocket()
        ws.connect("ws://rust.gdodge.dev/audio_stream",
                   cookie=f"X-Authorization={socket_key}")

        return ws

    def start_microphone_stream(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1 if sys.platform == 'darwin' else 2,
                        rate=44100,
                        input=True,
                        output=True,
                        frames_per_buffer=self.CHUNK)

        return p, stream

    def send_data(self):
        queued_data = self.stream.read(self.CHUNK)
        encoded_data = str(b64encode(queued_data))
        self.ws.send(encoded_data)

    def cleanup(self):
        self.stream.close()
        self.ws.close()
        self.p.terminate()


if __name__ == "__main__":
    error_count = 0
    while error_count < 3:
        streamer = None
        try:
            streamer = AudioStreamer(HOST, AUTH, AUTH_URL)
            class_running = True
            while class_running:
                streamer.send_data()
                error_count = 0  # reset counter if successful
                time.sleep(0.05)
        except Exception as e:
            print(f'Encountered exception {e}')
            if streamer:
                streamer.cleanup()  # close and reconnect
            error_count += 1

    print('Exceeded error count')
