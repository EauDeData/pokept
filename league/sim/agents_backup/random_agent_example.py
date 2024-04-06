from poke_env.player import RandomPlayer as RP

# Just importing the random player here so we can use it the same way a user uploaded it.
class RandomPlayer(RP):
    def __init__(self, *args, **kwargs):
        super(RandomPlayer, self).__init__(*args, **kwargs)