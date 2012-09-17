import collections
import copy
import time
from feature import COLOUR_WORLD, COLOUR_CONTESTED
from world import World
try:
    import curses
except ImportError:
    try:
        import _minimal_curses as curses
    except:
        pass

class WorldBuffer(object):
    def __init__(self, extent):
        half_extent = (extent * 2) - 1
        self.pad = curses.newpad(half_extent * 5 + 1, half_extent * 9 + 1)
        self.pad.clear()
        self.extent = extent
        self.zindex = collections.defaultdict(set)

    def update_world(self, world, attrs=curses.A_NORMAL):
        """
        Trigger a complete redraw of the world
        """
        self.pad.clear()
        self.zindex = collections.defaultdict(set)
        for tile in world.tiles.values():
            self.update_pad(self._update_tile_all(tile, attrs))

    def update_tile(self, tile, attrs=curses.A_NORMAL):
        self.update_pad(self._update_tile(tile, attrs))

    def update_feature(self, feature, attrs=curses.A_NORMAL):
        self.update_pad(self._update_feature(feature, attrs))

    def _update_tile_all(self, tile, attrs=curses.A_NORMAL, zindex=-1):
        """
        Special case for _update_tile, when we want to ensure
        everything in this tile gets _attrs_ and not that they
        might be depth-first reached via _update_feature->_update_tile
        and lose _attrs_

        This probably will result in graphical artifacts if used
        in case of >1 tile - ie, it's for the tile placement display.
        """
        return [(feature, attrs) for feature in tile.features()
                if feature.zindex > zindex]

    def _update_tile(self, tile, attrs=curses.A_NORMAL, zindex=-1, memo=None):
        """
        Request that everything in a tile be updated, probably
        because it's just been drawn.

        Call update_feature on all features, providing they
        aren't already listed in memo and have a equal or greater
        z-index than the filter value.

        Returns a list of (feature, attr) pairs.
        """
        refresh_list = []
        memo = set() if memo==None else memo
        for feature in tile.features():
            if feature.zindex > zindex and feature not in memo:
                refresh_list += self._update_feature(feature, attrs,
                                                     memo=memo)

        return refresh_list

    def _update_feature(self, feature, attrs=curses.A_NORMAL, memo=None):
        """
        Request that a feature be updated.

        Looks at all the tiles this feature touches, and
        finds any objects of greater zindex that also need
        to be redrawn, and also adds them to the redraw list.
        """
        refresh_list = [(feature, attrs)]
        memo = set() if memo==None else memo
        memo.add(feature)
        for tile in feature.tiles:
            refresh_list += self._update_tile(tile, zindex=feature.zindex,
                                              memo=memo)
        return refresh_list

    def update_pad(self, refresh_list):
        """
        Takes a list of objects to redraw, sorts them by zindex
        and calls draw on each.
        """
        for feature, attrs in sorted(refresh_list, key=lambda x: x[0].zindex):
            self.draw_feature(feature, attrs)

    def xytolinecol(self, x, y):
        line = (self.extent - y - 1) * 5
        col = (self.extent + x - 1) * 9
        return line, col

    def __str__(self):
        y, x = self.pad.getmaxyx()
        result = ""
        for j in range(y):
            for i in range(x):
                result += chr(127 & self.pad.inch(j, i))
            result += "\n"
        return result

    def draw_feature(self, feature, attrs):
        spec = feature.draw()
        colour = curses.color_pair(spec.pop("colour", COLOUR_WORLD))
        if feature.cleared:
            attrs |= curses.A_DIM
        for (x, y), text in spec.items():
            line, col = self.xytolinecol(x, y)
            for tx in range(9):
                for ty in range(5):
                    char = text[tx][ty]
                    if char:
                        self.pad.addch(line+ty, col+tx, char, colour | attrs)


class NullInterface(object):
    def place_tile(self, player, tile, possible):
        raise NotImplemented

    def place_avatar(self, player, features):
        raise NotImplemented

    def add_tile(self, tile):
        pass

    def centre_map(self, x, y, update=False):
        pass

    def message(self, msg, modal=False, delay=1):
        pass

    def highlight_feature(self, feature, bold=True, update=True, message=None,
                          message_bold=None, mode=""):
        pass

