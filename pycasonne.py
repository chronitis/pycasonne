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
parser.add_argument("players", metavar="PLAYER", nargs="+",
                    choices=AI_REGISTRY.keys(),
                    help="List of class names for human/AI players. (choices: %s)" %\
                         ', '.join(AI_REGISTRY.keys()))

args = parser.parse_args()
random.seed(args.seed)
g = Game(args.players, **args.__dict__)
if args.silent:
    print (g.play())
else:
    curses.wrapper(g.play)

