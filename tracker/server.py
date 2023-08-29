import eventlet
import datetime
import re
from flask import (
    Blueprint,
    Flask,
    copy_current_request_context,
    send_file,
    request,
)
from flask_socketio import SocketIO, emit
from config import config
from dwm import Dwm
from vision import TagTracker

DEBUG = config["flask_debug"]

app = Flask(__name__, static_url_path="/")
socketio = SocketIO(app, async_mode="eventlet")


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

dwm: Dwm | None = None
tag_tracker = TagTracker()


@api.post("start")
def start_recording_mqtt_data():
    try:

        @copy_current_request_context
        def start_dwm():
            global dwm
            if dwm is None:
                dwm = Dwm()
            dwm.start(
                on_message=lambda data: emit(
                    "dwm-message", data, namespace="/", broadcast=True
                )
            )
            tag_tracker.start(
                on_location=lambda loc: emit("vision-location", loc),
                on_frame=lambda frame: emit(
                    "vision-frame", frame, namespace="/", broadcast=True
                ),
            )

        eventlet.spawn(start_dwm)
        emit("x")
        return "started", 200

    except Exception:
        return "Can't connecto to MQTT server", 500


@api.post("end")
def end_recording_mqtt_data():
    tag_tracker.stop()
    global dwm
    if dwm is not None:
        df = dwm.stop()
        now = datetime.datetime.now().isoformat(timespec="seconds").replace(":", "_")
        return send_file(
            Dwm.df_to_excel(df),
            download_name=f"distance-log-{now}.xlsx",
            as_attachment=True,
        )
    else:
        return "", 200


app.register_blueprint(api)

if __name__ == "__main__":
    socketio.run(app, debug=DEBUG)
