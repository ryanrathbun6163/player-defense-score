"""One shared, charged-runtime continuation deadline; pure CPU arithmetic.

The first launcher charged 1788.469 seconds. Conservatively debit 1789 from
the original 5400-second execution allowance. CPU-only repair downtime is not
execution. Every new participant uses this launch's exact absolute deadline.
"""
from datetime import datetime, timedelta, timezone
import math
import time

TOTAL_SECONDS = 5400
PRIOR_CHARGED_SECONDS = 1789
MAX_TOTAL_SECONDS = 3611
CLEANUP_RESERVE_SECONDS = 30
SOFT_STOP_SECONDS = 3581
SCHEMA = 'dual_view_context_recovery_deadline/v0.1'


def check(condition, message):
    if not condition:
        raise ValueError(message)


def utc(value):
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    check(isinstance(parsed, datetime) and parsed.tzinfo is not None and
          parsed.utcoffset() == timedelta(0), 'Deadline requires explicit UTC')
    return parsed


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def make_contract(prior, started_at_utc=None, started_monotonic=None, prior_binding=None):
    charged = prior['charged_elapsed_seconds']
    check(finite(charged) and math.ceil(charged) == PRIOR_CHARGED_SECONDS,
          'Prior charged execution debit changed')
    check(prior['event_remaining_owned_processes'] == 0 and
          prior['supervisor_result']['remaining_owned_processes_before_close'] == 0 and
          prior['supervisor_result']['job_cleanup_error'] is None, 'Prior owned cleanup not complete')
    began_utc = utc(started_at_utc or datetime.now(timezone.utc))
    began = time.monotonic() if started_monotonic is None else started_monotonic
    check(finite(began), 'Invalid launcher monotonic origin')
    result = dict(schema=SCHEMA, total_execution_allowance_seconds=TOTAL_SECONDS,
        prior_charged_elapsed_seconds=charged, prior_charged_rounded_up_seconds=PRIOR_CHARGED_SECONDS,
        remaining_execution_cap_seconds=MAX_TOTAL_SECONDS, cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
        soft_stop_seconds=SOFT_STOP_SECONDS, launcher_started_at_utc=began_utc.isoformat(),
        launcher_started_monotonic=began, hard_deadline_utc=(began_utc+timedelta(seconds=MAX_TOTAL_SECONDS)).isoformat(),
        soft_deadline_utc=(began_utc+timedelta(seconds=SOFT_STOP_SECONDS)).isoformat(),
        hard_deadline_monotonic=began+MAX_TOTAL_SECONDS, soft_deadline_monotonic=began+SOFT_STOP_SECONDS,
        CPU_only_repair_downtime_excluded=True, fresh_90_minute_budget=False,
        prior_charge_receipt=prior_binding)
    validate_contract(result)
    return result


def validate_contract(policy):
    value = policy.get('deadline_contract', policy)
    check(value.get('schema') == SCHEMA, 'Missing shared continuation deadline')
    check(value.get('total_execution_allowance_seconds') == TOTAL_SECONDS and
          value.get('prior_charged_rounded_up_seconds') == PRIOR_CHARGED_SECONDS and
          value.get('remaining_execution_cap_seconds') == MAX_TOTAL_SECONDS and
          value.get('cleanup_reserve_seconds') == CLEANUP_RESERVE_SECONDS and
          value.get('soft_stop_seconds') == SOFT_STOP_SECONDS and
          value.get('CPU_only_repair_downtime_excluded') is True and
          value.get('fresh_90_minute_budget') is False, 'Continuation execution debit/cap differs')
    charged = value.get('prior_charged_elapsed_seconds')
    check(finite(charged) and math.ceil(charged) == PRIOR_CHARGED_SECONDS,
          'Prior debit is inconsistent')
    start, hard, soft = [utc(value[key]) for key in
                        ('launcher_started_at_utc','hard_deadline_utc','soft_deadline_utc')]
    check((hard-start).total_seconds() == MAX_TOTAL_SECONDS and
          (soft-start).total_seconds() == SOFT_STOP_SECONDS, 'UTC deadlines do not share launcher origin')
    start_m, hard_m, soft_m = [value.get(key) for key in
                              ('launcher_started_monotonic','hard_deadline_monotonic','soft_deadline_monotonic')]
    check(all(finite(x) for x in (start_m,hard_m,soft_m)) and
          math.isclose(hard_m-start_m,MAX_TOTAL_SECONDS,rel_tol=0,abs_tol=1e-6) and
          math.isclose(soft_m-start_m,SOFT_STOP_SECONDS,rel_tol=0,abs_tol=1e-6),
          'Monotonic deadlines do not share launcher origin')
    if 'deadline_contract' in policy:
        check(policy.get('max_total_seconds') == MAX_TOTAL_SECONDS and
              policy.get('soft_stop_seconds') == SOFT_STOP_SECONDS and
              policy.get('cleanup_reserve_seconds') == CLEANUP_RESERVE_SECONDS,
              'Supervisor policy and shared deadline disagree')
    return value


def remaining_wall_seconds(policy, now=None, monotonic_now=None):
    value = validate_contract(policy)
    now = utc(now or datetime.now(timezone.utc))
    mono = time.monotonic() if monotonic_now is None else monotonic_now
    check(finite(mono), 'Invalid current monotonic time')
    # A backward wall-clock adjustment cannot extend the monotonic deadline;
    # a forward jump fails conservatively. Both clocks share one launch origin.
    return min((utc(value['hard_deadline_utc'])-now).total_seconds(),
               value['hard_deadline_monotonic']-mono)


def validate_ready(ready, contract):
    validate_contract(contract)
    check(ready.get('status') == 'fresh_readonly_event_baseline_ready' and
          ready.get('deadline_contract') == contract and
          ready.get('soft_stop_seconds') == SOFT_STOP_SECONDS and
          ready.get('hard_limit_seconds') == MAX_TOTAL_SECONDS,
          'Event watcher readiness deadline differs from launcher')
