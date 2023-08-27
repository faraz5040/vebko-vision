import base64
import re
from collections import namedtuple
import json
import os
import random
import datetime
from io import BytesIO
from threading import Thread
from paho.mqtt import client as mqtt_client
import pandas as pd
import keyboard
from config import config

DEBUG = config["mqtt_debug"]

DistTuple = namedtuple("AnchorDistance", ("AnchorId", "DistanceMillimeters"))


class Dwm:
    topic_re = re.compile(
        r"^dwm/node/(?P<node_id>[a-fA-F0-9]+)/uplink/(?P<message_type>location|data)$"
    )

    def __init__(self, listening_topics="dwm/#"):
        self.client_id = f"mqtt-{random.randint(0, 1000)}"
        self.client = None
        self.thread = None
        self.listening_topics = listening_topics

        self.positions: list[dict] = []
        self.distances: list[dict] = []

    def _start(self, on_message):
        self.positions.clear()
        self.distances.clear()
        self.client = mqtt_client.Client(self.client_id)
        self.client.username_pw_set(config["mqtt_user"], config["mqtt_password"])
        self.client.on_message = lambda *args: on_message(self.on_message(*args))
        self.client.connect(config["mqtt_server"], config["mqtt_port"])
        self.client.subscribe(self.listening_topics)
        self.client.loop_start()

    def start(self, on_message):
        self.stop()
        self.thread = Thread(target=self._start, args=(on_message,))
        self.thread.run()

    def stop(self):
        if self.client is not None and self.client.is_connected():
            self.client.loop_stop()
            self.client.unsubscribe(self.listening_topics)
            self.client.disconnect()

        if self.thread is not None and self.thread.is_alive():
            self.thread.join()
        return self.merge_dataframes()

    def on_message(
        self, _client: mqtt_client.Client, _userdata, message: mqtt_client.MQTTMessage
    ):
        if DEBUG:
            print(f"Received `{message.payload}` from `{message.topic}` topic")

        payload: dict = json.loads(message.payload)
        match = self.topic_re.fullmatch(message.topic)

        if match is None:
            return

        node_id = match.group("node_id")
        message_type = match.group("message_type")

        if message_type == "location":
            return self.handle_position_message(node_id, payload)

        if message_type == "data":
            return self.handle_data_message(node_id, payload)

    def handle_data_message(self, node_id, payload):
        bytes = base64.b64decode(payload["data"])
        count = bytes[0]
        timestamp = int.from_bytes(bytes[1:5], "little")
        bytes = bytes[5:]
        dists = (self.parse_anchor_distance(bytes, 6 * i) for i in range(count))

        if DEBUG:
            dists_fmt = {hex(id): f"{dist}mm" for id, dist in dists}
            print(
                f"node: {node_id}, count: {count}, {dists_fmt}, time (ms): {timestamp}"
            )

        row = {
            "superFrameNumber": payload["superFrameNumber"],
            "Tag": node_id,
            "Number of Anchors": count,
            "Time (ms)": timestamp,
            **dists,
        }

        self.distances.append(row)
        return row

    def handle_position_message(self, node_id, payload):
        position = payload["position"]
        position["superFrameNumber"] = payload["superFrameNumber"]
        for dim in ("x", "y", "z"):
            position[dim] = round(float(position[dim]), 2)
        position["Tag"] = node_id
        self.positions.append(position)
        return position

    def parse_anchor_distance(bytes: bytes, offset: int) -> DistTuple:
        # First 2 bytes
        anchor_id = int.from_bytes(bytes[offset : offset + 2], "little")
        # Next 4 bytes
        distance_millimiters = int.from_bytes(bytes[offset + 2 : offset + 6], "little")
        return DistTuple(anchor_id, distance_millimiters)

    def merge_dataframes(self):
        if len(self.positions) == 0 or len(self.distances) == 0:
            return pd.DataFrame()

        loc_df = pd.DataFrame(self.positions)
        dst_df = pd.DataFrame(self.distances)
        print(loc_df.columns)
        print(dst_df.columns)

        self.positions.clear()
        self.distances.clear()
        combined_df = pd.merge(loc_df, dst_df, how="outer", on=["superFrameNumber"])
        combined_df = combined_df.loc[combined_df["time"] - combined_df["time2"] < 500]
        combined_df.drop(["time2", "superFrameNumber"])
        combined_df.index += 1
        return combined_df

    def df_to_excel(df: pd.DataFrame):
        in_memory_file = BytesIO()
        xlwriter = pd.ExcelWriter(in_memory_file, engine="xlsxwriter")
        df.to_excel(xlwriter)
        xlwriter.close()
        in_memory_file.seek(0)
        return in_memory_file


def main():
    print("Press 'Esc' key to exit.")
    dwm = Dwm()
    dwm.start(print)

    while True:
        if not keyboard.is_pressed("esc"):
            continue

        log = dwm.stop()
        num_tag = log["Tag"].nunique()
        num_anch = log["Number of Anchors"].iloc[0]
        file_name = (
            f"log_{datetime.datetime.now().isoformat()}_{num_tag}_{num_anch}.xlsx"
        )
        outdir = "./logs"
        if not os.path.exists(outdir):
            os.mkdir(outdir)
        full_path = os.path.join(outdir, file_name)
        log.to_excel(full_path)
        print(log)
        print(file_name)
        break


if __name__ == "__main__":
    main()
