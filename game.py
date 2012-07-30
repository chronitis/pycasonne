from stack import generate_stack
from world import World, Player
from ncurses import NullInterface, CursesInterface
import copy
import random

class PlayerInterface(object):
    """
    Object providing a filtered interface through which AI classes can interact
    with the world. AIs should not attempt to access the private attributes
    to ensure consistent game state (and prevent cheating).
    """
    def __init__(self, player, game):
        self.__player = player
        self.__game = game
        self.__world = game.world

    def turn(self):
        "The current turn number (zero-indexed)."
        return self.__game.turn

    def gui(self):
        """
        Get a reference to the ncurses interface class. Might be a dummy with
        the same signature if the game is running in silent mode.
        """
        return self.__game.interface

    def set_name(self, name):
        "Set the name the game will show for us."
        self.__player.name = name

    def index(self):
        "Our index for comparing with players in the game."
        return self.__player.index

    def players(self):
        "The number of players in the game."
        return self.__game.nplayers

    def option(self, option):
        "Get a named game option."
        return self.__game.options.get(option, None)

    def score(self):
        "Get our current score (for completed features only)."
        return self.__player.score

    def scores(self):
        "Return the current scores of all players."
        return {p.index: p.score for p in self.__game.players}

    def available_avatars(self):
        "Return the number of avatars available. TODO: Redo avatars."
        return self.option("avatars") - len(self.__player.claimed)

    def claimed_features(self):
        "Return a (proxied) list of the features we have claimed."
        return self.sandbox().players[self.index()].features()

    def completed_features(self):
        "Return a (proxied) list of features we've completed."
        return self.sandbox().players[self.index()].completed

    def turns_left(self):
        "The number of turns left for all players."
        return len(self.__game.stack)

    def our_turns_left(self):
        "The number of we have left to play."
        our_turns = [i for i in range(self.turn(),
                                      self.turn()+self.turns_left())
                     if i % self.players() == self.index()]
        return len(our_turns)

    def sandbox(self):
        """
        Get a version of the world to experiment with. Depending on the game
        configuration, this may either be a completely deep-copied version of
        the world or a copy-on-write proxy. Functionality should be the same
        in either case - it should function identically (but classes might be
        named as ProxyX instead of X and produce unusual eg, dir() results.
        """
        return self.__world.clone()

    def stack(self):
        """
        Returns a dictionary of tile -> count showing the types of tiles left
        in the stack (but not the order).
        """
        result = collections.defaultdict(int)
        for tile in self.__game.stack:
            result[tile] += 1
        return result

class PlayerBase(object):
    """
    Base class for human interface or AI players. The first argument is an
    :class:`PlayerInterface` object with which the class can query the game
    state. Only the place_tile and place_avatar methods are mandatory.
    """
    def __init__(self, interface, **kwargs):
        self.interface = interface

    def game_start(self, nplayers):
        """
        Called at game start with the number of players.
        """
        pass

    def place_tile(self, tile, possible):
        """
        Called with a tile object, and a list of
        (x, y, rotate_steps) valid placements.

        Return one of the placements as you see fit.
        """
        raise NotImplementedError

    def place_avatar(self, features):
        """
        Called with a list of feature objects available
        on the just-placed tile, choose one or
        return None to do nothing.
        """
        raise NotImplementedError

    def tile_placed(self, tile, x, y):
        """
        Information callback when any player places
        a tile, giving the tile object and x,y coords.
        """
        pass

    def avatar_placed(self, feature, player):
        """
        Information callback when any player places
        an avatar, giving the feature and player.
        """
        pass

    def feature_completed(self, feature, players, score):
        """
        Information callback when a feature is deemed
        completed, giving the feature, benefitting player(s)
        and score.
        """
        pass

    def game_over(self):
        """
        Information callback at game over, giving a chance
        for debrief and state save, if necessary.
        """
        pass

class Human(PlayerBase):
    def game_start(self, nplayers):
        self.gui = self.interface.gui()

    def place_tile(self, tile, possible):
        return self.gui.place_tile(self.interface._PlayerInterface__player,
                                   tile, possible)

    def place_avatar(self, features):
        return self.gui.place_avatar(self.interface._PlayerInterface__player,
                                     features)

