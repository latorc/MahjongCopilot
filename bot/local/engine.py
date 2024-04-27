""" Mortal Engine for 4p game"""
import torch
import numpy as np
from torch.distributions import Normal, Categorical
from bot.local.model import Brain, DQN

class MortalEngine:
    """ Mortal Engine for local Bot 4p"""
    def __init__(
        self,
        brain,
        dqn,
        is_oracle,
        version,
        device = None,
        stochastic_latent = False,
        enable_amp = False,
        enable_quick_eval = True,
        enable_rule_based_agari_guard = False,
        name = 'NoName',
        boltzmann_epsilon = 0,
        boltzmann_temp = 1,
        top_p = 1,
    ):
        self.engine_type = 'mortal'
        self.device = device or torch.device('cpu')
        assert isinstance(self.device, torch.device)
        self.brain = brain.to(self.device).eval()
        self.dqn = dqn.to(self.device).eval()
        self.is_oracle = is_oracle
        self.version = version
        self.stochastic_latent = stochastic_latent

        self.enable_amp = enable_amp
        self.enable_quick_eval = enable_quick_eval
        self.enable_rule_based_agari_guard = enable_rule_based_agari_guard
        self.name = name

        self.boltzmann_epsilon = boltzmann_epsilon
        self.boltzmann_temp = boltzmann_temp
        self.top_p = top_p

    def react_batch(self, obs, masks, invisible_obs):
        with (
            torch.autocast(self.device.type, enabled=self.enable_amp),
            torch.no_grad(),
        ):
            return self._react_batch(obs, masks, invisible_obs)

    def _react_batch(self, obs, masks, invisible_obs):
        obs = torch.as_tensor(np.stack(obs, axis=0), device=self.device)
        masks = torch.as_tensor(np.stack(masks, axis=0), device=self.device)
        invisible_obs = None
        if self.is_oracle:
            invisible_obs = torch.as_tensor(np.stack(invisible_obs, axis=0), device=self.device)
        batch_size = obs.shape[0]

        match self.version:
            case 1:
                mu, logsig = self.brain(obs, invisible_obs)
                if self.stochastic_latent:
                    latent = Normal(mu, logsig.exp() + 1e-6).sample()
                else:
                    latent = mu
                q_out = self.dqn(latent, masks)
            case 2 | 3 | 4:
                phi = self.brain(obs)
                q_out = self.dqn(phi, masks)

        if self.boltzmann_epsilon > 0:
            is_greedy = torch.full((batch_size,), 1-self.boltzmann_epsilon, device=self.device).bernoulli().to(torch.bool)
            logits = (q_out / self.boltzmann_temp).masked_fill(~masks, -torch.inf)
            sampled = sample_top_p(logits, self.top_p)
            actions = torch.where(is_greedy, q_out.argmax(-1), sampled)
        else:
            is_greedy = torch.ones(batch_size, dtype=torch.bool, device=self.device)
            actions = q_out.argmax(-1)

        return actions.tolist(), q_out.tolist(), masks.tolist(), is_greedy.tolist()

def sample_top_p(logits, p):
    if p >= 1:
        return Categorical(logits=logits).sample()
    if p <= 0:
        return logits.argmax(-1)
    probs = logits.softmax(-1)
    probs_sort, probs_idx = probs.sort(-1, descending=True)
    probs_sum = probs_sort.cumsum(-1)
    mask = probs_sum - probs_sort > p
    probs_sort[mask] = 0.
    sampled = probs_idx.gather(-1, probs_sort.multinomial(1)).squeeze(-1)
    return sampled

def get_engine(model_file:str) -> MortalEngine:
    """ Create and return Mortal engine object
    params:
        model_file(str): Mortal model file path"""
    # check if GPU is available
    if torch.cuda.is_available():
        device = torch.device('cuda')
    else:
        device = torch.device('cpu')

    # Get the path of control_state_file = current directory / control_state_file
    state = torch.load(model_file, map_location=device)

    mortal = Brain(version=state['config']['control']['version'],
        conv_channels=state['config']['resnet']['conv_channels'],
        num_blocks=state['config']['resnet']['num_blocks']).eval()
    dqn = DQN(version=state['config']['control']['version']).eval()
    mortal.load_state_dict(state['mortal'])
    dqn.load_state_dict(state['current_dqn'])

    engine = MortalEngine(
        mortal,
        dqn,
        is_oracle = False,
        device = device,
        enable_amp = False,
        enable_quick_eval = False,
        enable_rule_based_agari_guard = False,
        name = 'mortal',
        version = state['config']['control']['version'],
    )

    return engine