from game import PlayerBase
from ai_names import random_name
import random

class RandomAI(PlayerBase):
    """
    A very stupid AI that picks randomly from valid moves.
    Unlikely to win any prizes.
    """
    def __init__(self, interface, **kwargs):
        self.interface = interface
        name = random_name()
        self.interface.set_name(name)

    def place_tile(self, tile, possible):
        return random.choice(possible)

    def place_avatar(self, features):
        if random.random() > 0.5:
            return random.choice(features)
        else:
            return None
