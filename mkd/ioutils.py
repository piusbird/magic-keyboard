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
        if isinstance(msg, str):
            real = msg
        elif isinstance(msg, bytes):
            real = msg.decode("utf-8")
        syslog.syslog(syslog.LOG_DEBUG, real)
