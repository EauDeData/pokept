from poke_env.environment.pokemon import Pokemon
from poke_env.environment.move import Move
from poke_env.environment.move_category import MoveCategory
from poke_env.environment.status import Status
from poke_env.environment.battle import Battle
from poke_env.player.baselines import SimpleHeuristicsPlayer
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
