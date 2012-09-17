from game import Game, AI_REGISTRY
import random
try:
    import curses
except ImportError:
    try:
        import _minimal_curses as curses
    except:
        pass
import argparse
import re

class AIAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        result = []
        for value in values:
            match = re.match(r"(\w+)\*(\d+)", value)
            if match:
                if match.group(1) in AI_REGISTRY:
                    result += [match.group(1) for i in range(int(match.group(2)))]
                else:
                    raise argparse.ArgumentError(self, "invalid AI: %s (choose from %s)" % (match.group(1), AI_REGISTRY.keys()))
            else:
                if value in AI_REGISTRY:
                    result += [value]
                else:
                    raise argparse.ArgumentError(self, "invalid AI: %s (choose from %s)" % (value, AI_REGISTRY.keys()))
        setattr(namespace, self.dest, result)

def arg_bool(s):
    if s.lower() in ('1', 'y', 'yes', 'true'):
        return True
    return False

parser = argparse.ArgumentParser()
parser.add_argument("--silent", default=False, action="store_true",
                    help="Disable ncurses output.")
parser.add_argument("--seed", default=None, type=int,
                    help="Random number generator seed.")
for k, v in Game.default_options.items():
    if type(v) == bool:
        parser.add_argument("--"+k, type=arg_bool, default=v,
                            help=Game.option_help[k]+' (default: %(default)s)',
                            metavar="y/n")
    else:
        parser.add_argument("--"+k, type=type(v), default=v,
                            help=Game.option_help[k]+' (default: %(default)s)',
                            metavar=type(v).__name__)
parser.add_argument("players", metavar="PLAYERS", action=AIAction, nargs="+",
                    help="List of class names for human/AI players. (choices: %s)" %\
                         ', '.join(AI_REGISTRY.keys()))

args = parser.parse_args()
random.seed(args.seed)
g = Game(args.players, **args.__dict__)
if args.silent:
    print(g.play())
else:
    curses.wrapper(g.play)

