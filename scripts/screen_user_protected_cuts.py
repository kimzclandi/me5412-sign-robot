#!/usr/bin/env python3
"""Save real-geometry automatic endpoint screening for a frozen pair selection."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sign_robot.pair_contract import atomic_json, load_policy, run_identity
from sign_robot.pair_routes import PairWorkBudget, build_pair_context_v2, valid_endpoint_choices_v2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--pair',action='append',required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; keep historical evidence and choose a new path')
    policy = load_policy(args.policy,supported_versions=(1,2))
    context = build_pair_context_v2(ROOT,policy)
    if context.input_blockers:
        raise ValueError(context.input_blockers)
    pairs = {}
    for pair in args.pair:
        source,target = pair.split('__')
        budget = PairWorkBudget(policy)
        pairs[pair] = {'selection':valid_endpoint_choices_v2(context,source,target,budget),'budget':budget.snapshot()}
    result = {'identity':run_identity(context.library,policy),'window_provenance':'algorithm','pairs':pairs}
    atomic_json(args.output,result)
    print(json.dumps({'output':str(args.output),'pairs':{
        p:{role:len(x['selection'][role]['valid_frames']) for role in ('source','target')}
        for p,x in pairs.items()}}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
