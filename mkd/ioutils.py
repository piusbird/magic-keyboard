"""
Misc IO Related stuff
"""

import syslog

class NullFile:
    """
    File like object that ignores everything writen to it
    """
    def write(self, b):
        pass

class SyslogFile:
    """
    File like object, writes to syslog after decoding to utf8
    """
    def write(self, msg):
        if type(msg) == str:
            real = msg
        elif type(msg) == bytes:
            real = msg.decode('utf-8')
        syslog.syslog(syslog.LOG_DEBUG, real)