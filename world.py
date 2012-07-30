from feature import (City, CitySegment, Road, RoadSegment, Cloister, River,
                     RiverSegment, Farm, FarmSegment, Feature, Segment)

import copy
#import cPickle as pickle
from proxy import proxify

NORTH, EAST, SOUTH, WEST = range(4)
EMPTY = 0
(ROAD, RIVER, CITY, PENNANT,
CLOISTER, CATHEDRAL, INN) = [1 << i for i in range(7)]
EDGES = {ROAD:"Road", RIVER:"River", CITY:"City", PENNANT:"Pennant",
         CLOISTER:"Cloister", EMPTY:"Empty", CATHEDRAL: "Cathedral", INN: "Inn"}

OR_STR = lambda x: ' '.join(v for k, v in EDGES.items()
                            if k is not None and k & x)

SYMMETRY_CACHE = {}
FEATURE_CACHE = {}

class Tile(object):
    """
    Class representing a game tile.

    This both represents a free, rotateable tile (x, y, world -> None) and
    a tile anchored in the world. TODO: Split this into two classes.

    Rotating the tile returns a new tile instance.

    The tile is defined by (CENTRE, EDGES[4] [, hint]). The symmetry of the tile
    is checked and cached for determining available moves.

    The features on the tile are calculated once by build_features (producing a
    list of functions with signature f(tile) -> feature) and cached, since AI
    placement testing would otherwise involve repeatedly calculating this.
    """
    def __init__(self, centre, north, east, south, west, hint=None):
        self.edges = tuple(EMPTY if i==None else i
                           for i in (north, east, south, west))
        self.centre = centre if centre is not None else EMPTY
        self.segments = []
        self.hint = hint if hint else {}
        self.x = None
        self.y = None
        self.world = None

        if self.edges in SYMMETRY_CACHE:
            self.symmetry = SYMMETRY_CACHE[self.edges]
        else:
            rotate = lambda e, i: tuple(e[(x+i)%4] for x in range(4))
            if self.edges == rotate(self.edges, 1) ==\
                             rotate(self.edges, 2) == rotate(self.edges, 3):
                self.symmetry = 1
            elif self.edges == rotate(self.edges, 2):
                self.symmetry = 2
            else:
                self.symmetry = 4
            SYMMETRY_CACHE[self.edges] = self.symmetry

    def build_features(self):
        builders = []

        road_edges = [i for i in range(4) if self.edges[i] == ROAD]
        inn = self.centre & INN
        if 'road' in self.hint:
            for h in self.hint['road']:
                builders.append((lambda ii, *j:
                                 lambda tile: Road([RoadSegment(tile, j, ii)]))
                                 (inn, *h))
        else:
            if len(road_edges) == 2: #through road
                builders.append((lambda ii, j, k:
                                 lambda tile: Road([RoadSegment(tile, [j, k], ii)]))
                                 (inn, *road_edges))
            else:
                for i in road_edges:
                    builders.append((lambda ii, j:
                                     lambda tile: Road([RoadSegment(tile, [j], ii)]))
                                     (inn, i))

        river_edges = [i for i in range(4) if self.edges[i] == RIVER]
        if len(river_edges) == 2: #through road
            builders.append((lambda j, k:
                             lambda tile: River([RiverSegment(tile, [j, k])]))
                             (*river_edges))
        else:
            for i in river_edges:
                builders.append((lambda j:
                                 lambda tile: River([RiverSegment(tile, [j])]))
                                 (i))

        if self.centre & CLOISTER:
            builders.append((lambda:
                             lambda tile: Cloister(tile))
                             ())

        city_counter = 0
        city_segments = [None] * 4
        city_edges = [i for i in range(4) if self.edges[i] == CITY]
        if 'city' in self.hint:
            for h in self.hint['city']:
                pennant = False
                if h[-1] == 'pennant':
                    pennant = True
                    h = h[:-1]
                builders.append((lambda p, *j:
                                 lambda tile: City([CitySegment(tile, j, p)]))
                                 (pennant, *h))
                for e in h:
                    city_segments[e] = city_counter
                city_counter += 1
        else:
            if city_edges and not self.centre & CITY:
                for edge in city_edges:
                    city_segments[edge] = city_counter
                    builders.append((lambda j:
                                     lambda tile: City([CitySegment(tile, [j])]))
                                     (edge))
                    city_counter += 1
            elif city_edges:
                builders.append((lambda p, c, *j:
                                 lambda tile: City([CitySegment(tile, j, p, c)]))
                                 (self.centre&PENNANT, self.centre&CATHEDRAL, *city_edges))
                for e in city_edges:
                    city_segments[e] = 0

        if 'farm' in self.hint:
            farm_edge_sets = self.hint['farm']
        else:
            seed_edges = [i for i in range(8) if not (i // 2 in city_edges)]

            farm_edge_sets = []
            while seed_edges:
                seed = seed_edges[0]
                def farm_recursor(here, seed_edges, tile):
                    seed_edges.remove(here)
                    result = [here]
                    tile_edge = here // 2
                    left = (here + 7) % 8
                    right = (here + 1) % 8
                    across = 5 - here if (here // 2) % 2 == 0 else 9 - here
                    if here % 2 == 0: #left-side of an edge
                        if left in seed_edges:
                            result += farm_recursor(left, seed_edges, tile)
                        if right in seed_edges and not tile.edges[tile_edge] in (ROAD, RIVER):
                            result += farm_recursor(right, seed_edges, tile)
                    else:
                        if left in seed_edges and not tile.edges[tile_edge] in (ROAD, RIVER):
                            result += farm_recursor(left, seed_edges, tile)
                        if right in seed_edges:
                            result += farm_recursor(right, seed_edges, tile)
                    if across in seed_edges and not tile.centre in (CITY, PENNANT):
                        if min(here, across) % 2 == 0:
                            side_edge = ((min(here, across) // 2) - 1) % 4
                        else:
                            side_edge = ((min(here, across) // 2) + 1) % 4
                        if not tile.edges[side_edge] in (ROAD, RIVER):
                            result += farm_recursor(across, seed_edges, tile)
                    return result
                farm_edge_sets.append(farm_recursor(seed, seed_edges, self))

        for farm_edges in farm_edge_sets:
            farm_city_segments = set()
            for e in farm_edges:
                if e == 8: #hint that the farm includes the whole tile and all city segments
                    for seg in city_segments:
                        if not seg == None:
                            farm_city_segments.add(seg)
                else:
                    left = ((e + 7) % 8) // 2
                    right = ((e + 1) % 8) // 2
                    if city_segments[left] is not None:
                        farm_city_segments.add(city_segments[left])
                    if city_segments[right] is not None:
                        farm_city_segments.add(city_segments[right])
            builders.append((lambda fe, fcs:
                             lambda tile: Farm([FarmSegment(tile, fe, fcs)]))
                             (tuple(farm_edges), tuple(farm_city_segments)))

        return builders

    def place(self, x, y, world):
        self.x = x
        self.y = y
        self.world = world

        key = (self.edges, self.centre)
        if key not in FEATURE_CACHE:
            FEATURE_CACHE[key] = self.build_features()

        features = []

        for builder in FEATURE_CACHE[key]:
            features.append(builder(self))

        city_segments = []
        for feature in features:
            self.segments.extend(feature.segments)
            if feature.is_city():
                city_segments.append(feature.segments[0])
            if feature.is_farm():
                feature.segments[0].city_segments = tuple(city_segments[i]
                                                          for i in feature.segments[0].city_segments)

        for feature in features:
            if feature.merge:
                to_merge = set()
                for x, y, edge in feature.get_edges():
                    if x == self.x and y == self.y:
                        nx, ny, _ = feature.swap_edge(x, y, edge)
                    else:
                        nx, ny = x, y
                    other_tile = self.world[nx, ny]
                    if other_tile:
                        other_features = other_tile.features(feature.name)
                        for other_feature in other_features:
                            if feature.get_edges() & other_feature.get_edges():
                                to_merge.add(other_feature)

                for merge in to_merge:
                    feature += merge
                    if merge in self.world.features:
                        self.world.features.remove(merge)


        for feature in features[:]:
            if not feature.segments[0].feature == feature:
                features.remove(feature)

        self.world.features.extend(features)
        return features

    def rotate(self, steps):
        assert self.x==None and self.y==None
        if self.hint:
            hint = {}
            for key in self.hint:
                if key == 'farm':
                    hint['farm'] = [[h if h == 8 else (h - (steps * 2)) % 8
                                     for h in fhint]
                                    for fhint in self.hint['farm']]
                else:
                    hint[key] = [[(h - steps) % 4 if isinstance(h, int) else h
                                  for h in hh]
                                 for hh in self.hint[key]]
        else:
            hint = None
        return Tile(self.centre,
                    *[self.edges[(i + steps) % 4] for i in range(4)],
                    hint=hint)

    def reset(self):
        self.segments = []
        self.x = None
        self.y = None
        self.world = None

    def features(self, feature_name=None):
        result = list(set(s.feature for s in self.segments if s.feature))
        if feature_name:
            result = [f for f in result if f.name == feature_name]
        return result

    def __eq__(self, other):
        if isinstance(other, Tile):
            return self.x == other.x and self.y == other.y and\
                   self.edges == other.edges and self.centre == other.centre
        return NotImplemented

    def __contains__(self, other):
        if isinstance(other, Segment):
            return other in self.segments
        elif isinstance(other, Feature):
            return other in [s.feature for s in self.segments]
        return NotImplemented

    def __hash__(self):
        return hash((self.x, self.y, tuple(self.edges), self.centre))

    def __repr__(self):
        return "<Tile x=%s y=%s edges=%s centre=%s>" % \
               (self.x, self.y, [EDGES[i] for i in self.edges],
                OR_STR(self.centre))

    def image(self):
        text = [[None] * 5 for i in range(9)]
        for feature in sorted(self.features(), key=lambda x: x.zindex):
            our_tile = feature.draw().get((self.x, self.y), None)
            if our_tile:
                for j in range(5):
                    for i in range(9):
                        if our_tile[i][j]:
                            text[i][j] = our_tile[i][j]
        result = []
        for j in range(5):
            for i in range(9):
                result.append(chr(text[i][j]) if text[i][j] else ' ')
            result.append("\n")
        return ''.join(result)

class World(object):
    """
    Top-level class for in in-play game world.

    This class maintains a list of players, tiles and a global list of features
    (to avoid unnecessary object traversal to make this list on demand).

    Tile placement rules are enforced by this class - edges must match, tiles
    must be placed within a maximum extent (ie, the "table" size), and other
    special rules are enforced (eg, the river cannot turn back on itself).

    The clone method provides a sandbox world for AI players to experiment with.
    Depending on the proxify option, this is either a completely deepcopied
    version of the world or a copy-on-write proxy.
    """
    def __init__(self, options, players):
        self.tiles = {}
        self.options = options
        self.extent = options.get('extent', 20)
        self.proxify = options.get('proxify', True)
        self.players = players
        self.features = []

    def __getitem__(self, xy):
        if xy in self.tiles:
            return self.tiles[xy]
        else:
            return None

    def adjacent_edge(self, x, y, edge):
        if edge == 0:
            return x, y+1, 2
        elif edge == 1:
            return x+1, y, 3
        elif edge == 2:
            return x, y-1, 0
        else:
            return x-1, y, 1

    def can_place(self, tile, x, y):
        if abs(x) >= self.extent or abs(y) >= self.extent:
            return False
        for i in range(4):
            ox, oy, oedge = self.adjacent_edge(x, y, i)
            if self[ox, oy] and tile.edges[i] != self[ox, oy].edges[oedge]:
                return False

        if self.tiles and RIVER in tile.edges:
            #placement only valid if continuing river and not turning 180deg
            river_matched = False
            for i in range(4):
                if tile.edges[i] == RIVER:
                    ox, oy, oedge = self.adjacent_edge(x, y, i)
                    if self[ox, oy] and tile.edges[i] == self[ox, oy].edges[oedge]:
                        river_matched = True
                        break
            if not river_matched:
                return False

            river_tile = self[0, 0]
            river_edges = [i for i in range(4) if river_tile.edges[i] == RIVER]

            while True:
                nx, ny, nedge = self.adjacent_edge(river_tile.x, river_tile.y,
                                                   river_edges[-1])
                if self[nx, ny]:
                    river_tile = self[nx, ny]
                    river_edges += [i for i in range(4)
                                    if river_tile.edges[i] == RIVER
                                    and not i == nedge]
                else:
                    break

            if len(set(river_edges + [i for i in range(4)
                                      if tile.edges[i] == RIVER
                                      and not i == nedge])) > 2:
                return False
        return True

    def place(self, tile, x, y):
        self.tiles[(x, y)] = tile
        return tile.place(x, y, self)

    def possible_placements(self, tile):
        """
        Returns a list of (x, y, rotation) values where
        the given tile could be placed.
        """

        def _try(tile, i, j):
            result = []
            for r in range(4):
                if r < tile.symmetry and self.can_place(tile, i, j):
                    result.append((i, j, r))
                tile = tile.rotate(1)
            return result

        if not self.tiles:
            return [(0,0,0)]

        result = []
        for (x,y) in self.tiles:
            if not self[x+1, y]:
                result += _try(tile, x+1, y)
            if not self[x, y+1]:
                result += _try(tile, x, y+1)
            if not self[x-1, y]:
                result += _try(tile, x-1, y)
            if not self[x, y-1]:
                result += _try(tile, x, y-1)

        return sorted(set(result))

    def clone(self):
        #return pickle.loads(pickle.dumps(self))

        if self.proxify:
            return proxify(self) #faster with cpython
        else:
            return copy.deepcopy(self) #faster with pypy

    def tile_exists(self, x, y, stack):
        """
        Test whether a tile exists in stack that can be placed at (x, y).
        """
        for tile in set(stack):
            tile = copy.deepcopy(tile)
            for r in range(4):
                if r < tile.symmetry and self.can_place(tile, x, y):
                    return True
                tile = tile.rotate(1)
        return False



class Player(object):
    """
    Class representing a player in the game.

    This is detached from the class representing the human/ai interface.
    Comparison of the two should be done by comparing the index value.

    TODO: Have an avatar class rather than a list of claims.
    """
    def __init__(self, index, playertype):
        self.index = index
        self.name = "Player %d" % index
        self.playertype = playertype
        self.colour = index + 1
        self.claimed = []
        self.completed = []
        self.score = 0

    def features(self):
        return [seg.feature for seg in self.claimed]

    def __repr__(self):
        return "<Player %s: %s>" % (self.index, self.name)

    def __eq__(self, other):
        if isinstance(other, Player):
            return self.index == other.index
        elif isinstance(other, int):
            return self.index == other
        else:
            return NotImplemented

    #for some reason the default tries to call __hash__ on the new instance
    #before it has copied in the dictionary
    #connected to __eq__(int)?
    def __deepcopy__(self, memo):
        new_player = type(self)(self.index, self.playertype)
        new_player.__dict__.update(self.__dict__)
        new_player.claimed = copy.deepcopy(self.claimed, memo)
        new_player.completed = copy.deepcopy(self.completed, memo)
        return new_player

    def __hash__(self):
        return 1 << self.index
