"""
File related functions
"""

import os
import tomllib


def write_pid(file_path):
    fp = open(file_path, "w")
    fp.write(str(os.getpid()))
    return True


def pid_lock(U_path):
    file_path = os.path.expanduser(U_path)
    if os.path.exists(file_path):
        target_pid = open(file_path).read()
        if os.path.exists(os.path.join("/proc", target_pid)):
            return True
        else:

            return False
    else:

        return False


def get_config(U_path: str):
    file_path = os.path.expanduser(U_path)
    if os.path.exists(file_path):
        fp = open(file_path, "rb")
        try:
            cfig_data = tomllib.load(fp)
        except tomllib.TOMLDecodeError:
            cfig_data = None
        finally:
            fp.close()
        return cfig_data
    else:
        return None


def read_script(u_path: str):

    with open(os.path.expanduser(u_path), "r") as f:
        code = f.read()

    try:
        ocode = compile(code, u_path, "exec")
        return 0, code
    except SyntaxError as e:
        return 1, str(e)
    except ValueError as e:
        return 2, str(e)


class HaltRequested(Exception):
    pass
