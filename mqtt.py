import base64
import json
import os
import sys
import random

from aiomqtt import Client
import pandas as pd
import numpy as np
import keyboard
import asyncio

# ip address for connecting to raspberry
broker = "192.168.1.48"     # or raspberry
port = 1883
username = "dwmuser"
password = "dwmpass"

""" 
topic is the format which knows how to receive a message.
all messages will start with dwm/
this topic only receive messages (because of /uplink/) and downlink send message
"""
topic = "dwm/node/+/uplink/#"
client_id = f"mqtt-{random.randint(0, 1000)}"

pos_df = pd.DataFrame()     # saves positions (x, y, z, ...)
data_df = pd.DataFrame()    # saves ranges (distances)


# this function change device to tag/anchor
async def change_device(client: Client, hex_name, change_code):
    send_topic = f"dwm/node/{hex_name}/downlink/data"
    byte = change_code.to_bytes(1, byteorder='little')
    base64_encoded = base64.b64encode(byte).decode('utf8')
    payload = json.dumps({"data": base64_encoded})
    await client.publish(topic=send_topic, payload=payload)


""" this function handles errors occurs in multi-tag saving data, it will concat frame_number with respective tag name
    because multiple tags will have same frame_number so it will distinct them
"""
def grouping_frame_tag(dataframe: pd.DataFrame):
    try:
        pos_frame_grouped = dataframe.groupby('superFrameNumber')
        pos_groups = pos_frame_grouped.groups

        pos_frame_tag = np.zeros(len(dataframe), dtype='object')
        for frame, indexes in pos_groups.items():
            for ind in indexes:
                pos_frame_tag[ind] = (str(frame) + dataframe['Tag'].iloc[ind][-2:])

        dataframe['frame_tag'] = pos_frame_tag
    except Exception as err:
        print("Exception in grouping. Error:", err)

    return dataframe


# saves data in an excel file
def save_data():
    global pos_df, data_df
    pos_df = grouping_frame_tag(pos_df)
    data_df = grouping_frame_tag(data_df)

    log = pd.merge(data_df, pos_df)
    log['Time (ms)'] = log.groupby('Tag')['Time (ms)'].transform(lambda x: x - x.min()) / 1000

    log.drop(columns=['superFrameNumber'], inplace=True)
    log.drop(columns=['frame_tag'], inplace=True)

    log = log.drop(log.columns[log.isna().sum() / len(log) > 0.9], axis=1)
    log.dropna(inplace=True)

    log.rename(columns={'x': 'X', 'y': 'Y', 'z': 'Z', 'quality': 'Quality'}, inplace=True)
    log.index = log.index + 1

    num_tag = log['Tag'].nunique()
    num_anch = log['Number of Anchors'].iloc[1]
    rand_num = random.randint(1, 100000)

    file_name = f'log_{num_tag}_{num_anch}_{rand_num}.xlsx'
    outdir = './logs'
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    full_path = os.path.join(outdir, file_name)
    log.to_excel(full_path)
    print(log)
    print(file_name)


stop = False

# receives and sends messages with mqtt
async def subscribe(client: Client):
    global stop
    async with client.messages() as messages:
        await client.subscribe(topic)           # waits to receive incoming messages
        async for message in messages:
            if stop:
                break
            try:
                # after receiving messages sends it to on_message function to further processes
                on_message(message.topic, message.payload)
            except Exception as e:
                print(f'Error processing message: "{e}"')


