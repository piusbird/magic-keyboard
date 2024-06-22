"""
Here is the module where i abuse stats to calcualate
various input delays and things
The point of this project is to go at simulate human speeds.
Under Normal circumstances. This is an accomidation device, not intended
to give super powers usually. The user will be able to configure the simulation
to their liking, or turn it off entirely
"""

import math
import random
from enum import Enum


class Chaos(Enum):
    FAVOR = 1
    EVEN = 0
    UNLUCKY = -1


def calculate_clicks_persecond(mean_actions_per_min: int, odds: Chaos):
    """
    According to my research
    speed of input is messured in Actions per Minute by the gaming community
    Action refers to any action that the user performs.
    Like a mouse click or a key press. This is  a maddening imprecise unit as is.
    Add to that the articles i found cited no sources for the numbers they gave.

    This model makes *several* assumptions, which may not be accurate. Listed below

    * One action is one key press, mouse movement, or mouse click
    * actions per minute scores are Normally Distributed around their mean
        and a std div of about 25% of the mean. +/- three quaters of a percent
    * so to simulate human speeds we have to calculate the time delay, between
        discrete key presses, following bell curve


    """
    if odds == Chaos.FAVOR:
        std_div = 25 + (random.randint(25, 75) / 100)
    elif odds == Chaos.EVEN:
        std_div = 25
    else:
        std_div = 25 - (random.randint(25, 75) / 100)
    curve = random.gauss(mean_actions_per_min, std_div)
    if odds == Chaos.FAVOR:
        return math.ceil(curve) / 60 / 60
    else:
        return math.floor(curve) / 60 / 60
