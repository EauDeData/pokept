from poke_env.player import Player
from torch import Tensor, tensor
from calculator import basic_calculate_damage_dealt, calculate_stat
from itertools import product
import numpy as np
import nashpy as nash
import random
from poke_env.environment.pokemon import Pokemon
from poke_env.environment.move import Move

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


class OneStepNashEquilibrium(Player):
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
        total_damage = .5 * damage_info['max_pkmn']['expected_luck'] + .5 * damage_info['min_pkmn']['expected_luck']
        damage_percentage = total_damage / (sum(calculate_stat(receiver, 'hp'))*.5)

        return damage_percentage

    def simulate_move(self, our_move, their_move, battle):

        # Fixme: This is not considering speed!!!
        our_fainted_count, opponent_fainted_count = self.state_of_battle(battle)
        active_pokemon = battle.active_pokemon
        opponent_pokemon = battle.opponent_active_pokemon

        if our_move[0] == 'switch':
            active_pokemon = our_move[1]
        if their_move[0] == 'switch':
            opponent_pokemon = their_move[1]

        if our_move[0] == 'attack':
            opponent_fainted_count = opponent_fainted_count + self.calculate_damage_percentage(active_pokemon,
                                                                                               opponent_pokemon,
                                                                                               our_move[1])
        if their_move[0] == 'attack':
            our_fainted_count = our_fainted_count + self.calculate_damage_percentage(opponent_pokemon,
                                                                                     active_pokemon,
                                                                                     their_move[1])
        return our_fainted_count, opponent_fainted_count
    @staticmethod
    def find_nash_equilibrium(payoff_matrix_our, payoff_matrix_opponent):
        num_rows = len(payoff_matrix_our)
        num_cols = len(payoff_matrix_our[0])

        for i in range(num_rows):
            for j in range(num_cols):
                our_payoff = payoff_matrix_our[i][j]
                opponent_payoff = payoff_matrix_opponent[i][j]

                # Check if no player can unilaterally improve payoff
                if all(payoff_matrix_our[x][j] <= our_payoff for x in range(num_rows)) \
                        and all(payoff_matrix_opponent[i][y] <= opponent_payoff for y in range(num_cols)):
                    return i, j
    def nash_grid_search(self, battle):
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

        # Initialize the payoff matrices
        num_our_moves = len(our_availible_moves)
        num_opponent_moves = len(opponent_availible_moves)
        payoff_matrix_our = np.zeros((num_our_moves, num_opponent_moves))
        payoff_matrix_opponent = np.zeros((num_our_moves, num_opponent_moves))

        # Populate the payoff matrices
        for i, our_move in enumerate(our_availible_moves):
            for j, opponent_move in enumerate(opponent_availible_moves):
                try:
                    our_fainted_count, opponent_fainted_count = self.simulate_move(our_move, opponent_move, battle)
                except ZeroDivisionError:
                    #FIXME: Sometimes they have 0 max defense and its like wtf
                    print('Some pokemon stats are kind of corrupted or something')
                    return random.choice(our_availible_moves)

                # Calculate the income (our cost) and cost (opponent's cost)
                income = opponent_fainted_count
                cost = our_fainted_count

                # Store the payoffs in the matrices
                payoff_matrix_our[i, j] = cost
                payoff_matrix_opponent[i, j] = income

        # Find by dominated strategies
        our_selected_move = self.find_nash_equilibrium(payoff_matrix_our, payoff_matrix_opponent)

        if our_selected_move is None:
            print('Warning: Nash is crashing!')
            return random.choice(our_availible_moves)
        else:
            return our_availible_moves[our_selected_move[0]]



    def choose_move(self, battle):
        decision = self.nash_grid_search(battle)
        return self.create_order(decision[1])


if __name__ == '__main__':
    import asyncio
    import time

    from poke_env.player import Player, RandomPlayer


    async def main():
        start = time.time()

        # We create two players.
        random_player = OneStepNashEquilibrium(
            battle_format="gen8randombattle",
        )
        max_damage_player = EffectivenessOffensive(
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
