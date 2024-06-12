# Pius Q Bird's Working Stream for June 2nd 2024

## Streamer Status

7 out of 10. Had some health issues, but i'll be fine

New Computer is in the mail, so we should have more content shortly

I punched a Christmas Tree this weekend how about y'all

## Tonight's Project

Magic Keyboard Daemon

## Wut?

Basically, one of the ways in which my cerebral palsy manifests is in my hands and fingers. I have full use of my hands, including the thumb and first two fingers of each. But doing things that require precision, or fast movement of the hands and fingers is a bit of pain. That is only getting worse as I get older.

Magic keyboard demon, is an attempt to make a keyboard macro processor, and input re mapper for Linux. I hope this piece of software will make my life substantially easier, and allow for faster completion of projects.

## Design Considerations

At first I thought this was going to be a straight rewrite Auto Hot Key, the windows program I use for Linux. But I discovered auto hotkey is basically designed as a rootkit, which you voluntarily install in your computer.

I attempted to prototype the Linux kernel portion of the code, in bpf. But this turns out to be a security and stability nightmare, so I'm taking a new approach.

## Magic Keyboard Daemon 2.0

My new design will use a second keyboard, which will be connected to the system. At all times, but a piece of code (userspace or kernel?) will mark the second keyboard inactive, until some sort of configuration file (lua script?) is loaded.

Upon loading of the configuration input events on the secondary keyboard we'll be responded to with macros specified in the configuration.

### Example!

A game might require that the user press WASD to move and click the mouse button to shoot. On a left handed setup this is difficult. If the game developer didn't provide a convenient way to remap keys. A magic keyboard macro (MKM) could be activated which would synthesize the correct movement keystrokes. When the arrow keys are pressed.

## Stuff I need

this project should be prototypeable with the python standard library, and bindings to the evdev Linux kernel API. Sooner or later I will need a lea interpreter for python.

so far as I'm aware, this should be doable from user space by constructing a demon. having the following control flow.

 1. Demons startup initialization
 2. initial configuration contains the device specification of the secondary keyboard, other stuff (TBD)
 3. demon sends ioctl **EVIOGRAB** to the secondary keyboard **see Below**
 4. demon holds this ioctl for the whole lifespan of the process.
 5. Demon loads keyboard macros, (lua scripts)? from somewhere. See Macros section
 6. secondary keyboard is now designated magic keyword
 7. demon reads events from magic in a continuous loop that last the life of the process
 8. if an event matches a trigger condition specified in the currently loaded macro, or macro set go to step ten, otherwise ignore the event, ( or perform default action)?
 9. demon should maintain an inter process communication link, so that the user may load new macros.
10. demon synthesizes input events, either requested by macros or directly from the user via the inter process communication link specified above

### Macros

* Macros are lieu of programs
* Each Macro has an input event that triggers it.
* The macro will have the capability to request that the demon synthesize other input events. according to its own logic
* macro may have the ability to perform other actions, such as interact with the file system or play sounds. This will depend on what sort of runtime is included with the lua interpreter.

## EVIOGRAB 

  in a Linux system, when two or more keyboards are attached the default keyboard  handling routine treats key presses from all keyboards as io events.   it neither differentiates between keyboards  nor is there any way  in configurations exposed  with the default tools to  have a keyboard  be ignored, but remain readable to processes  as needed.

 Even though the  kernel apis have the capability to differentiate  among different io sources, and this has been used in projects like multi pointer X, as well as in the X11 and Wayland implementations of touchscreen and wacom tablet inputs. The exposure of these low level capabilties to user space is somewhat limited.

 So far as I know the only way to have an input device ignored by X11 or Wayland, but still remain readable is to send certain ioctls  to the device. So that one process has exclusive use of  said device  until it releases it's exclusive lock.

 This is what EVIOGRAB  does and this is why we have to  write this program as a system level demon. With all that entails