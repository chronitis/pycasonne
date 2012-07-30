from world import Tile, ROAD, RIVER, CLOISTER, PENNANT, CITY, CATHEDRAL, INN
import random

"""
Raw data for different stacks of tiles

Each tile is defined using the ROAD, RIVER, etc enums imported from :mod:`world`
and each tile is represented by a tuple (CENTRE, NORTH, EAST, SOUTH, WEST [, hint])
where CENTRE can be a binary OR of multiple attributes and the optional hint
argument is a dictionary overrides for the segments that should appear.

Note that arbitrary new combinations here may work, but might either not have
the correct segments produced by :func:`world.Tile.build_features` or the correct
representation produced by :func:`feature.Feature.draw`.
"""

def standard_set():
    "Base game set, less the starting tile"
    tiles = []
    tiles += [(CLOISTER, None, None, ROAD, None)] * 2
    tiles += [(CLOISTER, None, None, None, None)] * 4
    tiles += [(CITY | PENNANT, CITY, CITY, CITY, CITY)]
    tiles += [(None, ROAD, CITY, ROAD, None)] * 3
    tiles += [(None, CITY, None, None, None)] * 5
    tiles += [(CITY | PENNANT, None, CITY, None, CITY)] * 2
    tiles += [(CITY, CITY, None, CITY, None)]
    tiles += [(None, None, CITY, None, CITY)] * 3
    tiles += [(None, None, CITY, CITY, None)] * 2
    tiles += [(None, CITY, ROAD, ROAD, None)] * 3
    tiles += [(None, ROAD, CITY, None, ROAD)] * 3
    tiles += [(None, ROAD, CITY, ROAD, ROAD)] * 3
    tiles += [(CITY | PENNANT, CITY, None, None, CITY)] * 2
    tiles += [(CITY, CITY, None, None, CITY)] * 3
    tiles += [(CITY | PENNANT, CITY, ROAD, ROAD, CITY,
               {'farm':((2, 5), (3, 4))})] * 2
    tiles += [(CITY, CITY, ROAD, ROAD, CITY,
               {'farm':((2, 5), (3, 4))})] * 3
    tiles += [(CITY | PENNANT, CITY, CITY, None, CITY)]
    tiles += [(CITY, CITY, CITY, None, CITY)] * 3
    tiles += [(CITY | PENNANT, CITY, CITY, ROAD, CITY)] * 2
    tiles += [(CITY, CITY, CITY, ROAD, CITY)]
    tiles += [(None, ROAD, None, ROAD, None)] * 8
    tiles += [(None, None, None, ROAD, ROAD)] * 9
    tiles += [(None, None, ROAD, ROAD, ROAD)] * 4
    tiles += [(None, ROAD, ROAD, ROAD, ROAD)]
    return tiles

def river_set():
    "River set, less river start and end tiles"
    tiles = []
    tiles += [(None, RIVER, RIVER, None, None)] * 2
    tiles += [(None, RIVER, None, RIVER, None)] * 2
    tiles += [(CITY, CITY, CITY, RIVER, RIVER,
               {'farm':((4,7),(5,6))})]
    tiles += [(None, RIVER, RIVER, ROAD, ROAD,
               {'farm':((1,2),(3,4,7,0),(5,6))})]
    tiles += [(None, RIVER, ROAD, RIVER, ROAD)]
    tiles += [(None, RIVER, CITY, RIVER, CITY)]
    tiles += [(CLOISTER, None, RIVER, ROAD, RIVER)]
    tiles += [(None, CITY, RIVER, ROAD, RIVER,
               {'farm':((2,),(3,4),(5,6),(7,))})]
    return tiles

def river_ii_set():
    tiles = []
    tiles += [(None, RIVER, None, None, None)]
    tiles += [(None, RIVER, None, None, RIVER)]
    tiles += [(None, RIVER, RIVER, None, RIVER)]
    tiles += [(None, None, RIVER, None, CITY,
               {'farm': ((0, 1, 2), (3, 4, 5))})]
    tiles += [(CITY, CITY, RIVER, CITY, RIVER,
               {'farm': ((2,), (3,), (6,), (7,))})]
    tiles += [(CLOISTER, None, RIVER, None, RIVER)]
    tiles += [(None, RIVER, CITY, RIVER, ROAD,
               {'farm': ((1,), (4,), (5, 6), (7, 0))})]
    tiles += [(None, ROAD, ROAD, RIVER, RIVER,
               {'farm': ((1, 2), (3, 4, 7, 0), (5, 6))})]
    tiles += [(None, None, None, None, RIVER)]
    tiles += [(None, None, RIVER, RIVER, None)]
    tiles += [(None, RIVER, ROAD, RIVER, ROAD)]
    tiles += [(CITY, RIVER, CITY, CITY, RIVER,
               {'farm': ((1, 6), (7, 0))})]
    return tiles

