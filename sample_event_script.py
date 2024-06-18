import evdev
from evdev import ecodes
def mk_evread(e: evdev.KeyEvent):
    global active_config
    global evqueue
    if active_config.get("idle_bounce") == None:
        active_config["idle_bounce"] = False

    presses = [ecodes.KEY_P, ecodes.KEY_I, ecodes.KEY_U, ecodes.KEY_S]
    if active_config.get("mirror_jacket"):
        if e.scancode == ecodes.KEY_UP:
            evqueue.put((ecodes.EV_KEY, ecodes.KEY_W, e.keystate))
        if e.scancode == ecodes.KEY_DOWN:
            evqueue.put((ecodes.EV_KEY, ecodes.KEY_S, e.keystate))
        if e.scancode == ecodes.KEY_LEFT:
            evqueue.put((ecodes.EV_KEY, ecodes.KEY_A, e.keystate))
        if e.scancode == ecodes.KEY_RIGHT:
            evqueue.put((ecodes.EV_KEY, ecodes.KEY_D, e.keystate))

    if (e.keystate == e.key_up) and e.scancode == ecodes.KEY_F2:
        send_notice("Tea Time")
        active_config["idle_bounce"] = not active_config["idle_bounce"]
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
