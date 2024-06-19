#!/usr/bin/env python3
import evdev

devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for d in devices:
    print(d)
