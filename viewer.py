import asyncio
import json
import threading

import cv2
import numpy as np
import websockets


MAC_IP = "192.168.1.50"
PORT = 8765
TOKEN = "change-this-token"

WINDOW = "Python Remote Mac Viewer"

latest_mouse = {"x": 0, "y": 0}
event_queue = asyncio.Queue()


def mouse_callback(event, x, y, flags, param):
    latest_mouse["x"] = x
    latest_mouse["y"] = y

    if event == cv2.EVENT_MOUSEMOVE:
        param.call_soon_threadsafe(
            event_queue.put_nowait,
            {"type": "mouse_move", "x": x, "y": y},
        )

    elif event == cv2.EVENT_LBUTTONDOWN:
        param.call_soon_threadsafe(
            event_queue.put_nowait,
            {"type": "mouse_click", "button": "left", "x": x, "y": y},
        )

    elif event == cv2.EVENT_RBUTTONDOWN:
        param.call_soon_threadsafe(
            event_queue.put_nowait,
            {"type": "mouse_click", "button": "right", "x": x, "y": y},
        )


async def send_events(ws):
    while True:
        event = await event_queue.get()
        await ws.send(json.dumps(event))


async def viewer():
    uri = f"ws://{MAC_IP}:{PORT}"

    async with websockets.connect(uri, max_size=None) as ws:
        await ws.send(json.dumps({"token": TOKEN}))

        loop = asyncio.get_running_loop()

        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(WINDOW, mouse_callback, loop)

        sender = asyncio.create_task(send_events(ws))

        try:
            async for frame_bytes in ws:
                data = np.frombuffer(frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(data, cv2.IMREAD_COLOR)

                if frame is None:
                    continue

                cv2.imshow(WINDOW, frame)

                key = cv2.waitKey(1) & 0xFF

                if key == 27:
                    break

                elif key in (13, 10):
                    await event_queue.put({"type": "key", "key": "enter"})

                elif key == 8:
                    await event_queue.put({"type": "key", "key": "backspace"})

                elif key == 9:
                    await event_queue.put({"type": "key", "key": "tab"})

                elif 32 <= key <= 126:
                    await event_queue.put({"type": "key", "key": chr(key)})

        finally:
            sender.cancel()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    asyncio.run(viewer())
