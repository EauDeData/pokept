from poke_env.player import Player
from torch import Tensor, tensor
from calculator import basic_calculate_damage_dealt, calculate_stat
from itertools import product
import numpy as np
import nashpy as nash
import random
from poke_env.environment.pokemon import Pokemon
from poke_env.environment.move import Move
import pandas as pd


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


class MaxDamagePlayer2(Player):
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


class EffectivenessOffensive(Player):
    def choose_move(self, battle):
        # If the player can attack, it will

        if battle.available_moves:
            # Finds the best move among available ones
            best_move = max(battle.available_moves,
                            key=lambda move: move.base_power * battle.opponent_active_pokemon.damage_multiplier(
                                move.type))
            return self.create_order(best_move)

        # If no attack is available, a random switch will be made
        else:
            return self.choose_random_move(battle)


class SingleStageMinMax(Player):
    # FIXME: It is bullshit, i think the damage approximations are not working
    prev_state = None

    # Assume single step nash equilibrium
    # In the future we should do the tree
    def state_of_battle(self, battle):

        our_fainted_count = sum(
            1 for mon in battle.team.values() if mon.fainted
        )
        opponent_fainted_count = sum(
            1 for mon in battle.opponent_team.values() if mon.fainted
        )

        our_fainted_count += 1 - battle.active_pokemon.current_hp_fraction
        opponent_fainted_count += 1 - battle.opponent_active_pokemon.current_hp_fraction
        if self.prev_state is None:
            self.prev_state = (our_fainted_count, opponent_fainted_count)
        else:
            prev_our_fainted, prev_opponent_fainted = self.prev_state
            if our_fainted_count - prev_our_fainted >= 2:
                our_fainted_count -= 1  # When a pokemon faints its duplicated somehow
                # FIXME: This wouldnt not apply "as is" to double battles

            if opponent_fainted_count - prev_opponent_fainted >= 2:
                opponent_fainted_count -= 1  # When a pokemon faints its duplicated somehow

        self.prev_state = (our_fainted_count, opponent_fainted_count)
        return our_fainted_count, opponent_fainted_count
    def calculate_damage_percentage(self, dealer, receiver, move):

        damage_info = basic_calculate_damage_dealt(dealer, receiver, move)
        # Delulu strategy: Assumes fairness
        total_damage = .5 * damage_info['max_pkmn']['expected_luck'] + .5 * damage_info['max_pkmn']['expected_luck']
        damage_percentage = total_damage / (sum(calculate_stat(receiver, 'hp')) * .5)

        return damage_percentage

    def simulate_move(self, our_move, their_move, battle):

        # Fixme: This is not considering speed!!!
        # Fixme: Use state of battle + calculate_damage_percentage
        active_pokemon = battle.active_pokemon
        opponent_pokemon = battle.opponent_active_pokemon

        if our_move[0] == 'switch':
            active_pokemon = our_move[1]
            opponent_fainted_count = 0

        if their_move[0] == 'switch':
            opponent_pokemon = their_move[1]
            our_fainted_count = 0

        if our_move[0] == 'attack':
            opponent_fainted_count = self.calculate_damage_percentage(active_pokemon, opponent_pokemon, our_move[1])
        if their_move[0] == 'attack':
            our_fainted_count = self.calculate_damage_percentage(opponent_pokemon, active_pokemon, their_move[1])

        return opponent_fainted_count, our_fainted_count

    def minmax_search(self, battle):
        # A move can be a switch ("switch", switch_object)
        # Or an attack ('attack', attack_move)
        our_availible_moves = ([('attack', atck) for atck in battle.available_moves] +
                               [('switch', stch) for stch in battle.available_switches])

        opponent_availible_moves = ([('attack', Move(atck, gen=battle.opponent_active_pokemon._data.gen))
                                     for atck in battle.opponent_active_pokemon.moves] +
                                    [('switch', stch) for stch in battle.opponent_team.values()
                                     if not stch.active and not stch.fainted])

        if not len(opponent_availible_moves):
            return random.choice(our_availible_moves)

        max_our_payoff = float('-inf')
        best_move_indices = []
        for i, our_move in enumerate(our_availible_moves):
            for j, opponent_move in enumerate(opponent_availible_moves):
                our_payoff, their_payoff = self.simulate_move(our_move, opponent_move, battle)
                our_payoff -= their_payoff
                # Update max_our_payoff and best_move_indices if our payoff is higher
                if our_payoff > max_our_payoff:
                    max_our_payoff = our_payoff
                    best_move_indices = [(i, j)]


        # Choose a move randomly among the best moves
        chosen_move_index = random.choice(best_move_indices +
                                          [(random.randint(0, len(our_availible_moves) - 1), None)])
        chosen_our_move = our_availible_moves[chosen_move_index[0]]

        return chosen_our_move
    def choose_move(self, battle):
        decision = self.minmax_search(battle)
        return self.create_order(decision[1])


if __name__ == '__main__':
    import asyncio
    import time

    from poke_env.player import Player, RandomPlayer
    from poke_env.player.baselines import SimpleHeuristicsPlayer

    async def main():
        start = time.time()

        # We create two players.
        random_player = SingleStageMinMax(
            battle_format="gen8randombattle",
        )
        max_damage_player = SimpleHeuristicsPlayer(
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
