from poke_env.player import Player
class PacifistDamagePlayer(Player):
    def choose_move(self, battle):
        # If the player can attack, it will
        # print(_get_env_state(battle))
        if battle.available_moves:
            # Finds the best move among available ones
            best_move = min(battle.available_moves, key=lambda move: move.base_power)
            return self.create_order(best_move)

        # If no attack is available, a random switch will be made
        else:
            return self.choose_random_move(battle)