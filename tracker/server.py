import asyncio
from contextlib import asynccontextmanager
import datetime
import re
from typing import Any
import aiomqtt
import janus
from fastapi import FastAPI, BackgroundTasks, APIRouter
from fastapi.responses import FileResponse, StreamingResponse
from fastapi_socketio import SocketManager
import concurrent.futures

import uvicorn

from config import config
from dwm import Dwm
from vision import TagTracker

DEBUG = config["api_debug"]

thread_shared = {"stop": False}
queue: janus.Queue[tuple[str, Any]]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global queue
    queue = janus.Queue()
    yield
    queue.close()
    await queue.wait_closed()


app = FastAPI(static_url_path="/", lifespan=lifespan)
socket = SocketManager(app=app)

static_file_re = re.compile(r"\.(?:js|css|html|svg|png|jpe?g|ttf|woff2?|json)$")

# app.mount("/static", StaticFiles(directory="static"), name="static")
router = APIRouter(prefix="/api")


@app.get("/", response_class=StreamingResponse)
def index():
    return StreamingResponse("index.html")


# Any file in assets subtree or files directly inside root folder
@app.get("/<string:filename>")
@app.get("/assets/<path:filename>")
def static_proxy(filename):
    if request.path.startswith("/assets/"):
        filename = f"assets/{filename}"
    if not static_file_re.search(filename):
        filename = "index.html"
    return app.send_static_file(filename)


@app.get("/<path:path>", response_class=StreamingResponse)
def spa_not_found_redirect(path):
    return app.send_static_file("index.html")


def dwm_thread(ctx: dict[str, bool], queue: janus.SyncQueue[tuple[str, Any]]):
    async def run():
        dwm = Dwm()
        try:
            await dwm.start(on_message=lambda msg: queue.put(("dwm-message", msg)))
        except aiomqtt.error.MqttError as e:
            print(f"MQTT Error: {e}")
            await dwm.stop()
        while not ctx.get("stop", False):
            await asyncio.sleep(0)
        df = await dwm.stop()
        queue.put(("dwm-dataframe", df))

    asyncio.run(run())


def tracker_thread(
    tag_tracker: TagTracker,
    ctx: dict[str, bool],
    queue: janus.SyncQueue[tuple[str, Any]],
):
    def on_frame(msg):
        queue.put(("vision-frame", msg))

    def on_location(msg):
        queue.put(("vision-location", msg))

    async def run():
        await tag_tracker.start(on_frame=on_frame, on_location=on_location)
        while not ctx.get("stop", False):
            await asyncio.sleep(0)
        tag_tracker.stop()

    asyncio.run(run())


async def listen_queue(ctx: dict[str, bool], queue: janus.AsyncQueue[tuple[str, Any]]):
    while not ctx.get("stop", False):
        msg_type, msg_payload = await queue.get()
        if msg_type == "stop":
            break
        await socket.emit(msg_type, msg_payload, namespace="/")


# async def run_dwm():
#     try:
#         async for _ in dwm.start(on_message=emit_cb("dwm-message")):
#             pass
#     except aiomqtt.error.MqttError as e:
#         print(f"MQTT Error: {e}")
#         dwm.stop()
#         await run_dwm()


# @contextlib.asynccontextmanager
# async def lifespan(app):
#     async with aiomqtt.Client("test.mosquitto.org") as c:
#         # Make client globally available
#         client = c
#         # Listen for MQTT messages in (unawaited) asyncio task
#         loop = asyncio.get_event_loop()
#         task = loop.create_task(listen(client))
#         yield
#         # Cancel the task
#         task.cancel()
#         # Wait for the task to be cancelled
#         try:
#             await task
#         except asyncio.CancelledError:
#             pass


@app.sio.on("status")
def get_status(sid):
    global thread_shared
    print("in status")
    return thread_shared.get("stop", False)


@router.post("/start")
async def start_recording_mqtt_data(background_tasks: BackgroundTasks):
    global queue
    global thread_shared
    tag_tracker = TagTracker()
    tag_tracker.open_video()

    thread_shared["stop"] = False

    with concurrent.futures.ThreadPoolExecutor() as executor:
        thread_shared["dwm_handler"] = executor.submit(
            dwm_thread, thread_shared, queue.sync_q
        )
        thread_shared["tracker_handler"] = executor.submit(
            tracker_thread, thread_shared, queue.sync_q
        )

    background_tasks.add_task(listen_queue, thread_shared, queue.async_q)

    return "started", 200


@router.post("/end", response_class=StreamingResponse)
async def end_recording_mqtt_data():
    global queue
    global thread_shared
    thread_shared["stop"] = True
    if thread_shared.get("dwm_handler"):
        await thread_shared["dwm_handler"]
    if thread_shared.get("tracker_handler"):
        await thread_shared["tracker_handler"]

    q = queue.async_q
    await q.put(("stop", None))
    while not q.empty():
        msg_type, df = q.get_nowait()
        if msg_type != "dwm-dataframe":
            continue

        if df.empty:
            raise Exception("Logs Empty")

        now = datetime.datetime.now().isoformat(timespec="seconds").replace(":", "_")
        headers = {
            "Content-Disposition": f"attachment; filename='distance-log-{now}.xlsx';"
        }
        return StreamingResponse(Dwm.df_to_excel(df), headers=headers)

    raise Exception("Can't find dataframe")


app.include_router(router)
# app.register_blueprint(api)

# if __name__ == "__main__":
#     socket.run(app, debug=DEBUG)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
