"""
Where all the evdev related functions go
"""

import evdev
from evdev import ecodes
from queue import Queue

DOWN = 1
UP = 0
HOLD = 2

STOP_VALUE = 65535


def activate_device(path: str):
    current_device = None
    new_device = evdev.InputDevice(path)
    if current_device is None:
        current_device = new_device
    try:
        current_device.ungrab()
    except OSError:
        pass
    current_device = new_device
    try:
        current_device.grab()
    except OSError:
        pass
    return current_device


def release_device(path: str):
    current_device = evdev.InputDevice(path)
    if current_device is not None:
        try:
            current_device.ungrab()
        except OSError:
            pass
        return True


def syn_key_press(key: int, evqueue: Queue):
    down_event = (ecodes.EV_KEY, key, 1)
    up_event = (ecodes.EV_KEY, key, 0)
    evqueue.put(down_event)
    evqueue.put(up_event)


def syn_key_hold(key: int, evqueue: Queue):
    down_event = (ecodes.EV_KEY, key, DOWN)
    evqueue.put(down_event)
    hold_event = (ecodes.EV_KEY, key, HOLD)
    evqueue.put(hold_event)


def syn_key_release(key: int, evqueue: Queue):
    evqueue.put((ecodes.EV_KEY, key, UP))


def syn_key_activate(key: int, evqueue: Queue):
    evqueue.put((ecodes.EV_KEY, key, DOWN))
