"""Read-only neural contract probe. Passing this is NOT a physical save test."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import torch

EXPECTED_SHA = '7ecdedff5de6e30a0a4d11742561a9be6c94d8faeefc4701f3e8788381b67b14'


def probe(reference):
    checkpoint = reference/'src/assets/soccer/weight/goalkeeper.pt'
    source = reference/'src/tasks/soccer/modules/gk_actor_critic.py'
    inputs = [checkpoint, source]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    if before[checkpoint] != EXPECTED_SHA:
        raise ValueError('Unverified external checkpoint; no load attempted')
    state = torch.load(checkpoint, map_location='cpu', weights_only=True)['model_state_dict']
    spec = importlib.util.spec_from_file_location('reference_goalkeeper_audit', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    obs = SimpleNamespace(spaces={'actor': SimpleNamespace(shape=(960,)),
                                 'critic': SimpleNamespace(shape=(113,))})
    with contextlib.redirect_stdout(io.StringIO()):
        actor = module.GoalkeeperActorCritic(obs, None, None)
    result = actor.load_state_dict(state, strict=True)
    actor.eval()
    chunks = [torch.arange(10*n).reshape(1, 10, n) for n in actor._TERM_SIZES]
    term_major = torch.cat([c.reshape(1, -1) for c in chunks], dim=-1).float()
    expected = torch.cat(chunks, dim=-1).reshape(1, 960).float()
    with torch.inference_mode():
        action = actor.act_inference(torch.zeros((1, 960)))
        again = actor.act_inference(torch.zeros((1, 960)))
        visible = torch.zeros((1, 960))
        critic_a = actor({'actor': visible, 'critic': torch.zeros((1, 113))})
        critic_b = actor({'actor': visible, 'critic': torch.full((1, 113), 12345.0)})
    checks = dict(strict_keys=not result.missing_keys and not result.unexpected_keys,
        finite_29_actions=tuple(action.shape) == (1, 29) and bool(torch.isfinite(action).all()),
        history_reorder_exact=bool(torch.equal(actor._reorder_obs_history(term_major), expected)),
        deterministic_same_input=bool(torch.equal(action, again)),
        critic_changes_do_not_change_action=bool(torch.equal(critic_a, critic_b)),
        no_recurrent_state=not actor.is_recurrent,
        external_inputs_unchanged=all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p, h in before.items()))
    return dict(checks=checks, checkpoint_sha256=before[checkpoint], source_sha256=before[source],
        torch_version=torch.__version__, physics_executed=False, visual_evaluation=False,
        interpretation='Neural compatibility only; no evidence of balance, contact or saves.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    report = probe(args.reference.resolve())
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(text)
    print(text)
    return 0 if all(report['checks'].values()) else 2


if __name__ == '__main__':
    raise SystemExit(main())
