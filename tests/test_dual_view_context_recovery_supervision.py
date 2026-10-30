"""CPU-only deadline/actual watcher-loop regression tests. No OS or GPU query."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.ball_tracking import dual_view_context_recovery_deadline as deadline

ROOT=Path(__file__).resolve().parents[1]
BASE=Path('data/outputs/ball_tracking/dual_view_context_v0_1')
START=datetime(2026,10,30,20,0,0,tzinfo=timezone.utc)


def prior():
    return dict(charged_elapsed_seconds=1788.469,event_remaining_owned_processes=0,
        supervisor_result=dict(remaining_owned_processes_before_close=0,job_cleanup_error=None))


def module(name,version='launch_v0_2'):
    spec=importlib.util.spec_from_file_location('recovery_test_'+version+'_'+name,ROOT/BASE/version/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def policy(contract):
    return dict(module='src.ball_tracking.dual_view_context_resume',created_at_utc=(START+timedelta(seconds=20)).isoformat(),
        max_total_seconds=3611,soft_stop_seconds=3581,cleanup_reserve_seconds=30,deadline_contract=contract)


class RecoveryDeadlineTests(unittest.TestCase):
    def test_exact_prior_debit_and_total_cap(self):
        contract=deadline.make_contract(prior(),START,100)
        self.assertEqual(contract['hard_deadline_monotonic'],3711)
        self.assertEqual(contract['soft_deadline_monotonic'],3681)
        self.assertEqual(contract['remaining_execution_cap_seconds']+contract['prior_charged_rounded_up_seconds'],5400)
        self.assertFalse(contract['fresh_90_minute_budget'])
        self.assertTrue(contract['CPU_only_repair_downtime_excluded'])

    def test_supervisor_created_later_cannot_reset_deadline(self):
        contract=deadline.make_contract(prior(),START,100)
        p=policy(contract)
        self.assertEqual(deadline.remaining_wall_seconds(p,START+timedelta(seconds=30),130),3581)
        self.assertEqual(deadline.remaining_wall_seconds(p,START+timedelta(seconds=3581),3681),30)

    def test_wall_clock_change_cannot_extend_deadline(self):
        contract=deadline.make_contract(prior(),START,100)
        self.assertEqual(deadline.remaining_wall_seconds(contract,START-timedelta(hours=1),3681),30)
        self.assertEqual(deadline.remaining_wall_seconds(contract,START+timedelta(seconds=3600),100),11)

    def test_stale_30minute_policy_or_inconsistent_contract_is_rejected(self):
        contract=deadline.make_contract(prior(),START,100)
        for changes in ({'max_total_seconds':1800},{'soft_stop_seconds':1770},{'max_total_seconds':5400}):
            p=policy(contract);p.update(changes)
            with self.assertRaises(ValueError):deadline.validate_contract(p)
        bad=dict(contract,hard_deadline_monotonic=5500)
        with self.assertRaises(ValueError):deadline.validate_contract(bad)

    def test_ready_handshake_rejects_old_timings_even_when_status_is_ready(self):
        contract=deadline.make_contract(prior(),START,100)
        old=dict(status='fresh_readonly_event_baseline_ready',soft_stop_seconds=1770,hard_limit_seconds=1800)
        with self.assertRaises(ValueError):deadline.validate_ready(old,contract)
        good=dict(status=old['status'],soft_stop_seconds=3581,hard_limit_seconds=3611,deadline_contract=contract)
        deadline.validate_ready(good,contract)
        good['deadline_contract']=deadline.make_contract(prior(),START+timedelta(seconds=1),101)
        with self.assertRaises(ValueError):deadline.validate_ready(good,contract)

    def test_unclean_prior_cleanup_or_changed_debit_rejected(self):
        p=prior();p['event_remaining_owned_processes']=1
        with self.assertRaises(ValueError):deadline.make_contract(p,START,100)
        p=prior();p['charged_elapsed_seconds']=1801
        with self.assertRaises(ValueError):deadline.make_contract(p,START,100)

    def test_launcher_hard_guard_uses_remaining_time_and_owned_exit(self):
        launcher=module('run_supervised')
        class Done:
            def wait(self,seconds):self.seconds=seconds;return False
        done=Done();calls=[]
        launcher.hard_deadline(done,0,calls.append)
        self.assertEqual(calls,[124]);self.assertEqual(done.seconds,0)


class ActualWatcherLoopTests(unittest.TestCase):
    def run_watcher(self,version,stop_at=None,clock_steps=(1800,)):
        watcher=module('events_watch',version)
        now=[0.0];steps=iter(clock_steps)
        class FakeDateTime(datetime):
            @classmethod
            def now(cls,tz=None):return START+timedelta(seconds=now[0])
        def sleep(seconds):now[0]+=next(steps,seconds)
        contract=deadline.make_contract(prior(),START,0)
        remaining=deadline.remaining_wall_seconds
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);base=root/BASE/version
            monitor=base/'monitoring/test';monitor.mkdir(parents=True)
            p=policy(contract)
            if version=='launch_v0_1':
                p.update(module='src.ball_tracking.dual_view_context_experiment',created_at_utc=START.isoformat(),max_total_seconds=5400,soft_stop_seconds=5370)
            (monitor/'policy.json').write_text(json.dumps(p))
            (base/'launcher_deadline.json').write_text(json.dumps(contract))
            def query(watermarks):
                if stop_at is not None and now[0]>=stop_at:
                    (monitor/'finished.json').write_text('{}')
                return [dict(log=key,latest_record_id=value,events=[]) for key,value in watermarks.items()]
            with patch.object(watcher,'owner_alive',return_value=True),\
                 patch.object(watcher,'baseline',return_value=dict(watermarks={'System':1,'Application':1},known_wer_report_ids=[])),\
                 patch.object(watcher,'query_since',side_effect=query),\
                 patch.object(watcher,'datetime',FakeDateTime),\
                 patch.object(watcher,'time',SimpleNamespace(monotonic=lambda:now[0],sleep=sleep)),\
                 patch.object(deadline,'remaining_wall_seconds',side_effect=lambda value:remaining(value,START+timedelta(seconds=now[0]),now[0])):
                code=watcher.watch(root,str(monitor.relative_to(root)),str((base/'events_test').relative_to(root)),1234)
            finished=json.loads((base/'events_test/finished.json').read_text())
            ready=json.loads((base/'events_test/ready.json').read_text())
            return code,finished,ready,(monitor/'STOP').exists(),now[0]

    def test_actual_old_watcher_reproduces_1770_stop_despite5400_policy(self):
        code,result,ready,stopped,elapsed=self.run_watcher('launch_v0_1',clock_steps=(1769,1))
        self.assertEqual(result['reason'],'fresh_game_1770_second_soft_deadline')
        self.assertEqual(elapsed,1770);self.assertEqual(code,1);self.assertTrue(stopped)
        self.assertEqual(ready['soft_stop_seconds'],1770)

    def test_actual_new_watcher_continues_beyond_old30minute_stop(self):
        code,result,ready,stopped,elapsed=self.run_watcher('launch_v0_2',stop_at=1800)
        self.assertEqual(result['status'],'supervisor_finished')
        self.assertEqual(code,0);self.assertFalse(stopped);self.assertEqual(elapsed,1800)
        self.assertEqual(ready['hard_limit_seconds'],3611)

    def test_actual_new_watcher_stops_at_shared3581_soft_deadline(self):
        code,result,ready,stopped,elapsed=self.run_watcher('launch_v0_2',clock_steps=(3580,1))
        self.assertEqual(result['reason'],'dual_view_recovery_shared_soft_deadline')
        self.assertEqual(elapsed,3581);self.assertEqual(code,1);self.assertTrue(stopped)


if __name__=='__main__':unittest.main()
