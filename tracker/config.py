import argparse
from dataclasses import dataclass
from typing import TypedDict
from environs import Env
from frozendict import frozendict

env = Env(expand_vars=True)
env.read_env()

ap = argparse.ArgumentParser()
ap.add_argument(
    "--mqtt-server",
    type=str,
    default="raspberrypi.local",
    help="network address of mqtt sever to connect to",
)
ap.add_argument(
    "--mqtt-port",
    type=int,
    default=1883,
    help="network port number of the mqtt server",
)
ap.add_argument(
    "--mqtt-user",
    type=str,
    default="dwmuser",
    help="username used for connecting to mqtt server",
)
ap.add_argument(
    "--mqtt-password",
    type=str,
    default="dwmpass",
    help="password used for connecting to mqtt server",
)
ap.add_argument(
    "--video-path",
    type=str,
    default="/dev/video0",
    help="video source read by image tracker",
)
ap.add_argument("--api-debug", action=argparse.BooleanOptionalAction)
ap.add_argument("--vision-debug", action=argparse.BooleanOptionalAction)
ap.add_argument("--mqtt-debug", action=argparse.BooleanOptionalAction)

args, _ = ap.parse_known_args()


class Config(TypedDict):
    mqtt_server: str
    mqtt_port: int
    mqtt_user: str
    mqtt_password: str
    video_path: str
    api_debug: bool
    vision_debug: bool
    mqtt_debug: bool


config: Config = frozendict(
    {
        "mqtt_server": env.str("MQTT_SERVER", args.mqtt_server),
        "mqtt_port": env.int("MQTT_PORT", args.mqtt_port),
        "mqtt_user": env.str("MQTT_USER", args.mqtt_user),
        "mqtt_password": env.str("MQTT_PASSWORD", args.mqtt_password),
        "mqtt_debug": env.bool("MQTT_DEBUG", args.mqtt_debug),
        "video_path": env.str("VIDEO_PATH", args.video_path),
        "api_debug": env.bool("API_DEBUG", args.api_debug),
        "vision_debug": env.bool("VISION_DEBUG", args.vision_debug),
    }
)
