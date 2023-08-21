import datetime
from io import BytesIO
import re
import pandas as pd
from flask import (
    Blueprint,
    Flask,
    send_file,
    request,
)
from flask_socketio import SocketIO, emit
from dwm import Dwm


app = Flask(__name__, static_url_path="/")
socketio = SocketIO(app)


static_file_re = re.compile(r"\.(?:js|css|html|svg|png|jpe?g|ttf|woff2?|json)$")


@app.get("/")
def index():
    print("index")
    return app.send_static_file("index.html")


# Any find in assets subtree or files directly inside root folder
@app.get("/<string:filename>")
@app.get("/assets/<path:filename>")
def static_proxy(filename):
    print("static")
    if request.path.startswith("/assets/"):
        filename = f"assets/{filename}"
    if not static_file_re.search(filename):
        filename = "index.html"
    return app.send_static_file(filename)


@app.get("/<path:path>")
def spa_not_found_redirect(path):
    print("catched:", path)
    return app.send_static_file("index.html")


api = Blueprint("API", __name__, url_prefix="/api")
dwm = Dwm()


@api.post("start")
def start_recording_mqtt_data():
    try:
        dwm.start()
        return "started", 200
    except Exception:
        return "Can't connecto to MQTT server", 500


@api.post("end")
def end_recording_mqtt_data():
    return "ended"
    # _, distances = dwm.end()
    # loc_df = pd.DataFrame(locations)
    dst_df = pd.DataFrame(distances)

    in_memory_file = BytesIO()
    xlwriter = pd.ExcelWriter(in_memory_file, engine="xlsxwriter")
    dst_df.to_excel(xlwriter)
    xlwriter.save()
    xlwriter.close()
    in_memory_file.seek(0)

    now = datetime.datetime.now().isoformat()
    return send_file(
        in_memory_file.read(),
        # mimetype="xlsx",
        download_name=f"distance-log-{now}.xlsx",
        as_attachment=True,
    )
    # response = make_response(in_memory_file.read())
    # response.headers.set(
    #     "Content-Type",
    #     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # ),
    # response.headers.set("Content-Disposition", "attachment; filename=myfile.xlsx")
    # return response


app.register_blueprint(api)

if __name__ == "__main__":
    socketio.run(app, debug=True)
