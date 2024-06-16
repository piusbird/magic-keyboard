"""
Where all the evdev related functions go
"""
from time import sleep
import evdev
from evdev import ecodes, InputDevice
from queue import Queue

DOWN = 1
UP = 0
HOLD = 2

OFF = 0
ON = 1
STOP_VALUE = 65535
STOCK_LEDS = [(ecodes.LED_NUML, OFF), (ecodes.LED_CAPSL, OFF ), (ecodes.LED_SCROLLL, OFF)]

def leds_loop(dev: InputDevice, hack: bool):
    leds = dev.leds(verbose=True)
    if not hack:
        for light in reversed(leds):
            dev.set_led(ecodes.ecodes[light[0]], ON)
            sleep(0.25)
            dev.set_led(ecodes.ecodes[light[0]], OFF)
            sleep(0.25)
    else:
        for light in reversed(STOCK_LEDS):
            dev.set_led(light[0], ON)
            sleep(0.25)
            dev.set_led(light[0], OFF)
            sleep(0.20)



def activate_device(path: str):
    current_device = None
    new_device = evdev.InputDevice(path)
    if current_device is None:
        current_device = new_device
    try:
        current_device.ungrab()
    except OSError:
        False
    current_device = new_device
    try:
        current_device.grab()
    except OSError:
        False
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