class CursesInterface(object):
    def __init__(self, screen, game):
        self.screen = screen
        curses.noecho()
        if curses.has_colors():
            for i in range(1, 8):
                curses.init_pair(i, i, curses.COLOR_BLACK)

        self.game = game
        self.maxy, self.maxx = screen.getmaxyx()
        self.tilesx = self.maxx // 9
        self.tilesy = self.maxy // 5
        self.originx = (self.tilesx // 2) * 9
        self.originy = (self.tilesy // 2) * 5

        self.world_buffer = WorldBuffer(game.options['extent'] + 5)
        self.place_buffer = WorldBuffer(1)
        self.win_left = curses.newwin(8, 32, 0, 0)
        self.win_right = curses.newwin(8, 32, 0, self.maxx - 33)
        self.win_centre = curses.newwin(10, 60, self.maxy - 11,
                                        (self.maxx // 2) - 30)

    def update_left(self):
        self.win_left.clear()
        for i in range(self.game.nplayers):
            name = self.game.players[i].name[0:28].ljust(28)
            score = str(self.game.players[i].score).rjust(4)
            self.win_left.addstr(i, 0, name + score,
                                 curses.A_BOLD |
                                 curses.color_pair(self.game.players[i].colour))
        self.win_left.overlay(self.screen)

    def update_right(self, mode=""):
        player = self.game.players[self.game.turn % self.game.nplayers]
        name = player.name
        colour = player.colour
        avatars = player.available()

        self.win_right.clear()
        self.win_right.addstr(0, 0, "PYCASONNE".rjust(32), curses.A_BOLD)
        self.win_right.addstr(1, 0, ("Turn %d" % self.game.turn).rjust(32),
                              curses.A_BOLD)
        self.win_right.addstr(2, 0, ("Player %s" % name).rjust(32),
                              curses.A_BOLD | curses.color_pair(colour))
        self.win_right.addstr(3, 0, ("Remaining avatars %d" % avatars).rjust(32),
                              curses.A_BOLD)
        self.win_right.addstr(4, 0, ("Remaining tiles %d" % len(self.game.stack)).rjust(32),
                              curses.A_BOLD)
        self.win_right.addstr(5, 0, mode.rjust(32),
                              curses.A_BOLD | curses.A_REVERSE)
        self.win_right.overlay(self.screen)

    def update_centre(self, messages, bold=None):
        messages = messages[:9]
        offset = 9 - len(messages)
        self.win_centre.clear()
        for i, line in enumerate(messages):
            attrs = curses.A_REVERSE if i == bold else 0
            self.win_centre.addstr(i + offset, 0, line[0:60].center(60),
                                   curses.A_BOLD | attrs)
        self.win_centre.overlay(self.screen)

    def centre_map(self, x, y, update=False):
        line, col = self.world_buffer.xytolinecol(x, y)
        sminrow = line - self.originy
        smincol = col - self.originx
        pminrow = 0
        pmincol = 0
        if sminrow < 0:
            pminrow = abs(sminrow)
            sminrow = 0
        if smincol < 0:
            pmincol = abs(smincol)
            smincol = 0
        maxline, maxcol = self.world_buffer.pad.getmaxyx()
        pmaxrow = min(self.maxy - 1, maxline - line)
        pmaxcol = min(self.maxx - 1, maxcol - col)
        self.world_buffer.pad.overwrite(self.screen, sminrow, smincol,
                                        pminrow, pmincol, pmaxrow, pmaxcol)
        if update:
            self.screen.refresh()

    def place_tile(self, player, tile, possible):
        index = 0
        message = None
        ysorted = sorted(possible, key=lambda xyr: (xyr[1], xyr[0], xyr[2]))
        while True:
            index %= len(possible)
            if not message:
                message = ["Place tile (%d/%d options)" % \
                           (index + 1, len(possible)),
                           "Avatars available: %d" % \
                           player.available(),
                           "Arrows choose, ENTER places",
                           "'l' lists claimed features"
                           "'e' enters free exploration mode"]
            self._place_tile(tile, possible[index], message)
            message = None
            key = self.screen.getch()
            if key == curses.KEY_LEFT:
                index -= 1
            elif key == 10:#curses.KEY_ENTER:
                return possible[index % len(possible)]
            elif key == ord("l"):
                message = []
                for feature in player.features():
                    message += [feature.desc(owner=False)]
                if not message:
                    message = ["No avatars placed"]
            elif key == ord("e"):
                self.explore()
            elif key == curses.KEY_RIGHT:
                index += 1
            elif key == curses.KEY_UP:
                y_index = ysorted.index(possible[index])
                index = possible.index(ysorted[(y_index+1) % len(ysorted)])
            elif key == curses.KEY_DOWN:
                y_index = ysorted.index(possible[index])
                index = possible.index(ysorted[(y_index-1) % len(ysorted)])
            else:
                index += 1


    def explore(self):
        centre = (0, 0)
        while True:
            tile = self.game.world[centre]
            self.centre_map(*centre)
            self.update_left()
            self.update_right(mode="Explore Mode")
            if tile:
                message = ["Tile (%s, %s)" % centre]
                for feature in tile.features():
                    message += [feature.desc()]
            else:
                message = ["No tile (%s, %s)" % centre]
            message += ["Arrows navigate, any other key returns"]
            self.update_centre(message)
            self.screen.refresh()

            key = self.screen.getch()
            if key == curses.KEY_LEFT:
                centre = (centre[0]-1, centre[1])
            elif key == curses.KEY_RIGHT:
                centre = (centre[0]+1, centre[1])
            elif key == curses.KEY_UP:
                centre = (centre[0], centre[1] + 1)
            elif key == curses.KEY_DOWN:
                centre = (centre[0], centre[1] - 1)
            else:
                return

    def _place_tile(self, tile, xyr, msg):
        x, y, rotate = xyr
        self.centre_map(x, y)
        cloned_tile = copy.deepcopy(tile)
        cloned_tile = cloned_tile.rotate(rotate)
        place_world = World(self.game.options, [])
        place_world.place(cloned_tile, 0, 0)
        self.place_buffer.update_world(place_world,
                                       curses.A_BOLD |
                                       curses.color_pair(COLOUR_CONTESTED))
        self.place_buffer.pad.overwrite(self.screen, 0, 0,
                                        self.originy, self.originx,
                                        self.originy + 4, self.originx + 8)

        self.update_left()
        self.update_right("Tile Placement Mode")
        self.update_centre(msg)
        self.screen.refresh()

    def place_avatar(self, player, features):
        names = ["None"] + [f.desc(owner=False, location=False)
                            for f in features]
        features = [None] + features
        index = 0
        while True:
            index %= len(features)
            feature = features[index]
            self.highlight_feature(feature, bold=True, update=True,
                                    message=names, message_bold=index,
                                    mode="Avatar Placement Mode")
            key = self.screen.getch()
            if key in (curses.KEY_UP, curses.KEY_LEFT):
                self.highlight_feature(feature,
                                       bold=False, update=True)
                index -= 1

            elif key == 10:#curses.KEY_ENTER:
                self.highlight_feature(feature,
                                       bold=False, update=True)
                return feature
            else:
                self.highlight_feature(feature,
                                       bold=False, update=True)
                index += 1


    def highlight_feature(self, feature, bold=True, update=True, message=None,
                          message_bold=None, mode=""):
        if feature:
            self.world_buffer.update_feature(feature,
                                             curses.A_BOLD |
                                             curses.color_pair(COLOUR_CONTESTED)
                                             if bold else curses.A_NORMAL)
            self.centre_map(*feature.centre())
        self.update_left()
        self.update_right(mode)
        self.update_centre(message if message else [], message_bold)
        if update:
            self.screen.refresh()

    def message(self, message, modal=False, delay=1):
        message = message if isinstance(message, list) else [message]
        self.update_left()
        self.update_right()
        self.update_centre(message)
        self.screen.refresh()
        if modal:
            self.screen.getch()
        else:
            time.sleep(delay)

    def add_tile(self, tile):
        self.world_buffer.update_tile(tile)
