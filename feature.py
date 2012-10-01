import collections

NORTH, EAST, SOUTH, WEST = range(4)
COLOUR_WORLD = 0
COLOUR_CONTESTED = 6
COLOUR_RIVER = 6

CHAR_CITY, CHAR_WALL, CHAR_PENNANT = ord('^'), ord('#'), ord('>')
CHAR_CATHEDRAL = ord('+')
CHAR_VROAD, CHAR_HROAD, CHAR_INN = ord('|'), ord('='), ord('*')
CHAR_LROAD, CHAR_RROAD = ord('\\'), ord('/')
CHAR_CLOISTER = ord('+')
CHAR_RIVER = ord('~')
CHAR_FARM = ord("`")

class Feature(object):
    """
    Base class for map features (roads, towns, etc). May be mergeable.
    Features have properties:
        * owner(s)
        * completion
        * score
        * tile(s)

    Features are mutable, unlike Segments, which are immutable once created.
    """
    merge = False
    name = None
    zindex = None
    def __init__(self, tiles=None):
        self.avatars = []
        self.owners = []
        self.tiles = tiles if tiles else []
        self.cleared = False

    def score(self):
        "Calculate the score, usually taking completion into account"
        return 0

    def can_own(self):
        "Return whether a player can take control of this feature"
        return False

    def claim(self, avatar):
        assert avatar.available
        if self.can_own():
            self.avatars.append(avatar)
            self.update_owners()
            return True
        else:
            return False
          
    def update_owners(self):
        if len(self.avatars) == 0:
            self.owners = []
        elif len(self.avatars) == 1:
            self.owners = [self.avatars[0].player]
        else:
            owner_scores = collections.defaultdict(int)
            for a in self.avatars:
                owner_scores[a.player] += a.strength
            best_score = max(owner_scores.values())
            self.owners = list(p for p in owner_scores if owner_scores[p] == best_score)

    def is_complete(self):
        """
        Return true when the feature is completed and the player gets their
        avatar freed.
        """
        return False

    def desc(self, owner=True, location=True):
        """
        Get a string describing the feature for UI purposes.
        """
        s_owner = ""
        if owner and not self.owners:
            s_owner = "Unowned "
        elif owner and len(self.owners) == 1:
            s_owner = owners[0].name + " "
        elif owner and self.owners:
            s_owner = "Contested "

        s_location = ""
        if location:
            s_location = " @ "+str(self.centre())

        return s_owner + self.name + s_location + ": %s points (%s tiles)" % \
                                                (self.score(), len(self.tiles))

    def get_colour(self):
        """
        Get the appropriate colour to represent the feature (unowned, player
        colour, contested colour).
        """
        if len(self.owners) == 1:
            return self.owners[0].colour
        elif len(self.owners) == 0:
            return COLOUR_WORLD
        else:
            return COLOUR_CONTESTED

    def draw(self):
        """
        Return a dict of (tilex, tiley) -> 9x5 char or None,
        plus a "colour" element
        """
        return {}

    def centre(self):
        """
        Get the weigted centre of the feature to centre the map on.
        """
        x = 0.
        y = 0
        for t in self.tiles:
            x += t.x
            y += t.y
        x /= len(self.tiles)
        y /= len(self.tiles)
        return int(x), int(y)

    def is_city(self):
        "Convienience method to test if the feature is a city"
        return False
    def is_road(self):
        "Convienience method to test if the feature is a road"
        return False
    def is_farm(self):
        "Convienience method to test if the feature is a farm"
        return False
    def is_cloister(self):
        "Convienience method to test if the feature is a cloister"
        return False

