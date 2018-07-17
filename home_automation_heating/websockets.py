from home_automation_hub import websocket
from . import storage

ws = None

def get_instance():
    if not ws:
        raise Exception("Websocket not initialised")
    return ws

def push_state():
    ws.publish("state", {
        "ch_running": storage.get("ch_running"),
        "ch_set_on": storage.get("ch_set_on"),
    })

def initialise(module_id):
    global ws, storage
    ws = websocket.ModuleWebsocket(module_id)    