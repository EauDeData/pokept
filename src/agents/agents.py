from poke_env.player import Player
from torch import Tensor, tensor

def _get_env_state(battle):
    # Get active Pokémon and opponent's active Pokémon
    our_active_pokemon = battle.active_pokemon
    opponent_active_pokemon = battle.opponent_active_pokemon
    # Get status conditions of Pokémon (e.g., poisoned, paralyzed)
    our_status = our_active_pokemon.status.value if our_active_pokemon.status else None
    opponent_status = opponent_active_pokemon.status.value if opponent_active_pokemon.status else None

    return (f"OUR STATE:"
        f" Our Pokémon {our_active_pokemon._species}, with base stats"
        f" ({our_active_pokemon.base_stats}), "
        f"currently has {round(100 * our_active_pokemon.current_hp / our_active_pokemon.max_hp, 1)}% HP."
        f" They have the status {our_status}."
        f" We have the ability {our_active_pokemon._ability} and we are type {our_active_pokemon._type_1}"
        f" and {our_active_pokemon._type_2} with the following boosts:"
        f"\n{our_active_pokemon._boosts}"
        f"\nOPPONENT: The opponent is {opponent_active_pokemon._species}, with base stats"
        f" ({opponent_active_pokemon.base_stats})."
        f" The opponent currently has {round(100 * opponent_active_pokemon.current_hp / opponent_active_pokemon.max_hp, 1)}% HP."
        f" They have the status {opponent_status}."
        f" The opponent might have the abilities {opponent_active_pokemon._possible_abilities}"
            f" and is type {opponent_active_pokemon._type_1}"
        f" and {opponent_active_pokemon._type_2} with the following boosts:"
        f"\n{opponent_active_pokemon._boosts}"
        f"\nFIELD: Whether is {battle._weather} with field {battle._fields}. "
            f"Our field has conditions {battle._side_conditions} and opponent's has conditions"
            f" {battle._opponent_side_conditions}")

class MaxDamagePlayer(Player):
    def choose_move(self, battle):
        # If the player can attack, it will
        # print(_get_env_state(battle))
        if battle.available_moves:
            # Finds the best move among available ones
            best_move = max(battle.available_moves, key=lambda move: move.base_power)
            return self.create_order(best_move)

        # If no attack is available, a random switch will be made
        else:
            return self.choose_random_move(battle)

class RLAgent(Player):

    def _log_pytorch_decoder_model(self, model, criterion, optimizer):
        # This pytorch agent will receive the available list of moves
        # And will return the probability of selecting each move
        self.rlagent_pytorch = model
        self.loss_fn = criterion
        self.rlagent_optimizer = optimizer

    @staticmethod
    def _get_action_state(battle):
        # Logs as strings the available
        # Actions given a battle
        return {
            'moves': battle.available_moves,
            'switches': battle.available_switches
        }

    @staticmethod
    def _calculate_rewards(battle) -> Tensor:
        # Given the current action space, calculate the reward of each one of them
        # Compute the damage dealt by us and the opponent
        our_damage = battle.team.opponent.active_pokemon.last_damage
        opponent_damage = battle.opponent_team.active_pokemon.last_damage

        # Compute the reward as the difference between the damages
        reward = our_damage - opponent_damage

        return reward

    @staticmethod
    def _actions_to_tensor(actions: dict) -> Tensor:
        # Returns a tensor of shape (1, NUM_ACTIONS)
        # Therefore we will need an action tokenizer
        pass

    @staticmethod
    def _idx_to_action(idx, actions):
        if idx >= len(actions['moves']):
            return actions['switches'][idx - len(actions['moves'])]
        return actions['moves'][idx]

    def choose_move(self, battle):
        # choose action given the occasion
        actions = self._get_action_state(battle)
        action_state = self._actions_to_tensor(actions)

        battle_state = _get_env_state(battle)  # This should contain the current state of the battle
        # Then we should pass the network the battle state and the possible actions
        # And select the action with max likelihood
        # This will be indicated with an idx (argmax) that will go
        # through idx_to_action(actions) and will select the most likely action

if __name__ == '__main__':
    import asyncio
    import time

    from poke_env.player import Player, RandomPlayer


    async def main():
        start = time.time()

        # We create two players.
        random_player = RandomPlayer(
            battle_format="gen8randombattle",
        )
        max_damage_player = MaxDamagePlayer(
            battle_format="gen8randombattle",
        )

        # Now, let's evaluate our player
        await max_damage_player.battle_against(random_player, n_battles=100)

        print(
            "Max damage player won %d / 100 battles [this took %f seconds]"
            % (
                max_damage_player.n_won_battles, time.time() - start
            )
        )
        return True


    print(asyncio.get_event_loop().run_until_complete(main()))