class Segment(object):
    """
    A single part of a feature on one tile. This is created when the tile is
    placed and should be immutable after that (except for the feature pointer
    being updated to point to the feature it currently belongs to).

    Since these are immutable, when trying to keep a persistent reference
    to a feature you should keep a reference to a single segment and read
    segment.feature to get the current feature (which will change when extra
    tiles are added and the existing feature pointer might be invalidated).
    """
    type = 0
    def __init__(self, tile, edges):
        self.tile = tile
        self.edges = tuple(edges)
        self.feature = None
        self.hash = None

    def __hash__(self):
        if self.hash is None:
            self.hash = hash((self.type, self.tile.x, self.tile.y, self.edges))
        return self.hash

    def __eq__(self, other):
        if isinstance(other, Segment):
            return self.type == other.type and self.tile.x == other.tile.x and \
                   self.tile.y == other.tile.y and self.edges == other.edges
        return NotImplemented


class SegmentedFeature(Feature):
    """
    A feature consisting of a number of segments (ie, all of them except
    a cloister). Each component segment has a pointer to the feature to which
    it belongs.
    """
    merge = True
    def __init__(self, segments):
        self.segments = segments
        tiles = list(set(s.tile for s in segments))
        Feature.__init__(self, tiles=tiles)
        for s in self.segments:
            s.feature = self

    def is_complete(self):
        return not self.get_edges()

    def __eq__(self, other):
        if isinstance(other, SegmentedFeature):
            return self.segments == other.segments or \
                   set(self.segments) == set(other.segments)
        return NotImplemented

    def __hash__(self):
        return hash(tuple(self.segments))

    def __contains__(self, other):
        if isinstance(other, Segment):
            return other in self.segments
        return NotImplemented

    def get_edges(self, normalise=True):
        """
        Get a set of feature edges which remain open (ie, are the edge of
        the world with no adjacent tile). The edge sets are normalised so
        the edge index should always be (0, 1) with the (x, y) coordinates
        adjusted appropriately.

        The return is of the form set((x, y, edge), ...)
        """
        open_edges = set()
        for seg in self.segments:
            for edge in seg.edges:
                if edge == 8:
                    continue
                x, y = seg.tile.x, seg.tile.y
                if normalise:
                    x, y, edge = self.normalise_edge(x, y, edge)
                if (x, y, edge) in open_edges:
                    open_edges.remove((x, y, edge))
                else:
                    open_edges.add((x, y, edge))
        return open_edges

    def normalise_edge(self, x, y, edge):
        """
        Convert an (x, y, edge) set into a normalised edge (with x, y possibly
        adjusted so that edge-sets are comparable).
        """
        if edge >= 2:
            return self.swap_edge(x, y, edge)
        else:
            return x, y, edge

    def swap_edge(self, x, y, edge):
        """
        Implement edge-swapping.
        """
        if edge == 0:
            return x, y+1, 2
        elif edge == 1:
            return x+1, y, 3
        elif edge == 2:
            return x, y-1, 0
        elif edge == 3:
            return x-1, y, 1

    def __iadd__(self, other):
        """
        Join two features, performing the necessary updates. Other is invalid
        after it has been added.
        """
        assert not set(self.segments) & set(other.segments), "merging already overlapping features %s %s %s %s" % (self, other, [hash(s) for s in self.segments], [hash(s) for s in other.segments])
        assert self.get_edges() & other.get_edges(), "edges don't meet %s %s %s %s" % (self, other, self.get_edges(), other.get_edges())
        self.segments += other.segments
        for s in self.segments:
            s.feature = self
        self.tiles = list(set(s.tile for s in self.segments))
        self.avatars.extend(other.avatars)
        self.update_owners()
        return self

    def __repr__(self):
        return "<%s %s>" % (self.name, self.segments)

    def segments_by_tile(self):
        """
        Return a dictionary of x, y -> list(segment, ...)
        """
        result = collections.defaultdict(list)
        for seg in self.segments:
            result[(seg.tile.x, seg.tile.y)] += [seg]
        return result

    def draw(self):
        """
        Return a dictionary for ncurses drawing, consisting of a colour element
        and x, y -> 9x5 array of character codes.
        """
        result = {"colour": self.get_colour()}
        for tile, segments in self.segments_by_tile().items():
            result[tile] = self.draw_tile(segments)
        return result

    def draw_tile(self, segments):
        """
        Return a 9x5 array of character codes (as ints) representing the one or
        more segments in any given tile. Empty cells should be left as None.
        """
        text = [[None]*5 for i in range(9)]
        for seg in segments:
            edges = tuple(sorted(seg.edges))
            if len(edges) == 1:
                if edges == (0,):
                    for i in range(3):
                        text[4][i] = self.VCHAR
                elif edges == (2,):
                    for i in range(2, 5):
                        text[4][i] = self.VCHAR
                elif edges == (3,):
                    for i in range(5):
                        text[i][2] = self.HCHAR
                elif edges == (1,):
                    for i in range(4, 9):
                        text[i][2] = self.HCHAR
            else:
                if edges == (0, 2):
                    for i in range(5):
                        text[4][i] = self.VCHAR
                elif edges == (1, 3):
                    for i in range(9):
                        text[i][2] = self.HCHAR
                else:
                    if 0 in edges:
                        text[4][0] = self.VCHAR
                    if 1 in edges:
                        for i in range(6, 9):
                            text[i][2] = self.HCHAR
                    if 2 in edges:
                        text[4][4] = self.VCHAR
                    if 3 in edges:
                        for i in range(3):
                            text[i][2] = self.HCHAR
                    if edges == (0, 1):
                        text[5][1] = self.LDIAG
                    elif edges == (1, 2):
                        text[5][3] = self.RDIAG
                    elif edges == (2, 3):
                        text[3][3] = self.LDIAG
                    else:
                        text[3][1] = self.RDIAG
        return text

