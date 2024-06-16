#!/usr/bin/env python3

# Copyright (c) 2024 Matt Arnold

# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and
# associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom
# the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice
# shall be included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE
# AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT,  TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys
import os
import queue
import tomllib
import syslog
import signal
from time import sleep
import socket
import threading
import gi

gi.require_version("Notify", "0.7")
from gi.repository import Notify, GLib
import evdev
import syslog
import multiprocessing
from evdev import InputDevice, categorize, ecodes, UInput
from mkd.ioutils import NullFile, SyslogFile
from mkd.fileutils import write_pid, pid_lock, get_config
from mkd.evdev import (
    syn_key_press,
    syn_key_hold,
    syn_key_release,
    activate_device,
    release_device,
    STOP_VALUE,
)

stop_flag = threading.Event()
evqueue = queue.Queue()
active_config = None
daemon_tmpfiles = ["~/.mkd.sock", "~/.mkd.pid"]
actual_send_notice = lambda m: Notify.Notification.new(
    "magic-keyboard", m, "dialog-information"
).show()
current_device = None


def main():
    if os.getuid() == 0 or os.geteuid == 0:
        print("Do not run me as root, add urself to input")
        exit(0x0f)
    cfig = get_config("~/.mkd.conf")
    print("Config Values")
    for k, v in cfig.items():
        print(k + ": " + v)
    print(len(sys.argv))
    if len(sys.argv) == 2:
        match sys.argv[1]:
            case 'lsdevices':
                devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
                for d in devices:
                    print(d)
            case 'foreground':
                daemon_main(cfig)
            case other:
                print("Unknown Subcommand")

        exit(0)

    pid = os.fork()

    if pid:
        os._exit(0)
    else:
        os.umask(0)
        os.setpgrp()
        if pid_lock("~/.mkd.pid"):
            print("already running")
            exit(1)

        sys.stdout = SyslogFile()
        sys.stdin.close()
        sys.stderr = NullFile()
        signal.signal(signal.SIGTERM, handle_sigterm)
        daemon_main(cfig)


def daemon_main(cfig):
    global active_config
    global current_device
    Notify.init("Magic Keyboard")
    active_config = cfig
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    if startup_proc(devices, active_config["grab_device"]):
        pidpath = os.path.expanduser("~/.mkd.pid")
        write_pid(pidpath)
    else:
        send_notice("Startup failed")
        if len(devices) == 0:
            print("Add urself to input group")
        exit(2)

    sockpath = os.path.expanduser("~/.mkd.sock")
    if os.path.exists(sockpath):
        os.unlink(sockpath)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(sockpath)
    sock.listen(1)
    do_cleanup()

    lisnr = threading.Thread(target=uds_thread, args=(sock,))
    vinput_t = threading.Thread(target=uinput_thread, args=(evqueue,))
    while not stop_flag.is_set():
        if not lisnr.is_alive():
            lisnr = threading.Thread(target=uds_thread, args=(sock,))
            lisnr.start()
        if not vinput_t.is_alive():
            vinput_t = threading.Thread(target=uinput_thread, args=(evqueue,))
            vinput_t.start()
        ## Something is releasing grab, i can't figure out what
        ## py3-evdev doesn't provide EBUSY for iograbs
        ## so we make sure we are holding the grab before we read events
        ## even though this way of doing it is a hax
        try:
            current_device.grab()
        except OSError:
            pass
        event = current_device.read_one()
        if event is not None:
            if event.type == ecodes.EV_KEY:
                dispatch_event(evdev.util.categorize(event))

    if lisnr.is_alive():
        lisnr.join()  # make sure on sigterm we clean this up
    if vinput_t.is_alive():
        vinput_t.join()
    try:
        do_cleanup()
        exit(0)
    except Exception as e:
        print(e)
        multiprocessing.current_process().kill()


def startup_proc(devices, target_device):
    global current_device
    if os.getuid() == 0 or os.geteuid() == 0:
        print("Do not run this as root")
        return False
    for d in devices:
        if d.name == target_device:
            current_device = activate_device(d.path)
    if not current_device:
        send_notice("early start failed")
        return False
    else:
        send_notice(f"{current_device.name} at {current_device.path} Activated")
        return True


def uinput_thread(evqueue):
    Notify.init("mkd Vinput")

    ui = UInput()
    send_notice("input synth ready")
    while not stop_flag.is_set():
        keydata = evqueue.get()
        if type(keydata) == int and keydata == STOP_VALUE:
            break
        ui.write(*keydata)
        ui.syn()
    ui.close()


def uds_thread(sock):
    Notify.init("Mkd Background process")
    global active_config
    global current_device
    if stop_flag.is_set():  # we don't want to cause problems in cleanup
        return

    connection, client_address = sock.accept()
    data = connection.recv(256)
    sdata = data.decode("utf-8")

    if len(data.split()) < 1:  # nothing ventured, nothing gained
        connection.close()
        return

    print(data)
    match data.split()[0]:
        case b"rehash":
            active_config = get_config("~/..mkd.conf")
            connection.close()
        case b"msg":
            if len(sdata) > 4:
                send_notice(sdata[4:])
            else:
                connection.sendall(b"bad syntax\n")
            connection.close()
        case b"quit":
            connection.close()
            multiprocessing.current_process().terminate()
        case other:
            connection.sendall(b"unknown command\n")
            connection.close()


def dispatch_event(e: evdev.KeyEvent):
    global active_config
    global evqueue

    presses = [ecodes.KEY_P, ecodes.KEY_I, ecodes.KEY_U, ecodes.KEY_S]
    if active_config.get("mirror_jacket"):
        if e.scancode == ecodes.KEY_UP:
            evqueue.put((ecodes.EV_KEY, ecodes.KEY_W, e.keystate))
        if e.scancode == ecodes.KEY_DOWN:
            evqueue.put((ecodes.EV_KEY, ecodes.KEY_S, e.keystate))
        if e.scancode == ecodes.KEY_LEFT:
            evqueue.put((ecodes.EV_KEY,ecodes.KEY_A, e.keystate ))
        if e.scancode == ecodes.KEY_RIGHT:
            evqueue.put((ecodes.EV_KEY, ecodes.KEY_D, e.keystate))

    if (e.keystate == e.key_up) and e.scancode == ecodes.KEY_M:
        send_notice("Mirror Jacket On")
        active_config["mirror_jacket"] = 1
    if (e.keystate == e.key_up) and e.scancode == ecodes.KEY_Q:
        active_config["mirror_jacket"] = 0
        send_notice("Mirror Jacket off")
        
    if (e.keystate == e.key_down) and e.scancode == ecodes.KEY_P:
        send_notice("Party Time, conga line")
        for k in presses:
            syn_key_press(k, evqueue)


def handle_sigterm(num, fr):
    global current_device
    evqueue.put(STOP_VALUE)
    release_device(current_device.path)
    print("Released Device Setting Stop flag")
    stop_flag.set()


def do_cleanup():
    if current_device is not None:
        try:
            current_device.ungrab()
        except OSError:
            pass
    for p in daemon_tmpfiles:
        if os.path.exists(p):
            os.unlink(p)


def send_notice(msg):
    try:
        actual_send_notice(msg)
    except Exception:
        syslog.syslog(syslog.LOG_INFO, msg)


if __name__ == "__main__":
    main()
