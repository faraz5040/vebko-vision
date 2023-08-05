import random
from paho.mqtt import client as mqtt_client


broker = "192.168.1.144"
port = 1883
username = "dwmuser"
password = "dwmpass"
topic = "dwm/#"
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
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")

    client.subscribe(topic)
    client.on_message = on_message


if __name__ == "__main__":
    main()