# this function decodes message, there are two incoming message, 1)Positions 2)Ranges
def on_message(msg_topic, payload):
    global pos_df, data_df
    node = msg_topic.value[9:13]
    payload = json.loads(payload.decode())

    # this part decodes the positions and concat to dataframe
    if "position" in payload:
        pos = {'Tag': node}

        pos.update(payload["position"])
        pos['superFrameNumber'] = payload['superFrameNumber']
        for dim in ('x', 'y', 'z'):
            pos[dim] = round(float(pos[dim]), 2)

        new_frame_num = pos['superFrameNumber']
        try:
            num_tags = pos_df['Tag'].nunique()
            while new_frame_num in pos_df.superFrameNumber.values:
                if len(pos_df[pos_df.superFrameNumber == new_frame_num]['Tag'].values) == num_tags:
                    new_frame_num += 2000
                else:
                    break

            pos['superFrameNumber'] = new_frame_num
        except Exception as error:
            print(f'Error in position {new_frame_num}, {error}')

        pos_df = pd.concat([pos_df, pd.DataFrame([pos])], ignore_index=True)

    # this part decodes data (ranges) and concat to dataframe
    elif "data" in payload:
        try:
            bytes = base64.b64decode(payload["data"])
            count = bytes[0]
            timestamp = int.from_bytes(bytes[1:5], "little")
            bytes = bytes[5:]
            data = {
                hex(
                    int.from_bytes(bytes[6 * i: 2 + 6 * i], "little")
                ): f'{int.from_bytes(bytes[2 + 6 * i: 6 * (i + 1)], "little")}mm'
                for i in range(count)
            }

            data_dict = {'superFrameNumber': payload['superFrameNumber'],
                         'Tag': node, 'Number of Anchors': count, 'Time (ms)': timestamp}
            data_dict.update(data)

            new_frame_num = data_dict['superFrameNumber']
            try:
                num_tags = data_df['Tag'].nunique()
                while new_frame_num in data_df.superFrameNumber.values:
                    if len(data_df[data_df.superFrameNumber == new_frame_num]['Tag'].values) == num_tags:
                        new_frame_num += 2000
                    else:
                        break

                data_dict['superFrameNumber'] = new_frame_num
            except Exception as error:
                print(f'Error in data {new_frame_num}, {error}')

            data_df = pd.concat([data_df, pd.DataFrame([data_dict])], ignore_index=True)
            print(f"node: {node}, count: {count}, {data}, time (ms): {timestamp}, row: {len(data_df)}")

        except Exception as err:
            print("Error in data ranges:", err)

    else:
        print(f"Received {payload} topic")


# this function saves the data if auto-positioning is called
def save_test_data():
    global data_df
    rand_num = random.randint(1, 100000)

    data_df.drop(columns=['superFrameNumber', 'Time (ms)'], inplace=True)

    file_name = f'test_{rand_num}.xlsx'
    outdir = './tests'
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    full_path = os.path.join(outdir, file_name)
    data_df.to_excel(full_path)
    print(data_df)
    print(file_name)


# this function changes device to tag, then waits for 30 second and again will change to anchor (for auto-positioning)
async def auto_position(client: Client, nodes):
    to_tag, to_anchor = 255, 10

    for node in nodes:
        await (change_device(client, node, to_tag))
        await asyncio.sleep(30)
        await (change_device(client, node, to_anchor))

    save_test_data()


# main function of program
async def main():
    global stop
    # connects to broker
    async with Client(broker, port, username=username, password=password) as client:
        future = asyncio.create_task(subscribe(client))
        print("Press 'Esc' key to exit.")

        # this numbers will be encoded and sent to firmware
        to_tag, to_anchor = 255, 10

        while True:
            await asyncio.sleep(0)

            # if tab is pressed changes the device which name is bellow to tag
            if keyboard.is_pressed('tab'):
                await (change_device(client, '0307', to_tag))
                print('changed device to tag')

            # if alt is pressed changes the device which name is bellow to anchor
            if keyboard.is_pressed('alt'):
                await (change_device(client, '0307', to_anchor))
                print('changed device to anchor')

            # if space is pressed it will start auto-positioning process with devices listed as nodes
            if keyboard.is_pressed('space'):
                print('spaced')
                nodes = ['0307', '0027', '257e', '08b9']

                # fist we change all devices to anchors
                for node in nodes:
                    await (change_device(client, node, to_anchor))

                await (auto_position(client, nodes))
                print('Auto Positioning')

            # if esc is pressed it will save the
            if keyboard.is_pressed('esc'):
                try:
                    save_data()
                except Exception as e:
                    print(f'Error saving logs: "{e}"')
                stop = True
                future.cancel()
                break


# program starts here
if __name__ == "__main__":
    if sys.platform.lower() == "win32" or os.name.lower() == "nt":
        from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy

        set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
