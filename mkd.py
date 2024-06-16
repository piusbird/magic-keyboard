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
from evdev import InputDevice, categorize, ecodes

stop_flag = threading.Event()
Notify.init("Magic Keyboard")
active_config = None
daemon_tmpfiles = ["~/.mkd.sock", "~/.mkd.pid"]
send_notice = lambda m: Notify.Notification.new("magic-keyboard",m, "dialog-information").show()
current_device = None
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
    send_notice = lambda m: Notify.Notification.new("magic-keyboard",m, "dialog-information").show()
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
            write_pid(file_path)
            return False
    else:
        write_pid(file_path)
        return False
        
    
def handle_sigterm(num, fr):
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


def dispatch_event(e: evdev.KeyEvent):
    global active_config
    send_notice = lambda m: Notify.Notification.new("magic-keyboard",m, "dialog-information").show()
    print( " what is this: " + str(e.keystate) + " and is it " + str(e.key_down))
    print(str(int(e.scancode) == ecodes.KEY_M))
    if (e.keystate == e.key_up) and e.scancode == ecodes.KEY_M:
        send_notice(active_config["message"])
    


    

async def event_read(dev: InputDevice):
    async for event in dev.read_loop():
            if event.type == ecodes.EV_KEY:
                dispatch_event(categorize(event))


def daemon_main(cfig):
    global active_config
    global current_device
    send_notice = lambda m: Notify.Notification.new("magic-keyboard",m, "dialog-information").show()
    active_config = cfig
    Notify.init("Magic Keyboard")
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    if active_config["grab_device"]:
        for d in devices:
            if d.name == active_config["grab_device"]:
                activate_device(d.path)
        if current_device is None:
            send_notice("Device not found shutting down")
            stop_flag.set()

    sockpath = os.path.expanduser("~/.mkd.sock")
    if os.path.exists(sockpath):
        os.unlink(sockpath)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(sockpath)
    sock.listen(1)
    
    x = threading.Thread(target=handle_socket, args=(sock,))
    while not stop_flag.is_set():
            if not x.is_alive():
                x = threading.Thread(target=handle_socket, args=(sock,))
                x.start()
            msg = active_config["message"] + " "
            ourpid = os.getpid()
            msg += str(ourpid)
            event = current_device.read_one()
            if event is not None:
                if event.type == ecodes.EV_KEY:
                    dispatch_event(evdev.util.categorize(event))
            
    if x.is_alive():
        x.join() # make sure on sigterm we clean this up
    do_cleanup()

    




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
            print("daemon running")
            exit(1)
        print("Successful daemonize")

        #sys.stdout.close()
        #sys.stdin.close()
        #sys.stderr.close()
        signal.signal(signal.SIGTERM, handle_sigterm)
        daemon_main(cfig)
        


if __name__ == '__main__':
    main()