"""
Where all the evdev related functions go
"""

from time import sleep
import evdev
from evdev import ecodes, InputDevice
from queue import Queue
from .misc import LostDeviceError


DOWN = 1
UP = 0
HOLD = 2

OFF = 0
ON = 1
STOP_VALUE = 65535
STOCK_LEDS = [
    (ecodes.LED_NUML, OFF),
    (ecodes.LED_CAPSL, OFF),
    (ecodes.LED_SCROLLL, OFF),
]
from .misc import ContextDict


def default_evread(e: evdev.KeyEvent, ctx: ContextDict):

    if e.scancode == ecodes.KEY_UP:
        ctx.evqueue.put((ecodes.EV_KEY, ecodes.KEY_W, e.keystate))
    if e.scancode == ecodes.KEY_DOWN:
        ctx.evqueue.put((ecodes.EV_KEY, ecodes.KEY_S, e.keystate))
    if e.scancode == ecodes.KEY_LEFT:
        ctx.evqueue.put((ecodes.EV_KEY, ecodes.KEY_A, e.keystate))
    if e.scancode == ecodes.KEY_RIGHT:
        ctx.evqueue.put((ecodes.EV_KEY, ecodes.KEY_D, e.keystate))


## LED idle loop for anti cheat circumvention, and asthetics
## TODO: Make the time interval a gaussian distribution around mu of 0.25
## will make it slightly faster, in most cases
def leds_loop(dev: InputDevice, hack: bool):
    leds = dev.leds(verbose=True)
    if not hack:
        for light in reversed(leds):
            try:
                dev.set_led(ecodes.ecodes[light[0]], ON)
            except OSError as e:
                raise LostDeviceError("Lost device")
            sleep(0.25)
            try:
                dev.set_led(ecodes.ecodes[light[0]], OFF)
            except OSError as e:
                raise LostDeviceError("Lost Device")
            sleep(0.25)
    else:
        for light in reversed(STOCK_LEDS):
            try:
                dev.set_led(light[0], ON)
            except OSError:
                raise LostDeviceError("Lost Device")
            sleep(0.25)
            try:
                dev.set_led(light[0], OFF)
            except OSError:
                raise LostDeviceError("Lost Device")
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
