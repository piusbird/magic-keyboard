import evdev
from evdev import ecodes
from math import ceil, floor


def mk_evread(e: evdev.KeyEvent, ctx: ContextDict):
    active_config = ctx.active_config
    evqueue = ctx.evqueue
    send_notice = ctx.send_notice
    ceil = ctx.ceil
    floor = ctx.floor
    if ctx.get("current_velocity") == None:
        ctx["current_velocity"] = 5
    ov = ctx.active_config.get("mouse_invel")
    if ov == None:
        ov = 5
    mouse_keys = [ecodes.KEY_I, ecodes.KEY_J, ecodes.KEY_K, ecodes.KEY_L]
    if e.scancode == ecodes.KEY_UP:
        ctx.evqueue.put((ecodes.EV_KEY, ecodes.KEY_W, e.keystate))
    if e.scancode == ecodes.KEY_DOWN:
        ctx.evqueue.put((ecodes.EV_KEY, ecodes.KEY_S, e.keystate))
    if e.scancode == ecodes.KEY_LEFT:
        ctx.evqueue.put((ecodes.EV_KEY, ecodes.KEY_A, e.keystate))
    if e.scancode == ecodes.KEY_RIGHT:
        ctx.evqueue.put((ecodes.EV_KEY, ecodes.KEY_D, e.keystate))

    if (e.scancode == ecodes.KEY_I) and (
        e.keystate == e.key_down or e.keystate == e.key_hold
    ):
        ctx.evqueue.put((ecodes.EV_REL, ecodes.REL_Y, floor(-ctx.current_velocity)))
        print("Should Be Moving up")
        if ecodes.KEY_J in ctx.active_keys:
            ctx.evqueue.put((ecodes.EV_REL, ecodes.REL_X, floor(-ctx.current_velocity)))
            ctx.evqueue.put((ecodes.EV_SYN, ecodes.SYN_REPORT, 0))
        if ecodes.KEY_L in ctx.active_keys:
            ctx.evqueue.put((ecodes.EV_REL, ecodes.REL_X, ceil(ctx.current_velocity)))
            ctx.evqueue.put((ecodes.EV_SYN, ecodes.SYN_REPORT, 0))
        ctx.current_velocity = ctx.current_velocity + 0.125
    if (e.scancode == ecodes.KEY_K) and (
        e.keystate == e.key_down or e.keystate == e.key_hold
    ):

        ctx.evqueue.put((ecodes.EV_REL, ecodes.REL_Y, ceil(ctx.current_velocity)))
        ctx.current_velocity = ctx.current_velocity + 0.125
        print("going down")
        if ecodes.KEY_J in ctx.active_keys:
            ctx.evqueue.put((ecodes.EV_REL, ecodes.REL_X, floor(-ctx.current_velocity)))
            ctx.evqueue.put((ecodes.EV_SYN, ecodes.SYN_REPORT, 0))
        if ecodes.KEY_L in ctx.active_keys:
            ctx.evqueue.put((ecodes.EV_REL, ecodes.REL_X, ceil(ctx.current_velocity)))
            ctx.evqueue.put((ecodes.EV_SYN, ecodes.SYN_REPORT, 0))
    if (e.scancode == ecodes.KEY_J) and (
        e.keystate == e.key_down or e.keystate == e.key_hold
    ):
        ctx.evqueue.put((ecodes.EV_REL, ecodes.REL_X, floor(-ctx.current_velocity)))
        ctx.current_velocity = ctx.current_velocity + 0.125
        print("going left")
    if (e.scancode == ecodes.KEY_L) and (
        e.keystate == e.key_down or e.keystate == e.key_hold
    ):
        ctx.evqueue.put((ecodes.EV_REL, ecodes.REL_X, ceil(ctx.current_velocity)))
        ctx.current_velocity = ctx.current_velocity + 0.125
        print("going right")
    if e.scancode in mouse_keys and (e.keystate == e.key_up):
        ctx.current_velocity = ov
    return ctx