class CitySegment(Segment):
    """
    One distinct walled area of city, possibly with a pennant or cathedral.
    """
    type = 1
    def __init__(self, tile, edges, pennant=False, cathedral=False):
        self.pennant = pennant
        self.cathedral = cathedral
        Segment.__init__(self, tile, edges)

    def __repr__(self):
        return "<CitySegment x=%d y=%d edges=%s%s%s>" % \
               (self.tile.x, self.tile.y, self.edges,
               " pennant" if self.pennant else "",
               " cathedral" if self.cathedral else "")


class City(SegmentedFeature):
    """
    City - complete when city wall is unbroken.
    Worth 2 points per tile if complete, 1 point otherwise.
    Pennant tiles are worth double.
    Cities containing a cathedral are worth 3 per tile when completed.
    """
    name = "City"
    zindex = 3
    def score(self):
        cathedral = False
        tiles = set()
        pennant_tiles = set()
        for seg in self.segments:
            if seg.pennant:
                pennant_tiles.add((seg.tile.x, seg.tile.y))
            else:
                tiles.add((seg.tile.x, seg.tile.y))
            if seg.cathedral:
                cathedral = True
        score = len(tiles) + 2*len(pennant_tiles)
        if self.is_complete():
            if cathedral:
                return score*3
            else:
                return score*2
        else:
            return score

    def can_own(self):
        return not self.owners

    def is_city(self):
        return True

    def draw_tile(self, segments):
        def _draw_wall(text, edge, fill=True):
            if edge == 0:
                text[0][0] = CHAR_WALL
                text[8][0] = CHAR_WALL
                for i in range(1, 8):
                    text[i][1] = CHAR_WALL
                    text[i][0] = CHAR_CITY if fill else None
            elif edge == 2:
                text[0][4] = CHAR_WALL
                text[8][4] = CHAR_WALL
                for i in range(1, 8):
                    text[i][3] = CHAR_WALL
                    text[i][4] = CHAR_CITY if fill else None
            elif edge == 3:
                text[0][0] = CHAR_WALL
                text[0][4] = CHAR_WALL
                for i in range(1, 4):
                    text[1][i] = CHAR_WALL
                    text[0][i] = CHAR_CITY if fill else None
            else:
                text[8][0] = CHAR_WALL
                text[8][4] = CHAR_WALL
                for i in range(1, 4):
                    text[7][i] = CHAR_WALL
                    text[8][i] = CHAR_CITY if fill else None
        text = [[None]*5 for i in range(9)]
        for seg in segments:
            edges = tuple(sorted(seg.edges))
            if len(edges) >= 3:
                for i in range(9):
                    for j in range(5):
                        text[i][j] = CHAR_CITY
                if seg.pennant:
                    text[4][2] = CHAR_PENNANT
                if seg.cathedral:
                    for i in range(2, 7):
                        for j in range(1, 4):
                            text[i][j] = CHAR_CATHEDRAL
                if len(edges) == 3:
                    open_edge = [i for i in range(4) if i not in edges][0]
                    _draw_wall(text, open_edge, False)
            elif len(edges) == 2:
                _draw_wall(text, edges[0], True)
                _draw_wall(text, edges[1], True)
                if edges == (0, 1):
                    text[8][0] = CHAR_PENNANT if seg.pennant else CHAR_CITY
                elif edges == (1, 2):
                    text[8][4] = CHAR_PENNANT if seg.pennant else CHAR_CITY
                elif edges == (2, 3):
                    text[0][4] = CHAR_PENNANT if seg.pennant else CHAR_CITY
                elif edges == (0, 3):
                    text[0][0] = CHAR_PENNANT if seg.pennant else CHAR_CITY
                elif edges == (0, 2):
                    _draw_wall(text, 1, False)
                    _draw_wall(text, 3, False)
                    for i in range(2, 7):
                        for j in range(1, 4):
                            text[i][j] = CHAR_CITY
                    if seg.pennant:
                        text[4][2] = CHAR_PENNANT
                elif edges == (1, 3):
                    _draw_wall(text, 0, False)
                    _draw_wall(text, 2, False)
                    for i in range(1, 8):
                        text[i][2] = CHAR_CITY
                    if seg.pennant:
                        text[4][2] = CHAR_PENNANT
            else:
                _draw_wall(text, edges[0], True)
        return text