#missing implementation: abbey, mayor, bridge
def abbey_mayor_set():
    tiles = []
    tiles += [(None, None, None, ROAD, None)]
    #tiles += [(PENNANT, None, None, None, CITY, {'farm': ((0, 1), (2, 3), (4, 5))})] #city touches all corners splitting farms, not rendered
    tiles += [(CLOISTER, ROAD, ROAD, ROAD, ROAD)]
    #tiles += [(None, CITY, CITY, CITY, CITY, {'farm': ((8,),), 'city': ((0, 2), (1, 3, 'pennant'))})] #two bridged cities, not rendered
    tiles += [(None, CITY, ROAD, ROAD, None)]
    tiles += [(None, None, ROAD, ROAD, CITY)]
    #tiles += [(PENNANT, CITY, CITY, CITY, CITY)] #double pennant, not implemented
    #tiles += [(None, CITY, CITY, None, CITY, {'farm': ((8,), (4, 5)), 'city': ((0, 'pennant'), (1, 3))})] #bridged city to connect to bridged road, farm8 probably not rendered properly where other farm present
    tiles += [(PENNANT, ROAD, CITY, ROAD, CITY,
               {'farm': ((0, 1), (4,), (5,)), 'road': ((0, 2),)})] #tunnelled road so northern farm connects up, not properly rendered
    tiles += [(None, ROAD, None, ROAD, ROAD)]
    tiles += [(None, None, None, ROAD, CITY,
               {'farm': ((0, 1, 2, 3, 4), (5,))})]
    tiles += [(None, CITY, CITY, ROAD, ROAD,
               {'farm': ((4,), (5, 6, 8), (7,)), 'road': ((2,), (3,))})]
    return tiles

#includes river pieces
def mini_expansion_set():
    tiles = []
    tiles += [(CITY, ROAD, CITY, None, CITY)]
    tiles += [(None, CITY, ROAD, CITY, ROAD)]
    tiles += [(None, ROAD, CITY, ROAD, ROAD,
               {'farm': ((1, 5, 6), (4,), (7, 0)), 'road': ((0, 3), (2,))})]
    tiles += [(None, None, ROAD, None, RIVER,
               {'farm': ((0, 1, 2, 7), (3, 4, 5, 6))})]
    tiles += [(CITY, CITY, CITY, None, ROAD,
               {'farm': ((4, 5, 6), (7,))})]
    tiles += [(CITY, CITY, CITY, ROAD, ROAD,
               {'farm': ((4,), (5, 6, 8), (7,)), 'road': ((2,), (3,))})]
    tiles += [(None, None, None, None, None)]
    tiles += [(CITY, CITY, ROAD, CITY, ROAD,
               {'farm': ((2,), (3,), (6,), (7,)), 'road': ((1,), (3,))})]
    tiles += [(None, CITY, CITY, CITY, ROAD,
               {'farm': ((6, 8), (7,)), 'city': ((0, 1), (2,))})]
    tiles += [(CLOISTER, ROAD, ROAD, ROAD, ROAD)]
    tiles += [(None, CITY, RIVER, CITY, RIVER)]
    return tiles

#missing implementation: large avatar
def inns_cathedrals_set():
    "Inns and cathedrals set (less one troublesome tile)"
    tiles = []
    tiles += [(CLOISTER, None, ROAD, None, ROAD,
               {'road': ((1,), (3,))})]
    tiles += [(CITY | CATHEDRAL, CITY, CITY, CITY, CITY)] * 2
    tiles += [(None, CITY, CITY, CITY, CITY,
               {'farm':((8,),)})]
    tiles += [(None, CITY, CITY, None, CITY,
               {'farm':((4, 5, 8),)})]
    tiles += [(None, CITY, ROAD, CITY, ROAD,
               {'farm':((2,), (3,), (6,), (7,)), 'road':((1,), (3,))})]
    tiles += [(None, CITY, None, CITY, CITY,
               {'city':((2,), (0, 3, 'pennant')), 'farm': ((2, 3, 8),)})]
#    tiles += [(CITY, CITY, None, None, None, {'farm':((2, 3), (4, 5, 6, 7))})] #tooth-shaped city, touches bottom-right corner #correctly modelled, but badly rendered
    tiles += [(None, CITY, None, ROAD, None,
               {'farm':((2, 3, 4), (5, 6, 7))})]
    tiles += [(CITY, CITY, ROAD, None, CITY,
               {'farm':((2,), (3, 4, 5))})]
    tiles += [(CITY | PENNANT, ROAD, CITY, ROAD, CITY,
               {'farm':((0,), (1,), (4,), (5,)), 'road':((0,), (2,))})]
    tiles += [(CITY | INN, CITY, None, ROAD, CITY,
               {'farm':((2, 3, 4), (5,))})]
    tiles += [(INN, CITY, None, ROAD, ROAD)]
    tiles += [(CITY | PENNANT | INN, CITY, ROAD, ROAD, CITY)]
    tiles += [(INN, None, ROAD, ROAD, ROAD)]
    tiles += [(INN, None, ROAD, None, ROAD)]
    tiles += [(INN, None, None, ROAD, ROAD)]
    tiles += [(None, ROAD, ROAD, ROAD, ROAD,
               {'farm':((0, 3, 4, 7), (1, 2), (5, 6)), 'road': ((0, 1), (2, 3))})]
    return tiles

def generate_stack(river=True, inns_cathedrals=True):
    """
    Generate a list of :class:`world.Tile` instances, randomly shuffled and
    containing the selected expansions.
    """
    rest = [Tile(*t) for t in standard_set()]
    if inns_cathedrals:
        rest += [Tile(*t) for t in inns_cathedrals_set()]
    random.shuffle(rest)
    if river:
        start = Tile(None, RIVER, None, None, None)
        end = Tile(None, RIVER, None, None, None)
        river = [Tile(*t) for t in river_set()]
        random.shuffle(river)
        return [start] + river + [end] + rest
    else:
        start = Tile(None, ROAD, CITY, ROAD, None)
        return [start] + rest

if __name__ == '__main__':
    from world import World

    for t in inns_cathedrals_set():
        tile = Tile(*t)
        tile.place(0, 0, World({}, []))
        print(tile)
        print(tile.image())
        print("Features:")
        for f in tile.features():
            print(f)
        print()
        raw_input("next?")

