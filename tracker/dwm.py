import asyncio
import base64
from dataclasses import dataclass
import inspect
import re
from collections import namedtuple
import json
import os
import datetime
import time
from io import BytesIO
from typing import Any, Callable
from aiomqtt import Client, Message
import pandas as pd
from pynput import keyboard
from config import config
import concurrent.futures

DEBUG = config["mqtt_debug"]
is_main = __name__ == "__main__"

@dataclass
class AnchorDistance:
    id: int
    distanceMillimeters: int


class Dwm:
    topic_re = re.compile(
        r"^dwm/node/(?P<node_id>[a-fA-F0-9]+)/uplink/(?P<message_type>location|data)$"
    )

    _task: asyncio.Task | None

    def __init__(self, listening_topics="dwm/#"):
        self.listening_topics = listening_topics
        self._stop = False
        self._task = None

        self.positions: list[dict] = []
        self.distances: list[dict] = []
        self.config = {
            "hostname": config["mqtt_server"],
            "port": config["mqtt_port"],
            "username": config["mqtt_user"],
            "password": config["mqtt_password"],
        }

    async def start(self, on_message: Callable):
        self.positions.clear()
        self.distances.clear()
        self._stop = False

        async with Client(**self.config) as client:
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(self.listen(client, on_message))

    async def listen(self, client: Client, on_message: Callable):
        async with client.messages() as messages:
            await client.subscribe(self.listening_topics)
            async for message in messages:
                if self._stop:
                    break
                on_message(self.process_message(message))

    async def stop(self):
        self._stop = True

        if self._task is not None:       
            # Cancel the task
            self._task.cancel()
            # Wait for the task to be cancelled
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        return self.merge_dataframes()

    def process_message(self, message: Message):
        if DEBUG:
            print(f"Received `{message.payload}` from `{message.topic}` topic")

        payload: dict = json.loads(message.payload)
        match = self.topic_re.fullmatch(message.topic.value)

        if match is None:
            return

        node_id = match.group("node_id")
        message_type = match.group("message_type")

        if message_type == "location":
            return self.handle_position_message(node_id, payload)

        if message_type == "data":
            return self.handle_data_message(node_id, payload)

    def handle_data_message(self, node_id, payload: dict):
        bytes = base64.b64decode(payload["data"])
        count = bytes[0]
        timestamp = int.from_bytes(bytes[1:5], "little")
        bytes = bytes[5:]
        dists = { str(d.id):d.distanceMillimeters for d in (Dwm.parse_anchor_distance(bytes, 6 * i) for i in range(count))}

        if DEBUG:
            dists_fmt = {hex(id): f"{dist}mm" for id, dist in dists.items()}
            print(
                f"node: {node_id}, count: {count}, {dists_fmt}, time (ms): {timestamp}"
            )

        row = {
            "superFrameNumber": payload["superFrameNumber"],
            "Tag": node_id,
            "Number of Anchors": count,
            "Time (ms)": timestamp,
            "l_time": time.time(),
            **dists,
        }

        self.distances.append(row)
        return row

    def handle_position_message(self, node_id, payload: dict) -> dict[str, Any]:
        position = payload["position"]
        position["superFrameNumber"] = payload["superFrameNumber"]
        for dim in ("x", "y", "z"):
            position[dim] = round(float(position[dim]), 2)
        position["Tag"] = node_id
        position["r_time"] = time.time()
        self.positions.append(position)
        return position

    @staticmethod
    def parse_anchor_distance(bytes: bytes, offset: int) -> AnchorDistance:
        # First 2 bytes
        anchor_id = int.from_bytes(bytes[offset : offset + 2], "little")
        # Next 4 bytes
        distance_millimiters = int.from_bytes(bytes[offset + 2 : offset + 6], "little")
        return AnchorDistance(anchor_id, distance_millimiters)

    def merge_dataframes(self):
        if len(self.positions) == 0 or len(self.distances) == 0:
            return pd.DataFrame()

        loc_df = pd.DataFrame(self.positions)
        dst_df = pd.DataFrame(self.distances)

        self.positions.clear()
        self.distances.clear()
        combined_df = pd.merge(
            loc_df, dst_df, how="outer", on=["superFrameNumber", "Tag"]
        )
        combined_df = combined_df.loc[
            (combined_df["l_time"] - combined_df["r_time"]).abs() < 0.5
        ]
        # combined_df.drop(["r_time"], inplace=True)
        # combined_df.drop(["superFrameNumber"], inplace=True)
        combined_df.index += 1
        return combined_df

    def df_to_excel(df: pd.DataFrame):
        in_memory_file = BytesIO()
        xlwriter = pd.ExcelWriter(in_memory_file, engine="xlsxwriter")
        df.to_excel(xlwriter)
        xlwriter.close()
        in_memory_file.seek(0)
        return in_memory_file


def on_exit(key: keyboard.Key, dwm: Dwm):
    if key != keyboard.Key.esc:
        return

    log = asyncio.get_running_loop().run_until_complete(dwm.stop())
    num_tag = log["Tag"].nunique()
    num_anch = log["Number of Anchors"].iloc[0]
    file_name = f"log_{datetime.datetime.now().isoformat()}_{num_tag}_{num_anch}.xlsx"
    outdir = "./logs"
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    full_path = os.path.join(outdir, file_name)
    log.to_excel(full_path)
    print(log)
    print(file_name)


async def main():
    dwm = Dwm()
    await dwm.start(on_message=print)
    print("Press 'Esc' key to exit.")
    await asyncio.sleep(10)
    await dwm.stop()
    # asyncio.get_running_loop().run_forever()
    # while True:
    #     pass
    # listener = keyboard.Listener(on_press=lambda key: on_exit(key, dwm))
    # listener.start()



if is_main:
    asyncio.run(main())
