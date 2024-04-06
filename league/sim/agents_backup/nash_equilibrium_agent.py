
from poke_env.environment.move_category import MoveCategory
from poke_env.environment.status import Status
from poke_env.player import Player
import numpy as np
import random
from poke_env.environment.pokemon import Pokemon
from poke_env.environment.move import Move

def _calculate_stat_term(base, ivs, evs, level, nature):
    # src: https://bulbapedia.bulbagarden.net/wiki/Stat#Stat
    stat = (2 * base + ivs + (evs / 4)) * level
    stat /= 100
    stat += 5
    stat *= nature
    return stat


def _calculate_hp_term(base, ivs, evs, level):
    stat = (2 * base + ivs + (evs / 4)) * level
    stat /= 100
    stat += level + 10
    return stat


def calculate_stat(pokemon: Pokemon, stat):
    '''
    Calculates the minimum and maximum state a pokemon can get.

    '''
    min_iv, max_iv = 0, 31
    min_ev, max_ev = 0, 256
    good_nature, bad_nature = 1.1, 0.9

    if stat == 'hp':
        min_hp_term = _calculate_hp_term(pokemon.base_stats[stat], min_iv, min_ev, pokemon.level)
        max_hp_term = _calculate_hp_term(pokemon.base_stats[stat], max_iv, max_ev, pokemon.level)
        return min_hp_term, max_hp_term

    else:

        lower_bound = _calculate_stat_term(pokemon.base_stats[stat], min_iv, min_ev, pokemon.level, bad_nature)
        upper_bound = _calculate_stat_term(pokemon.base_stats[stat], max_iv, max_ev, pokemon.level, good_nature)

        return lower_bound, upper_bound


def get_multipliers_bonus(pkmn_dealer: Pokemon, pkmn_receiver: Pokemon, move: Move):
    '''

    Calculates minimum bonus, EXPECTED (for crits) and maximum
    '''
    # FIXME: Ignores weather

    crit_ratio_lookup = {0: 0,
                         1: 0.0417,
                         2: 0.125,
                         3: 0.5}
    min_damage_multiplier = 0.8
    critical_damage_chance = crit_ratio_lookup.get(move.crit_ratio, 1)
    stab_multiplier = 1.5 if move.type in (pkmn_dealer.type_1, pkmn_dealer.type_2) else 1  # Doesnt count adaptability!
    type_multiplier = pkmn_receiver.damage_multiplier(move.type)
    burn_reducer = .5 if move.defensive_category == MoveCategory.PHYSICAL and pkmn_dealer.status in [Status.BRN] else 1

    minimum_bonus = min_damage_multiplier * stab_multiplier * type_multiplier * burn_reducer

    pre_critic_expected = (((1 - 0.8) / 2) * stab_multiplier * type_multiplier * burn_reducer * 1.5)
    expected_bonus = pre_critic_expected * critical_damage_chance + (1 - critical_damage_chance) * pre_critic_expected

    max_bonus = stab_multiplier * type_multiplier * burn_reducer
    max_bonus_with_crit = max_bonus * 1.5

    return minimum_bonus, expected_bonus, max_bonus, max_bonus_with_crit


def basic_calculate_damage_dealt(pkmn_dealer: Pokemon, pkmn_receiver: Pokemon, move: Move):
    '''

    Calculates damage (min, expected, max) ignoring complex stuff like additional effects
    of whatever shit we might encounter.

    Check from poke_env.player.baselines import SimpleHeuristicsPlayer
    For possible heuristics beyond stupid damage calculations

    '''

    attacking_level_factor = ((pkmn_dealer.level * 2) / 5) * move.base_power

    df_category, atk_category = ('def', 'atk') if move.defensive_category == MoveCategory.PHYSICAL else ('spd', 'spa')

    min_attack, max_attack = calculate_stat(pkmn_dealer, atk_category)
    min_def, max_def = calculate_stat(pkmn_receiver, df_category)

    min_attack, max_attack = (min_attack + (0.5 * min_attack) * pkmn_dealer._boosts[atk_category],
                              max_attack + (0.5 * max_attack) * pkmn_dealer._boosts[atk_category])

    min_def, max_def = (min_def + (0.5 * min_def) * pkmn_receiver._boosts[df_category],
                        max_def + (0.5 * max_def) * pkmn_receiver._boosts[df_category])

    # print(min_def, max_def, pkmn_receiver._boosts[df_category], pkmn_receiver)
    min_power_factor, max_power_factor = ((attacking_level_factor * (min_attack / max_def)) / 50,
                                          (attacking_level_factor * (max_attack / min_def)) / 50)

    min_power_factor += 2
    max_power_factor += 2

    minimum_bonus, expected_bonus, max_bonus, max_bonus_with_crit = get_multipliers_bonus(pkmn_dealer, pkmn_receiver,
                                                                                          move)

    return {
        'min_pkmn': {
            'min_luck': min_power_factor * minimum_bonus,
            'expected_luck': min_power_factor * expected_bonus * move.accuracy,
            'max_luck': min_power_factor * max_bonus,
            'max_luck_plus_crit': min_power_factor * max_bonus_with_crit
        },
        'max_pkmn': {'min_luck': max_power_factor * minimum_bonus,
                     'expected_luck': max_power_factor * expected_bonus * move.accuracy,
                     'max_luck': max_power_factor * max_bonus,
                     'max_luck_plus_crit': max_power_factor * max_bonus_with_crit
                     }
    }

class OneStepNashEquilibrium(Player):
    # FIXME: Make it work
    # There is some bug here when selecting the strategy or calculating the damage

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
