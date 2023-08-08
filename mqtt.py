import random
import json
import base64
import numpy as np
from paho.mqtt import client as mqtt_client


broker = "192.168.1.48"
port = 1883
username = "dwmuser"
password = "dwmpass"
# topic = "dwm/node/+/uplink/data"
topic = "#"
client_id = f"mqtt-{random.randint(0, 1000)}"


def main():
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()


def connect_mqtt():
    def on_connect(client: mqtt_client.Client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    # Set Connecting Client ID
    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


def subscribe(client: mqtt_client.Client):
    def on_message(client, userdata, msg):
        payload = json.loads(msg.payload)

        if "position" in payload:
            pos = payload["position"]
            del pos["quality"]
            for dim in ("x", "y", "z"):
                pos[dim] = round(float(pos[dim]), 2)
            print(pos)
        elif "data" in payload:
            bytes = base64.b64decode(payload["data"])
            count = bytes[0]
            data = {
                hex(
                    int.from_bytes(bytes[1 + 6 * i : 3 + 6 * i], "little")
                ): int.from_bytes(bytes[3 + 6 * i : 7 + 6 * i], "little")
                for i in range(count)
            }
            print(f"node: {msg.topic[9:13]}, count: {count}, {data}")
            print(data)
        else:
            print(f"Received `{payload}` from `{msg.topic}` topic")

    client.subscribe(topic)
    client.on_message = on_message


if __name__ == "__main__":
    main()
