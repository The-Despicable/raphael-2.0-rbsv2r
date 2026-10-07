"""grpo_proto.py — contained GRPO-mechanics prototype (RSI-1 Track C).

This is a REAL optimization loop implementing the GRPO algorithm's mechanics
from DeepSeekMath §4.1.1 (Eq. 2-4) on a deliberately tiny policy network —
NOT language-model training and NOT a RAPHAEL capability:

- policy: small MLP over a benign abstract state (no tools, no targets);
- group sampling: G trajectories per prompt-state from the current policy;
- rewards: deterministic simulator score (objective task, no self-report);
- advantage: group-relative normalization  A_i = (r_i - mean) / (std + eps)
  (paper §4.1.2 outcome-supervision form);
- objective: clipped PPO-style surrogate (paper Eq. 3) plus KL penalty
  against a frozen reference copy of the initial policy;
- optimizer: Adam on the policy parameters (the value-critic-free property
  of GRPO is exactly why this fits a tiny CPU budget).

Environment honesty: the simulated task is fixed and public (choose the
action whose latent score is highest under a noisy observation). Learning
here demonstrates the mechanics work and improve a policy's reward on the
training task; it demonstrates nothing about RAPHAEL's offensive performance.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any

import torch
import torch.nn as nn

K_ACTIONS = 4
STATE_DIM = 8
HIDDEN = 32
GROUP_SIZE = 8          # G outputs per prompt-state (paper used 64 for LLMs)
LR = 3e-3
KL_COEF = 0.04          # paper's beta (kept for fidelity; toy task is robust to it)
CLIP_EPS = 0.2
EPISODES = 300
SEED = 20261007


def make_env(seed: int):
    """Benign simulator: each state embeds a noisy observation of per-action
    latent scores; reward = score of the chosen action (objective, external)."""
    g = torch.Generator().manual_seed(seed)
    latent = torch.randn(K_ACTIONS, generator=g)

    def sample_state():
        obs = latent + 0.3 * torch.randn(K_ACTIONS, generator=g)
        state = torch.zeros(STATE_DIM)
        state[:K_ACTIONS] = obs
        return state

    def reward(state, action: int) -> float:
        return float(latent[action])

    return sample_state, reward


class PolicyMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(STATE_DIM, HIDDEN), nn.Tanh(),
                                 nn.Linear(HIDDEN, K_ACTIONS))

    def act(self, state):
        logits = self.net(state)
        dist = torch.distributions.Categorical(logits=logits)
        return dist


def run_prototype(out_dir: Path) -> Dict[str, Any]:
    torch.manual_seed(SEED)
    sample_state, reward_fn = make_env(SEED)
    policy = PolicyMLP()
    reference = PolicyMLP()
    reference.load_state_dict(policy.state_dict())   # frozen KL anchor
    for p in reference.parameters():
        p.requires_grad_(False)
    opt = torch.optim.Adam(policy.parameters(), lr=LR)

    history = []
    t0 = time.time()
    for ep in range(EPISODES):
        state = sample_state()
        with torch.no_grad():
            dist = policy.act(state)
            actions = dist.sample((GROUP_SIZE,))            # G group samples
        rewards = torch.tensor([reward_fn(state, int(a)) for a in actions])

        # group-relative advantage (outcome supervision, paper §4.1.2)
        adv = (rewards - rewards.mean()) / (rewards.std() + 1e-6)

        dist = policy.act(state)
        logp = dist.log_prob(actions)
        with torch.no_grad():
            ref_logp = reference.act(state).log_prob(actions)
        ratio = torch.exp(logp - logp.detach())
        clipped = torch.clamp(ratio, 1 - CLIP_EPS, 1 + CLIP_EPS)
        policy_loss = -torch.min(ratio * adv, clipped * adv).mean()
        kl = (torch.distributions.kl.kl_divergence(
            policy.act(state), reference.act(state))).mean()
        loss = policy_loss + KL_COEF * kl

        opt.zero_grad()
        loss.backward()
        opt.step()

        if ep % 25 == 0 or ep == EPISODES - 1:
            with torch.no_grad():
                mean_r = float(rewards.mean())
                best_r = float(rewards.max())
                p_best = float(dist.probs.argmax() == torch.tensor(
                    [reward_fn(state, k) for k in range(K_ACTIONS)]).argmax())
            history.append({"episode": ep, "mean_reward": round(mean_r, 4),
                            "best_reward": round(best_r, 4),
                            "picks_optimal": p_best})

    # deterministic final evaluation (greedy, 200 fresh states)
    with torch.no_grad():
        eval_rewards = []
        for _ in range(200):
            s = sample_state()
            eval_rewards.append(reward_fn(s, int(policy.act(s).probs.argmax())))
        init_rewards = []
        for _ in range(200):
            s = sample_state()
            init_rewards.append(reward_fn(s, int(reference.act(s).probs.argmax())))
    result = {
        "prototype": "GRPO-mechanics on a contained toy policy (torch, CPU)",
        "seed": SEED, "group_size": GROUP_SIZE, "episodes": EPISODES,
        "kl_coef": KL_COEF, "clip_eps": CLIP_EPS, "lr": LR,
        "initial_greedy_mean_reward": round(sum(init_rewards) / len(init_rewards), 4),
        "trained_greedy_mean_reward": round(sum(eval_rewards) / len(eval_rewards), 4),
        "history": history,
        "wall_seconds": round(time.time() - t0, 2),
        "honesty_labels": [
            "real parameter updates on a real policy network (Adam)",
            "group-relative advantages + clipped surrogate + KL-to-reference implemented per DeepSeekMath §4.1.1-4.1.2",
            "NOT language-model training; no RAPHAEL capability, target, or policy file is affected",
            "toy-task improvement only; no transfer claim",
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "grpo_prototype_result.json").write_text(json.dumps(result, indent=1))
    return result