class Cloister(Feature, Segment):
    """
    Cloister
    Worth 1 point + 1 per adjacent tile
    """
    name = "Cloister"
    type = 2
    zindex = 3
    def __init__(self, tile):
        self.tile = tile
        self.edges = ()
        self.feature = self
        self.segments = (self, )
        self.hash = None
        Feature.__init__(self, tiles=[tile])

    def can_own(self):
        return not self.owners

    def is_cloister(self):
        return True

    def score(self):
        x, y = self.tile.x, self.tile.y
        world = self.tile.world
        score = 0
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                if world[x+i, y+j]:
                    score += 1
        return score

    def is_complete(self):
        return self.score() == 9

    def __repr__(self):
        return "<Cloister x=%d y=%d>" % (self.tile.x, self.tile.y)

    def draw(self):
        text = [[None]*5 for i in range(9)]
        for i in range(2, 7):
            for j in range(1, 4):
                text[i][j] = CHAR_CLOISTER
        return {"colour": self.get_colour(), (self.tile.x, self.tile.y): text}

class RoadSegment(Segment):
    """
    A single piece of road.
    """
    type = 3
    def __init__(self, tile, edges, inn=False):
        self.inn = inn
        Segment.__init__(self, tile, edges)

    def __repr__(self):
        return "<RoadSegment x=%d y=%d edges=%s%s>" % \
               (self.tile.x, self.tile.y, self.edges,
                " inn" if self.inn else "")

class Road(SegmentedFeature):
    """
    Road
    Worth 1 point per tile.
    """
    VCHAR = CHAR_VROAD
    HCHAR = CHAR_HROAD
    LDIAG = CHAR_LROAD
    RDIAG = CHAR_RROAD
    zindex = 2
    name = "Road"
    def score(self):
        tiles = set()
        inn = False
        for seg in self.segments:
            tiles.add(seg.tile)
            if seg.inn:
                inn = True
        if inn:
            return len(tiles) * 2
        else:
            return len(tiles)

    def can_own(self):
        return not self.owners

    def is_road(self):
        return True

    def draw_tile(self, segments):
        text = super(Road, self).draw_tile(segments)
        for seg in segments:
            if seg.inn:
                text[4][2] = CHAR_INN
        return text


