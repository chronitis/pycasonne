from game import PlayerBase
import random
import collections
import base64
import math
from ai_names import random_name

#scales 0-255 to log-distributed e**-1 -> e
BYTE_TO_E = lambda x: math.pow(math.e, (x/128.)-1)
BYTE_TO_1 = lambda x: x/255.

class Genome(object):

    @classmethod
    def crossover(cls, parent0, parent1):

        point = random.randint(0, 8*len(cls.parts)-1)
        data0 = parent0.data
        data1 = parent1.data

        new_data0 = data0[:]
        new_data1 = data1[:]

        i = point // 8
        point %= 8

        mask_low = (1 << point+1) - 1
        mask_high = 0xff ^ mask_low

        new_data0[i] = (data0[i] & mask_low) | (data1[i] & mask_high)
        new_data1[i] = (data1[i] & mask_low) | (data0[i] & mask_high)

        new_data0[i+1:], new_data1[i+1:] = data1[i+1:], data0[i+1:]

        return cls(new_data0), cls(new_data1)

    parts = [
        ('city_factor', BYTE_TO_E),
        ('road_factor', BYTE_TO_E),
        ('farm_factor', BYTE_TO_E),
        ('cloister_factor', BYTE_TO_E),
        ('avatar_use_factor', BYTE_TO_E),
        ('avatar_return_factor', BYTE_TO_E),
        ('coop_factor', BYTE_TO_E),
        ('farm_city_factor', BYTE_TO_E),
        ('open_edge_factor', BYTE_TO_E),
    ]

    def __init__(self, data=None):
        if data:
            self.data = data
        else:
            self.data = [random.randint(0, 255) for _ in self.parts]
        self.update()

    def __eq__(self, other):
        if isinstance(other, Genome):
            return self.data == other.data
        return NotImplemented

    def __hash__(self):
        return hash(tuple(self.data))

    def update(self):
        for i, (name, func) in enumerate(self.parts):
            setattr(self, name, func(self.data[i]))

    def mutate(self, prob=0.05):
        for i in range(len(self.parts)):
            for j in range(8):
                if random.random() < prob:
                    self.data[i] ^= (1 << j)
        self.update()

    def name(self):
        return base64.encodestring(bytes(self.data))

    def __repr__(self):
        inner = " ".join("%s=%.2f" % (p[0], getattr(self, p[0])) for p in self.parts)
        return "<Genome %s>" % inner


class TestGenome(object):
    city_factor = 1.5
    road_factor = 1
    farm_factor = 1
    cloister_factor = 1.5
    avatar_use_factor = 0.5
    avatar_return_factor = 0.5
    coop_factor = 0.5
    farm_city_factor = 1.5
    open_edge_factor = 0.5

class GeneticAI(PlayerBase):
    def __init__(self, interface, name=None, genome=None, **kwargs):
        self.interface = interface
        if genome == None:
            self.genome = Genome()
        else:
            self.genome = genome
        self.chosen_feature_segment = None
        self.index = self.interface.index()
        if name == None:
            self.name = random_name()
        else:
            self.name = name
        self.interface.set_name(self.name)
        self.nplayers = 0

    def game_start(self, nplayers):
        self.nplayers = nplayers

    def dedup(self, src):
        result = []
        for s in src:
            if s not in result:
                result.append(s)
        return result

    def eval_feature(self, feature):
        score = feature.score()
        if feature.is_road():
            score *= self.genome.road_factor
        elif feature.is_city():
            score *= self.genome.city_factor
        elif feature.is_cloister():
            score *= self.genome.cloister_factor
        elif feature.is_farm():
            score += self.genome.farm_city_factor * len(feature.cities(complete=False))
            score *= self.genome.farm_factor
        if len(feature.owners) > 1:
            score *= self.genome.coop_factor
        return score

    def place_tile(self, tile, possible):
        best_score = -1e100
        best_choice = []
        turns_left = self.interface.our_turns_left()
        avatars = self.interface.available_avatars()

        scores = collections.defaultdict(float)
        world_features = self.interface.sandbox().features
        for feature in world_features:
            for owner in feature.owners:
                scores[owner.index] += self.eval_feature(feature)

        for (x, y, rotate) in possible:
            sandbox = self.interface.sandbox()
            placement_feature_score = 0
            placement_feature = None
            tile_features = sandbox.place(tile.rotate(rotate), x, y)

            placement_scores = collections.defaultdict(float)
            for feature in sandbox.features:
                for owner in feature.owners:
                    placement_scores[owner.index] += self.eval_feature(feature)

            for feature in tile_features:
                if feature.owners:
                    if feature.is_complete():
                        for owner in set(feature.owners):
                            available = owner.available()
                            if available < turns_left:
                                placement_scores[owner.index] += (turns_left / max(available, 0.5)) * self.genome.avatar_return_factor

                elif feature.can_own():
                    if avatars:
                        score = self.eval_feature(feature)
                        if not feature.is_complete():
                            if avatars < turns_left:
                                score -= (turns_left / max(avatars, 0.5)) * self.genome.avatar_use_factor
                            if feature.is_city():
                                edges = len(feature.get_edges())
                                score -= (edges / max(turns_left, 0.5)) * self.genome.open_edge_factor

                        if score > placement_feature_score:
                            placement_feature_score = score
                            placement_feature = feature.segments[0]


            our_benefit = placement_scores[self.index] - scores[self.index]
            their_benefit = 0
            for i in range(self.nplayers):
                if not i == self.index:
                    their_benefit += placement_scores[i] - scores[i]

            placement_score = our_benefit + placement_feature_score - their_benefit
            if placement_score > best_score:
                best_score = placement_score
                best_choice = [(placement_feature, (x, y, rotate))]
            elif placement_score == best_score:
                best_choice += [(placement_feature, (x, y, rotate))]

        best_segment, best_xyr = random.choice(best_choice)

        self.chosen_feature_segment = best_segment
        return best_xyr


    def place_avatar(self, features):
        if self.chosen_feature_segment:
            for f in features:
                if self.chosen_feature_segment in f.segments:
                    return f
        return None

