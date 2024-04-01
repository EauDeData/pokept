from typing import Dict
from importlib import import_module
import asyncio
import time

# Here we will take agents from the agents/ folder and make them battle automatically
# To determine which is the best agent
# Users might upload agents there
# In the database we will have {agent_name: class_name, file_name: file_name}

async def simulate_gen8_random_battle(player_1: Dict, player_2: Dict, nbattles=100):

    # TODO: Make it safer
    # Dynamically import player classes
    player1_module = import_module(f".agents.{player_1['file_name']}", package=__package__)
    player_one_constructor = getattr(player1_module, player_1['agent_name'])

    player2_module = import_module(f".agents.{player_2['file_name']}", package=__package__)
    player_two_constructor = getattr(player2_module, player_2['agent_name'])

    # Initialize players
    player1 = player_one_constructor(battle_format="gen8randombattle")
    player2 = player_two_constructor(battle_format="gen8randombattle")

    # Simulate battles
    await player1.battle_against(player2, n_battles=nbattles)

    return player1.n_won_battles, nbattles - player1.n_won_battles

