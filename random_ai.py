from game import PlayerBase
from ai_names import NAMES
import random

class RandomAI(PlayerBase):
    """
    A very stupid AI that picks randomly from valid moves.
    Unlikely to win any prizes.
    """
    def __init__(self, interface, **kwargs):
        self.interface = interface
        name = NAMES.pop(random.randint(0, len(NAMES) - 1))
        self.interface.set_name(name)

    def place_tile(self, tile, possible):
        return random.choice(possible)

    def place_avatar(self, features):
        return random.choice(features + [None])
