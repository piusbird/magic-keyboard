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
import fcntl
from time import sleep

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

def daemon_main(cfig):
    while True:
            msg = cfig["message"] + " "
            ourpid = os.getpid()
            msg += str(ourpid)
            syslog.syslog(syslog.LOG_ALERT, msg)
            sleep(10)


def main():
    cfig = get_config()
    print("Config Values")
    for k, v in cfig.items():
        print(k + ": " + v)
    
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
        sys.stdout.close()
        sys.stdin.close()
        sys.stderr.close()
        daemon_main(cfig)
        


if __name__ == '__main__':
    main()