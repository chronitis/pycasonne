from game import PlayerBase
from ai_names import NAMES
import random

class FakeFile(object):
    def write(self, s):
        pass

class BasicAI(PlayerBase):
    """
    A simple AI that plays a reasonable game but one unlikely to seriously
    challenge a human player. It evaluates its position separately each
    turn, trying to pick the most sensible tile placement and feature choice
    but doesn't do anything more sophisticated like attempt multi-turn thefts
    of features or plan ahead for the value of farms.
    """
    def __init__(self, interface, **kwargs):
        self.interface = interface
        self.chosen_feature_segment = None
        self.index = self.interface.index()
        self.name = NAMES.pop(random.randint(0, len(NAMES) - 1))
        self.interface.set_name(self.name)
        self.debug = FakeFile()#open("basicai-%s" % self.name, "w")

    def place_tile(self, tile, possible):

        self.debug.write("begin turn %d score %d\n" % \
                         (self.interface.turn(), self.interface.score()))
        self.debug.write("tile %s\n" % tile)

        best_score = -1e100
        best_choice = []

        claimed = self.interface.claimed_features()

        self.debug.write("claimed\n%s\n" % '\n'.join(str(c) for c in claimed))

        avatars = self.interface.available_avatars()

        self.debug.write("available %d\n" % avatars)

        partial_score = sum(f.score() for f in claimed)
        self.debug.write("potential score %d\n" % partial_score)

        for (x, y, rotate) in possible:
            self.debug.write("possible move %s\n" % ((x, y, rotate),))
            sandbox = self.interface.sandbox()
            placement_score = 0
            placement_feature_score = 0
            placement_feature = None
            for feature in sandbox.place(tile.rotate(rotate), x, y):
                self.debug.write("\tfeature %s %s\n" % (feature, feature.owners))

                #if we already own the feature
                if self.index in feature.owners:
                    self.debug.write("\t\towned by us\n")

                    #find the increased value of existing claims by adding this piece
                    new_score = feature.score()
                    for c in claimed:
                        if not set(feature.segments) & set(c.segments):
                            new_score += c.score()
                    new_score -= partial_score
                    self.debug.write("\t\tinitial score %s\n" % new_score)

                    #if we're a minority holder, score becomes a penalty
                    if self.index not in feature.owner:
                        self.debug.write("\t\tminority shareholder\n")
                        new_score = -new_score
                    #or if we're sharing the score with others, reduce it
                    elif len(feature.owner) > 1:
                        self.debug.write("\t\tequal partner\n")
                        #here we should consider whether we're helping someone ahead of us or not
                        #rather than apply a blanket penalty - cooperation is usually wise unless
                        #we're in first place
                        new_score /= 2.

                    #if this completes a feature and frees an avatar, boost value
                    #providing there are enough turns left to use it
                    if feature.is_complete():
                        self.debug.write("\t\twill complete feature\n")
                        if self.interface.turns_left() > avatars:
                            self.debug.write("\t\tsufficient turns to re-use avatar\n")
                            new_score += 2

                    #increase the desirability of adding to cities a bit to reflect
                    #the bonus for city completion
                    if feature.name == "City":
                        self.debug.write("\t\tcity bonus\n")
                        new_score *= 1.5

                    #we also need to take account of whether a player elsewhere may
                    #profit indirectly - eg, a farm that hasn't been modified but
                    #now includes an extra/completed city

                    self.debug.write("\t\tfinal score %d\n" % new_score)
                    #increase the general score for this tile placement
                    placement_score += new_score

                #if it is a new feature (that we can take control of)
                elif feature.can_own():
                    self.debug.write("\t\tcontrollable feature\n")
                    if avatars:
                        score = feature.score()
                        self.debug.write("\t\tinitial score %s\n" % score)

                        #if avatars are scarce, penalty against starting new
                        if self.interface.turns_left() > avatars:
                            score -= 1
                            self.debug.write("\t\tfinite avatars penalty\n")
                            #further penalise farms which lock up avatars till the end
                            if feature.name == "Farm":
                                self.debug.write("\t\tfarm penalty\n")
                                score -= 1

                        #little bonus reflecting completion bonus for cities
                        if feature.name == "City":
                            score += 1

                        #here a more complex AI needs to consider the probability
                        #of finishing the feature based on the available tiles,
                        #turns left and local topology of the world

                        if score > placement_feature_score:
                            placement_feature_score = score
                            placement_feature = feature.segments[0]

                    else:
                        self.debug.write("\t\tno avatars to exploit\n")

            #here a more complex AI needs to consider whether this placement
            #affects topology
            #   making features uncompleteable
            #   setting up an attempt to steal a feature

            for i in (-1, 0, 1):
                for j in (-1, 0, 1):
                    if i or j:
                        if sandbox[i, j]:
                            feature0 = sandbox[i, j].segments[0].feature
                            if feature0.name == "Cloister":
                                if self.index in feature0.owners:
                                    placement_score += 1
                                elif feature0.owners:
                                    placement_score -= 1


            placement_score += placement_feature_score
            self.debug.write("\tscore for placement %s\n" % placement_score)
            if placement_score > best_score:
                best_score = placement_score
                #best_segment = placement_feature
                #best_xyr = (x, y, rotate)
                best_choice = [(placement_feature, (x, y, rotate))]
            elif placement_score == best_score:
                best_choice += [(placement_feature, (x, y, rotate))]

        best_segment, best_xyr = random.choice(best_choice)

        self.chosen_feature_segment = best_segment
        self.debug.write("best score %s, segment %s, xyr %s\n\n\n" % \
                         (best_score, best_segment, best_xyr))
        return best_xyr


    def place_avatar(self, features):
        if self.chosen_feature_segment:
            for f in features:
                if self.chosen_feature_segment in f.segments:
                    return f
        return None

