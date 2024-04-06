from poke_env.player import Player
from torch import Tensor, tensor
from .agents import _get_env_state

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
