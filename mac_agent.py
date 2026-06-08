import asyncio
import json
import time
from io import BytesIO

import mss
from PIL import Image
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
import websockets


HOST = "0.0.0.0"
PORT = 8765
TOKEN = "change-this-token"
FPS = 12
JPEG_QUALITY = 55

mouse = MouseController()
keyboard = KeyboardController()


def grab_screen_jpeg() -> bytes:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        raw = sct.grab(monitor)

        img = Image.frombytes("RGB", raw.size, raw.rgb)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY)
        return buf.getvalue()


def handle_input(event: dict):
    print("INPUT:", event, flush=True)
    event_type = event.get("type")

    if event_type == "mouse_move":
        mouse.position = (int(event["x"]), int(event["y"]))

    elif event_type == "mouse_click":
        button = Button.left if event.get("button") == "left" else Button.right
        mouse.position = (int(event["x"]), int(event["y"]))
        mouse.click(button)

    elif event_type == "mouse_scroll":
        mouse.scroll(int(event.get("dx", 0)), int(event.get("dy", 0)))

    elif event_type == "key":
        key = event.get("key")

        special = {
            "enter": Key.enter,
            "esc": Key.esc,
            "backspace": Key.backspace,
            "tab": Key.tab,
            "space": Key.space,
            "up": Key.up,
            "down": Key.down,
            "left": Key.left,
            "right": Key.right,
        }

        k = special.get(key.lower(), key)

        keyboard.press(k)
        keyboard.release(k)


async def screen_sender(ws):
    delay = 1.0 / FPS

    while True:
        start = time.time()
        frame = grab_screen_jpeg()
        await ws.send(frame)

        elapsed = time.time() - start
        await asyncio.sleep(max(0, delay - elapsed))


async def input_receiver(ws):
    async for msg in ws:
        try:
            event = json.loads(msg)
            handle_input(event)
        except Exception as e:
            print(f"Input error: {e}")


async def handler(ws):
    auth_msg = await ws.recv()

    try:
        auth = json.loads(auth_msg)
    except Exception:
        await ws.close()
        return

    if auth.get("token") != TOKEN:
        await ws.close()
        return

    print("Client connected")

    sender = asyncio.create_task(screen_sender(ws))
    receiver = asyncio.create_task(input_receiver(ws))

    done, pending = await asyncio.wait(
        [sender, receiver],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    print("Client disconnected")


async def main():
    async with websockets.serve(
        handler,
        HOST,
        PORT,
        max_size=None,
        ping_interval=10,
        ping_timeout=10,
    ):
        print(f"Mac agent listening on {HOST}:{PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