class FarmSegment(Segment):
    """
    A single segment of farm. Contains a tuple of attached city segments.
    Edges of farms are in the range 0-7 rather than 0-3 (also ordered
    clockwise from north). Edge 8 is a special value indicating the whole tile.
    """
    type = 4
    def __init__(self, tile, edges, city_segments):
        self.city_segments = tuple(city_segments)
        Segment.__init__(self, tile, edges)
    def __repr__(self):
        return "<FarmSegment x=%d y=%d edges=%s citysegs=%s>" % \
               (self.tile.x, self.tile.y, self.edges, self.city_segments)

class Farm(SegmentedFeature):
    """
    Farm
    Worth 3 per complete city served.
    This is the messy one.
    """
    zindex = 0
    name = "Farm"
    def is_complete(self):
        return False

    def normalise_edge(self, x, y, edge):
        if edge == 8:
            return x, y, edge
        elif edge >= 4:
            return self.swap_edge(x, y, edge)
        else:
            return x, y, edge

    def is_farm(self):
        return True

    def can_own(self):
        return not self.owners

    def swap_edge(self, x, y, edge):
        e2 = edge // 2
        if e2 == 0:
            return x, y + 1, 5-edge
        elif e2 == 1:
            return x + 1, y, 9-edge
        elif e2 == 2:
            return x, y - 1, 5-edge
        else:
            return x - 1, y, 9-edge

    def cities(self, complete=None):
        """
        Get a list of cities associated with this farm (optionally selecting
        only complete or incomplete cities).
        """
        city_segments = set()
        for seg in self.segments:
            for cs in seg.city_segments:
                city_segments.add(cs)
        cities = set(s.feature for s in city_segments)
        if complete == True:
            return [c for c in cities if c.is_complete()]
        elif complete == False:
            return [c for c in cities if not c.is_complete()]
        else:
            return list(cities)

    def score(self):
        return 3*len(self.cities(complete=True))

    def draw_tile(self, segments):
        text = [[None]*5 for i in range(9)]
        for seg in segments:
            for edge in seg.edges:
                if edge == 8:
                    for i in range(9):
                        for j in range(5):
                            text[i][j] = CHAR_FARM
                else:
                    xr1 = (0, 5) if edge in (5, 6, 7, 0) else (4, 9)
                    if edge in (0, 1):
                        y1 = 0
                    elif edge in (4, 5):
                        y1 = 4
                    else:
                        y1 = 2

                    if edge in (6, 7):
                        xr2 = (0, 3)
                    elif edge in (0, 5):
                        xr2 = (2, 5)
                    elif edge in (1, 4):
                        xr2 = (4, 7)
                    else:
                        xr2 = (6, 9)
                    y2 = 1 if edge in (7, 0, 1, 2) else 3

                    if edge in (6, 7):
                        x3 = 0
                    elif edge in (2, 3):
                        x3 = 8
                    else:
                        x3 = 4
                    if edge in (2, 7):
                        y3 = 0
                    elif edge in (3, 6):
                        y3 = 4
                    else:
                        y3 = 2

                    for i in range(*xr1):
                        text[i][y1] = CHAR_FARM
                    for i in range(*xr2):
                        text[i][y2] = CHAR_FARM
                    text[x3][y3] = CHAR_FARM
        return text

class RiverSegment(Segment):
    """
    A segment of river.
    """
    type = 5
    def __repr__(self):
        return "<RiverSegment x=%d y=%d edges=%s>" % \
               (self.tile.x, self.tile.y, self.edges)

class River(SegmentedFeature):
    """
    River feature. Cannot be owned by players.
    """
    zindex = 1
    VCHAR = CHAR_RIVER
    HCHAR = CHAR_RIVER
    LDIAG = CHAR_RIVER
    RDIAG = CHAR_RIVER
    name = "River"
    def get_colour(self):
        return COLOUR_RIVER



