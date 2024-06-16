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
from evdev import InputDevice, categorize, ecodes, UInput

stop_flag = threading.Event()
evqueue = queue.Queue()
active_config = None
daemon_tmpfiles = ["~/.mkd.sock", "~/.mkd.pid"]
send_notice = lambda m: Notify.Notification.new("magic-keyboard",m, "dialog-information").show()
current_device = None
def uinput_thread():
    Notify.init("mkd Vinput")
    global evqueue
    ui = UInput()
    send_notice("input synth ready")
    while not stop_flag.is_set():
        keydata = evqueue.get()
        ui.write(*keydata)
        ui.syn()
    ui.close()


def syn_key_press(key: int):
    down_event = (ecodes.EV_KEY, key, 1)
    up_event = (ecodes.EV_KEY, key, 0)
    evqueue.put(down_event)
    evqueue.put(up_event)

def do_cleanup():
    if current_device is not None:
        try: 
            current_device.ungrab()
        except OSError:
            pass
    for p in daemon_tmpfiles:
        if os.path.exists(p):
            os.unlink(p)
    exit(0)



def handle_socket(sock):
    Notify.init("Mkd Background process")
    global active_config
    if stop_flag.is_set(): # we don't want to cause problems in cleanup
        return

    connection, client_address = sock.accept()
    data = connection.recv(256)
    sdata = data.decode('utf-8')
    
    if len(data.split()) < 1: # nothing ventured, nothing gained
        connection.close()
        return

    print(data)
    match data.split()[0]:
        case b"rehash":
            active_config = get_config()
            connection.close()
        case b"msg":
            if len(sdata) > 4:
                send_notice(sdata[4:])
            else:
                connection.sendall(b"bad syntax\n")
            connection.close()
        case b"quit":
            connection.close()
            stop_flag.set()
            release_current_device()
            do_cleanup()
        case other:
            connection.sendall(b"unknown command\n")
            connection.close()


def write_pid(file_path):
    fp = open(file_path, "w")
    fp.write(str(os.getpid()))
    return True

def pid_lock():
    file_path = os.path.expanduser("~/.mkd.pid")
    if os.path.exists(file_path):
        target_pid = open(file_path).read()
        if os.path.exists(os.path.join("/proc", target_pid)):
            return True
        else:
            
            return False
    else:
        
        return False
        
    
def handle_sigterm(num, fr):
    release_current_device()
    stop_flag.set()

def get_config():
    file_path = os.path.expanduser("~/.mkd.conf")
    if os.path.exists(file_path):
        fp = open(file_path, "rb")
        try:
            cfig_data = tomllib.load(fp)
        except tomllib.TOMLDecodeError:
            cfig_data = {}
        finally:
            fp.close()
        return cfig_data
    else:
        return {}

def activate_device(path: str):
    global current_device
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
        send_notice("Could not grab device shutting down")
        stop_flag.set()
    send_notice(f"{current_device.name} at {current_device.path} Active Grab")

def release_current_device():
    global current_device
    if current_device is not None:
        try: 
            current_device.ungrab()
        except OSError:
            pass
    current_device = None


def dispatch_event(e: evdev.KeyEvent):
    global active_config
    presses = [ecodes.KEY_P, ecodes.KEY_I, ecodes.KEY_U, ecodes.KEY_S]
    send_notice = lambda m: Notify.Notification.new("magic-keyboard",m, "dialog-information").show()
    print( " what is this: " + str(e.keystate) + " and is it " + str(e.key_down))
    print(str(int(e.scancode) == ecodes.KEY_M))
    if (e.keystate == e.key_up) and e.scancode == ecodes.KEY_M:
        send_notice(active_config["message"])
    if (e.keystate == e.key_down) and e.scancode == ecodes.KEY_P:
        send_notice("Party Time, conga line")
        for k in presses:
            syn_key_press(k)
        
    



def startup_proc(devices, target_device):
    if os.getuid() == 0 or os.geteuid() == 0:
        print("Do not run this as root")
        return False
    for d in devices:
        if d.name == target_device:
            activate_device(d.path)
    if current_device is None:
        return False
    else:
        return True

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
    
    lisnr = threading.Thread(target=handle_socket, args=(sock,))
    vinput_t = threading.Thread(target=uinput_thread)
    while not stop_flag.is_set():
            if not lisnr.is_alive():
                lisnr = threading.Thread(target=handle_socket, args=(sock,))
                lisnr.start()
            if not vinput_t.is_alive():
                vinput_t = threading.Thread(target=uinput_thread)
                vinput_t.start()

            event = current_device.read_one()
            if event is not None:
                if event.type == ecodes.EV_KEY:
                    dispatch_event(evdev.util.categorize(event))
            
    if lisnr.is_alive():
        lisnr.join() # make sure on sigterm we clean this up
    if vinput_t.is_alive():
        vinput_t.join()
    do_cleanup()
    sys.exit(127)

    




def main():
    cfig = get_config()
    print("Config Values")
    for k, v in cfig.items():
        print(k + ": " + v)
    print(len(sys.argv))
    if len(sys.argv) == 2:
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for d in devices:
            print(d)
        
        exit(0)

    
    pid = os.fork()

    if pid:
        os._exit(0)
    else:
        os.umask(0)
        os.setpgrp()
        if pid_lock():
            print("already running")
            exit(1)

        #sys.stdout.close()
        #sys.stdin.close()
        #sys.stderr.close()
        signal.signal(signal.SIGTERM, handle_sigterm)
        daemon_main(cfig)
        


if __name__ == '__main__':
    main()