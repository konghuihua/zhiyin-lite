import sys, os
sys.path.insert(0, r'C:\Users\admin\.openclaw\workspace\_published\zhiyin-lite')

from zhiyin import StateMachine, DriftSentinel, ToolConstraintChecker

# Test 1: StateMachine
sm = StateMachine()
sm.add_state('code', tools=['read','write','exec'], forbidden=['gateway'])
sm.transition_to('code')
assert sm.can_call('read').allowed, "read should be allowed"
assert not sm.can_call('gateway').allowed, "gateway should be blocked"
print(f"PASS StateMachine: {sm.summary()}")

# Test 2: DriftSentinel
ds = DriftSentinel()
ds.record_turn('t1', 'code_dev', ['read','write'], [{'type': 'SyntaxError'}])
ds.record_turn('t2', 'code_dev', ['edit','exec'], [{'type': 'SyntaxError'}])
r = ds.check(intent='code_dev', tools_so_far=['write','exec']*6)
assert r['triggered'], "should trigger on repeated error + tool bloat"
print(f"PASS DriftSentinel: triggered={r['triggered']} warnings={len(r['warnings'])}")

# Test 3: ToolConstraintChecker
tc = ToolConstraintChecker(sm)
got = tc.classify_intent('i want to write some code')
print(f"PASS ToolConstraintChecker: intent={got} state={tc.summary()}")

print("\nALL 3 MODULES OK — zhiyin-lite v0.1.0")
