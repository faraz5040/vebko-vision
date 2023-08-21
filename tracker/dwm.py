import base64
import re
from collections import namedtuple
import json
import os
import random
from typing import Literal
from paho.mqtt import client as mqtt_client
import pandas as pd
import keyboard
import sys


DistTuple = namedtuple("AnchorDistance", ("AnchorId", "DistanceMillimeters"))


class Dwm:
    topic_re = re.compile(
        r"^dwm/node/(?P<node_id>[a-fA-F0-9]+)/uplink/(?P<message_type>location|data)$"
    )

    def __init__(
        self,
        host="192.168.1.48",
        username="dwmuser",
        password="dwmpass",
        port=1883,
        listening_topics="dwm/#",
    ):
        self.client_id = f"mqtt-{random.randint(0, 1000)}"
        self.client = mqtt_client.Client(self.client_id)
        self.client.username_pw_set(username, password)
        self.host = host
        self.port = port
        self.listening_topics = listening_topics

        self.locations: list[dict] = []
        self.distances: list[dict] = []

    def start(self, on_message):
        self.client.on_message = self.on_message
        self.locations.clear()
        self.distances.clear()
        self.client.connect(self.host, self.port)
        self.client.subscribe(self.listening_topics)
        self.client.loop_start()

    def end(self):
        self.client.loop_stop()
        self.client.unsubscribe(self.listening_topics)
        self.client.disconnect()
        return self.locations, self.distances

    def on_message(
        self, _client: mqtt_client.Client, _userdata, message: mqtt_client.MQTTMessage
    ):
        match = self.topic_re.fullmatch(message.topic)

        if match is None:
            print(f"Received `{payload}` from `{message.topic}` topic")
            return

        node_id = match.group("node_id")
        message_type = match.group("message_type")

        payload: dict = json.loads(message.payload)

        if message_type == "location":
            handle_position_message(node_id, payload)

        if message_type == "data":
            handle_data_message(node_id, payload)

    def handle_data_message(self, node_id, payload):
        bytes = base64.b64decode(payload["data"])
        count = bytes[0]
        timestamp = int.from_bytes(bytes[1:5], "little")
        bytes = bytes[5:]
        dists_int = (parse_anchor_distance(bytes, 6 * i) for i in range(count))
        dists = {hex(id): f"{dist}mm" for id, dist in dists_int}
        print(f"node: {node_id}, count: {count}, {dists}, time (ms): {timestamp}")

        self.distances.append(
            {
                "superFrameNumber": payload["superFrameNumber"],
                "Tag": node_id,
                "Number of Anchors": count,
                "Time (ms)": timestamp,
                **dists,
            }
        )

    def handle_position_message(self, node_id, payload):
        pos = payload["position"]
        pos["superFrameNumber"] = payload["superFrameNumber"]
        for dim in ("x", "y", "z"):
            pos[dim] = round(float(pos[dim]), 2)
        pos["Tag"] = node_id
        self.locations.append(pos)

    def parse_anchor_distance(bytes: bytes, offset: int) -> DistTuple:
        # First 2 bytes
        anchor_id = int.from_bytes(bytes[offset : offset + 2], "little")
        # Next 4 bytes
        distance_millimiters = int.from_bytes(bytes[offset + 2 : offset + 6], "little")
        return DistTuple(anchor_id, distance_millimiters)


def grouping_frame_tag(dataframe: pd.DataFrame):
    pos_frame_grouped = dataframe.groupby("superFrameNumber")
    pos_groups = pos_frame_grouped.groups

    pos_frame_tag = []
    for frame, indexes in pos_groups.items():
        for ind in indexes:
            pos_frame_tag.append(str(frame) + dataframe["Tag"].iloc[ind][-2:])

    dataframe["frame_tag"] = pos_frame_tag
    return dataframe


# def main():
#     global pos_df, data_df
#     print("Press 'Esc' key to exit.")

#     client = connect_mqtt()
#     subscribe(client)
#     client.loop_start()

#     while True:
#         if not keyboard.is_pressed("esc"):
#             continue

#         pos_df = grouping_frame_tag(pos_df)
#         data_df = grouping_frame_tag(data_df)

#         log = pd.merge(data_df, pos_df)
#         log["Time (ms)"] = (
#             log.groupby("Tag")["Time (ms)"].transform(lambda x: x - x.min()) / 1000
#         )
#         log.drop(columns=["superFrameNumber"], inplace=True)

#         log.rename(
#             columns={"x": "X", "y": "Y", "z": "Z", "quality": "Quality"},
#             inplace=True,
#         )
#         log.index = log.index + 1

#         num_tag = log["Tag"].nunique()
#         num_anch = log["Number of Anchors"].iloc[0]
#         rand_num = random.randint(1, 100000)

#         file_name = f"log_{num_tag}_{num_anch}_{rand_num}.xlsx"
#         outdir = "./logs"
#         if not os.path.exists(outdir):
#             os.mkdir(outdir)

#         full_path = os.path.join(outdir, file_name)
#         log.to_excel(full_path)
#         print(log)
#         print(file_name)
#         client.unsubscribe("#")
#         client.loop_stop()
#         sys.exit()


def handle_data_message(node_id, payload):
    global data_df
    bytes = base64.b64decode(payload["data"])
    count = bytes[0]
    timestamp = int.from_bytes(bytes[1:5], "little")
    bytes = bytes[5:]
    dists_int = (parse_anchor_distance(bytes, 6 * i) for i in range(count))
    dists = {hex(id): f"{dist}mm" for id, dist in dists_int}
    print(f"node: {node_id}, count: {count}, {dists}, time (ms): {timestamp}")
    data_dict = {
        "superFrameNumber": payload["superFrameNumber"],
        "Tag": node_id,
        "Number of Anchors": count,
        "Time (ms)": timestamp,
    }
    data_dict.update(dists)

    data_df.append(data_dict)
    # data_df = pd.concat([data_df, pd.DataFrame([data_dict])], ignore_index=True)


def handle_position_message(node_id, payload):
    pos = payload["position"]
    pos["superFrameNumber"] = payload["superFrameNumber"]
    for dim in ("x", "y", "z"):
        pos[dim] = round(float(pos[dim]), 2)
    pos["Tag"] = node_id

    pos_df = pd.concat([pos_df, pd.DataFrame([pos])], ignore_index=True)


# if __name__ == "__main__":
#     main()
