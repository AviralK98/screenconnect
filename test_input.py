from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
import time

mouse = MouseController()
keyboard = KeyboardController()

print("Starting in 3 seconds...")
time.sleep(3)

mouse.position = (300, 300)
mouse.click(Button.left)

keyboard.press(Key.cmd)
keyboard.press(" ")
keyboard.release(" ")
keyboard.release(Key.cmd)
