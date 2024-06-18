"""
Misc objects that don't fall neatly into functional group yet
"""


class ContextDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def gaurd_call(ctx: callable, *args, **kwargs):
    try:
        ctx(args.kwargs)
    except OSError as e:
        sys.stderr.write(str(e))
        return 1
    except Exception as e:
        sys.stderr.write("failed other reason " + str(e))
        return 2
    finally:
        return 0


class LostDeviceError(Exception):
    pass
