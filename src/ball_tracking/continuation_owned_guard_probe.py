"""Bounded actual Windows supervision probe; standard library only, no model."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
from .continuation_owned_guard import verify_owned_worker,live_membership

MODULE = 'src.ball_tracking.continuation_owned_guard_probe'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',action='store_true',required=True)
    parser.add_argument('--monitor',required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    monitor=root/args.monitor
    result=verify_owned_worker(root,monitor,MODULE,sys.argv[1:])
    rejected=[]
    for label,module,arguments in [('wrong_module',MODULE+'_wrong',sys.argv[1:]),
        ('wrong_arguments',MODULE,[*sys.argv[1:],'--unexpected'])]:
        try:
            verify_owned_worker(root,monitor,module,arguments)
        except ValueError:
            rejected.append(label)
        else:
            raise AssertionError(label+' was accepted')
    policy=json.loads((monitor/'policy.json').read_text())
    owned=json.loads((monitor/'owned_process.json').read_text())
    for label,launcher in [('outside_job_launcher',owned['supervisor_pid']),('skip_declared_redirector',os.getpid())]:
        if launcher == owned['pid']: continue
        try:
            live_membership(os.getpid(),launcher,owned['supervisor_pid'],
                datetime.fromisoformat(policy['created_at_utc']).timestamp(),datetime.fromisoformat(owned['started_at_utc']).timestamp())
        except ValueError:
            rejected.append(label)
        else:
            raise AssertionError(label+' was accepted')
    assert 'torch' not in sys.modules
    result.update(negative_cases_rejected=rejected,torch_imported=False,model_calls=0,
        CUDA_initialization_calls=0,source_pixel_reads=0,at_utc=datetime.now(timezone.utc).isoformat())
    path=monitor/'worker_guard_probe.json'
    with path.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    print(json.dumps(result),flush=True)


if __name__=='__main__': main()
