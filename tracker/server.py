import asyncio
import contextlib
import datetime
import re
import aiomqtt
from fastapi import FastAPI, BackgroundTasks, APIRouter
from fastapi.responses import FileResponse, StreamingResponse
from fastapi_socketio import SocketManager
import concurrent.futures

from config import config
from dwm import Dwm
from vision import TagTracker

DEBUG = config["api_debug"]

app = FastAPI(static_url_path="/")
socket = SocketManager(app=app)

static_file_re = re.compile(r"\.(?:js|css|html|svg|png|jpe?g|ttf|woff2?|json)$")

# app.mount("/static", StaticFiles(directory="static"), name="static")
router = APIRouter(prefix="/api")


@app.get("/", response_class=StreamingResponse)
def index():
    return StreamingResponse("index.html")


# # Any file in assets subtree or files directly inside root folder
# @app.get("/<string:filename>")
# @app.get("/assets/<path:filename>")
# def static_proxy(filename):
#     if request.path.startswith("/assets/"):
#         filename = f"assets/{filename}"
#     if not static_file_re.search(filename):
#         filename = "index.html"
#     return app.send_static_file(filename)


@app.get("/<path:path>", response_class=StreamingResponse)
def spa_not_found_redirect(path):
    return app.send_static_file("index.html")


dwm = Dwm()
tag_tracker = TagTracker()
running_status = False


def emit_cb(event_name):
    def cb(*args, **kwargs):
        return socket.emit(event_name, *args, namespace="/", **kwargs)

    return cb


async def run_dwm():
    try:
        async for _ in dwm.start(on_message=emit_cb("dwm-message")):
            pass
    except aiomqtt.error.MqttError as e:
        print(f"MQTT Error: {e}")
        dwm.stop()
        await run_dwm()


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
    print("in status")
    return running_status


@app.sio.on("start")
@router.post("/start")
async def start_recording_mqtt_data(background_tasks: BackgroundTasks):
    tag_tracker.open_video()

    background_tasks.add_task(run_dwm)
    background_tasks.add_task(
        tag_tracker.start,
        on_location=emit_cb("vision-location"),
        on_frame=emit_cb("vision-frame"),
    )
    # with concurrent.futures.ThreadPoolExecutor() as executor:
    #     executor.submit(dwm.start, on_message=emit_cb("dwm-message"))
    #     executor.submit(
    #         tag_tracker.start,
    #         on_location=emit_cb("vision-location"),
    #         on_frame=emit_cb("vision-frame"),
    #     )

    # socket.emit("vision-location", {"hey": "hi"}, namespace="/")

    running_status = True
    return "started", 200


# except Exception as e:
#     print(e)
#     return "Can't connecto to MQTT server", 500


@app.sio.on("end")
@router.post("/end", response_class=StreamingResponse)
async def end_recording_mqtt_data():
    tag_tracker.stop()
    df = dwm.stop()
    running_status = False
    if df.empty:
        raise Exception("Logs Empty")

    now = datetime.datetime.now().isoformat(timespec="seconds").replace(":", "_")
    headers = {
        "Content-Disposition": f"attachment; filename='distance-log-{now}.xlsx';"
    }
    return StreamingResponse(Dwm.df_to_excel(df), headers=headers)


app.include_router(router)
# app.register_blueprint(api)

# if __name__ == "__main__":
#     socket.run(app, debug=DEBUG)