class Game(object):
    default_options = {
        "river": True,
        "extent": 20,
        "avatars": 7,
        "proxify": True,
        "inns-cathedrals": True,
        "shuffle-unplaceable": True
    }
    option_help = {
        "river": "Enable the river expansion.",
        "extent": "Size of the game table.",
        "avatars": "Number of avatar pieces per player.",
        "proxify": "Whether to use copy-on-write or deepcopy to provide AI sandboxes.",
        "inns-cathedrals": "Enable the inns & cathedrals expansion.",
        "shuffle-unplaceable": "Whether to re-shuffle the stack after a player draws an unplaceable tile."
    }
    def __init__(self, playerclasses, playeroptions=None, **options):
        self.options = {}
        self.options.update(Game.default_options)
        self.options.update(options)
        self.nplayers = len(playerclasses)
        if not playeroptions:
            playeroptions = [{} for _ in range(self.nplayers)]
        else:
            assert len(playeroptions) == self.nplayers
        assert 2 <= self.nplayers <= 6, "Too many or few players"
        reorder = list(range(self.nplayers))
        random.shuffle(reorder)
        playerclasses = [playerclasses[i] for i in reorder]
        playeroptions = [playeroptions[i] for i in reorder]
        self.players = [Player(i, pc) for i, pc in enumerate(playerclasses)]

        self.stack = generate_stack(river=self.options['river'],
                                    inns_cathedrals=self.options['inns-cathedrals'])
        if self.options['inns-cathedrals']:
            self.options['avatars'] += 1
        self.world = World(self.options, self.players)
        self.turn = 0

        self.ai = [self.get_ai(pc)(interface=PlayerInterface(p, self), **po)
                   for p, pc, po in zip(self.players, playerclasses, playeroptions)]
        self.interface = None

    def get_ai(self, ainame):
        return AI_REGISTRY[ainame]

    def play(self, screen=None):
        if screen:
            self.interface = CursesInterface(screen, self)
        else:
            self.interface = NullInterface()

        for ai in self.ai:
            ai.game_start(self.nplayers)

        while self.stack:
            player = self.players[self.turn % self.nplayers]
            ai = self.ai[self.turn % self.nplayers]


            if self.options['shuffle-unplaceable']:
                attempts = 0
                while True:
                    tile = self.stack.pop(0)
                    possible_locations = self.world.possible_placements(tile)
                    if possible_locations:
                        break
                    else:
                        self.stack.insert(random.randint(1, len(self.stack)), tile)
                        attempts += 1
                        assert attempts < 10, "No possible tile placements after 10 reshuffles"
            else:
                tile = self.stack.pop(0)
                possible_locations = self.world.possible_placements(tile)
                assert possible_locations, "No possible tile placements"
            chosen_placement = ai.place_tile(copy.deepcopy(tile),
                                             possible_locations)
            assert chosen_placement in possible_locations, "Chose %s not in %s" % (chosen_placement, possible_locations)
            x, y, rotate = chosen_placement
            tile = tile.rotate(rotate)
            assert self.world.can_place(tile, x, y)
            features = self.world.place(tile, x, y)
            features = [f for f in features if f.can_own()]
            self.interface.add_tile(tile)
            self.interface.centre_map(x, y)
            self.interface.message("")
            for i in self.ai:
                i.tile_placed(tile, x, y)
            if self.options['avatars'] - len(player.claimed) > 0 and features:
                chosen_feature = ai.place_avatar(features)
                if chosen_feature:
                    assert chosen_feature in features, "AI returned invalid feature: %s (valid %s)" % (chosen_feature, features)
                    chosen_feature.claim(player)
                    player.claimed += [chosen_feature.segments[-1]]
                    self.interface.highlight_feature(chosen_feature)
                    self.interface.message("%s claimed %s" % \
                                           (player.name, chosen_feature.name))
                    self.interface.highlight_feature(chosen_feature, False)
                    for i in self.ai:
                        i.avatar_placed(chosen_feature, player)

            for feature in self.world.features:
                if feature.is_complete() and not feature.cleared:
                    score = feature.score()
                    feature.cleared = True
                    owners = feature.get_owner()
                    for owner in owners:
                        owner.score += score
                        for seg in owner.claimed[:]:
                            if seg.feature == feature:
                                owner.claimed.remove(seg)
                        assert not feature in [seg.feature
                                               for seg in owner.claimed]
                        owner.completed.append(feature)
                    if owners:
                        self.interface.highlight_feature(feature)
                        self.interface.message("%s completed for %d" % \
                                               (feature.name, score))
                        self.interface.highlight_feature(feature, False)
                    for i in self.ai:
                        i.feature_completed(feature, owners, score)
            self.turn += 1

        for player in self.players:
            for seg in player.claimed:
                feature = seg.feature
                assert not feature.cleared
                assert not feature.is_complete()
                if player in feature.get_owner():
                    score = feature.score()
                    player.score += score
                    while feature in player.claimed:
                        player.claimed.remove(feature)
                    self.interface.highlight_feature(feature)
                    self.interface.message("incomplete %s worth %d" % \
                                           (feature.name, score))
                    self.interface.highlight_feature(feature, False)
                    for i in self.ai:
                        i.feature_completed(feature, [player], score)
        self.interface.message("Game over")
        msg = []
        for i, player in enumerate(sorted(self.players,
                                          key=lambda x: x.score, reverse=True)):
            msg.append("%d: %s (%s) with %d" % \
                       (i+1, player.name, player.playertype, player.score))
        self.interface.message(msg, delay=5)
        for i in self.ai:
            i.game_over()
        return {p.name: p.score for p in self.players}

AI_REGISTRY = {}
from basic_ai import BasicAI
from random_ai import RandomAI
from genetic_ai import GeneticAI
AI_REGISTRY['Human'] = Human
AI_REGISTRY['BasicAI'] = BasicAI
AI_REGISTRY['RandomAI'] = RandomAI
AI_REGISTRY['GeneticAI'] = GeneticAI
