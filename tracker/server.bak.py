import eventlet

eventlet.monkey_patch()
import datetime
import re
from flask import (
    Blueprint,
    Flask,
    copy_current_request_context,
    send_file,
    request,
)

# from uwsgidecorators import thread
from flask_executor import Executor
from flask_socketio import SocketIO, emit
from config import config

# from dwm import Dwm
from vision import TagTracker

DEBUG = config["api_debug"]

app = Flask(__name__, static_url_path="/")
socketio = SocketIO(app, cors_allowed_origins="*")
executor = Executor(app)

static_file_re = re.compile(r"\.(?:js|css|html|svg|png|jpe?g|ttf|woff2?|json)$")


@app.get("/")
def index():
    return app.send_static_file("index.html")


# Any file in assets subtree or files directly inside root folder
@app.get("/<string:filename>")
@app.get("/assets/<path:filename>")
def static_proxy(filename):
    if request.path.startswith("/assets/"):
        filename = f"assets/{filename}"
    if not static_file_re.search(filename):
        filename = "index.html"
    return app.send_static_file(filename)


@app.get("/<path:path>")
def spa_not_found_redirect(path):
    return app.send_static_file("index.html")


api = Blueprint("API", __name__, url_prefix="/api")

# dwm = Dwm()
tag_tracker = TagTracker()


def emit_cb(event_name):
    def cb(*args, **kwargs):
        socketio.emit(event_name, *args, namespace="/", **kwargs)

    return cb


@api.post("start")
async def start_recording_mqtt_data():
    # try:
    # @copy_current_request_context
    # @thread
    # def start_dwm():
    # dwm.start(
    #     on_message=lambda data: socketio.emit(
    #         "dwm-message", data, namespace="/", broadcast=True
    #     )
    # )
    eventlet.spawn(
        tag_tracker.start,
        on_location=emit_cb("vision-location"),
        # on_frame=emit_cb("vision-frame"),
    )

    # SocketIO.start_background_task(
    #     tag_tracker.start, on_location=emit_cb("vision-location")
    # )
    # executor.submit(start_dwm)
    socketio.emit("vision-location", {"hey": "hi"}, namespace="/")

    # eventlet.spawn(start_dwm)
    return "started", 200


# except Exception as e:
#     print(e)
#     return "Can't connecto to MQTT server", 500


@api.post("end")
async def end_recording_mqtt_data():
    tag_tracker.stop()
    return "", 200
    # df = dwm.stop()
    # if  df.empty:
    #     return "", 200

    # now = datetime.datetime.now().isoformat(timespec="seconds").replace(":", "_")
    # return send_file(
    #     Dwm.df_to_excel(df),
    #     download_name=f"distance-log-{now}.xlsx",
    #     as_attachment=True,
    # )


app.register_blueprint(api)

if __name__ == "__main__":
    socketio.run(app, debug=DEBUG)
