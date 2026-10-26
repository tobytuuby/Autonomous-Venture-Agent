"""Synthetic integration of the existing CEO runtime; no provider inference."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.ceo.agent import CEOAgent, CEO_TOOL_SCHEMAS
from agents.ceo.durable_state import DurableDecisionStore
from agents.ceo.provider import ModelProviderError
from agents.ceo.venture_exercise import ROOT, SYSTEM, fixture, run_exercise, main
from kernel.p6.registry import canonical, digest
from kernel.synthetic_venture_store import SyntheticStoreDenied, SyntheticVentureStore


class CEOVentureFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.path = Path(self.tmp.name)
        self.decisions = DurableDecisionStore(self.path / 'decisions.sqlite')
        self.store = SyntheticVentureStore(self.path / 'ventures.sqlite')
        self.calls = []
        self.attack = None

        def model(request, tools):
            self.assertEqual(tools, ())
            opportunity = request['opportunity']
            stage = opportunity['stage']
            self.calls.append(stage)
            response = {'decision': {'content': canonical(fixture(stage, opportunity['context']))},
                        'tool_call': None}
            if self.attack:
                return self.attack(stage, response)
            return response
        model.model_family = 'injected-fake-no-inference'
        self.model = model
        self.agent = self.make_agent()

    def make_agent(self, **kwargs):
        return CEOAgent(self.model, SYSTEM, self.path / 'decisions.jsonl',
                        durable_store=self.decisions, advisory_only=True, **kwargs)

    def tearDown(self):
        self.decisions.close()
        self.store.close()
        self.tmp.cleanup()

    def run_flow(self):
        return run_exercise(self.store, ceo_agent=self.agent)

    def test_complete_flow_reopens_and_replays_without_inference_or_duplicate_allocation(self):
        first = self.run_flow()
        self.assertEqual(self.calls, ['evaluation', 'manager', 'review'])
        self.assertEqual(first['model_call_count'], 3)
        self.assertFalse(first['ai_inference_independently_verified'])
        flow = first['stored']['flow']
        evidence = flow['decision_provenance']
        self.assertEqual(evidence, first['evidence'])
        self.assertEqual(len(flow['worker_results']), 3)
        self.assertEqual(flow['worker_results'][1]['result']['total'], 5000)
        self.assertEqual(first['stored']['available_to_spend_cents'], 0)
        for index, item in enumerate(evidence):
            row = self.decisions.get(item['decision_id'])
            self.assertEqual(row['state'], 'completed')
            self.assertEqual(row['configuration_fingerprint'], item['configuration_fingerprint'])
            self.assertEqual(json.loads(row['response']['decision']['content']), item['response'])
            self.assertEqual(item['parent_decision_id'], evidence[index-1]['decision_id'] if index else None)
            self.assertFalse(row['response']['executed'])
            self.assertEqual(item['durable_response_hash'], digest(canonical(row['response'])))
            self.assertEqual(item['durable_event_hash'], self.decisions.events(item['decision_id'])[-1]['event_hash'])
        self.assertEqual(evidence[2]['response']['aggregate_hash'], digest(canonical(flow['manager_aggregate'])))
        self.decisions.close()
        self.decisions = DurableDecisionStore(self.path / 'decisions.sqlite')
        self.agent = self.make_agent()
        self.store.close()
        self.store = SyntheticVentureStore(self.path / 'ventures.sqlite')
        replay = self.run_flow()
        self.assertEqual(replay['stored'], first['stored'])
        self.assertEqual(replay['model_call_count'], 0)
        self.assertEqual(len(self.calls), 3)
        self.assertTrue(self.decisions.verify_chain())
        self.assertEqual(len((self.path / 'decisions.jsonl').read_text().splitlines()), 3)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0], 1)

    def test_registry_interruption_recovers_from_completed_decisions(self):
        with patch.object(self.store, 'record', side_effect=RuntimeError('simulated crash')):
            with self.assertRaises(RuntimeError):
                self.run_flow()
        result = self.run_flow()
        self.assertEqual(result['model_call_count'], 0)
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(len(result['stored']['ledger']), 1)

    def test_response_recorded_checkpoint_recovers_without_model_retry(self):
        original = self.decisions.transition
        def crash(decision_id, state, **kwargs):
            if state == 'completed':
                raise RuntimeError('interrupted after durable response')
            return original(decision_id, state, **kwargs)
        with patch.object(self.decisions, 'transition', side_effect=crash):
            with self.assertRaises(RuntimeError):
                self.run_flow()
        result = self.run_flow()
        self.assertEqual(self.calls, ['evaluation', 'manager', 'review'])
        self.assertEqual(result['model_call_count'], 2)

    def test_provider_failure_is_terminal_and_does_not_fallback(self):
        def fail(stage, response):
            if stage == 'manager':
                raise ModelProviderError('simulated unavailable model')
            return response
        self.attack = fail
        with self.assertRaises(ModelProviderError):
            self.run_flow()
        self.attack = None
        with self.assertRaises(ValueError):
            self.run_flow()
        self.assertEqual(self.calls, ['evaluation', 'manager'])
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0], 0)
        states = self.decisions._connection.execute('SELECT state FROM shadow_decisions').fetchall()
        self.assertEqual(sorted(row[0] for row in states), ['completed', 'rejected'])

    def test_tools_and_authority_fields_are_quarantined_without_registry_writes(self):
        for stage in ['evaluation', 'manager', 'review']:
            for attack in ['tool', 'authority', 'malformed']:
                with self.subTest(stage=stage, attack=attack):
                    self.decisions.close()
                    self.decisions = DurableDecisionStore(':memory:')
                    self.agent = self.make_agent()
                    def change(current, response):
                        if current == stage:
                            if attack == 'tool':
                                response['tool_call'] = {'schema': CEO_TOOL_SCHEMAS[0]}
                            elif attack == 'authority':
                                parsed = json.loads(response['decision']['content'])
                                parsed['capital_authorized'] = True
                                response['decision']['content'] = canonical(parsed)
                            else:
                                response['decision']['content'] = '{"x":1,"x":2}'
                        return response
                    self.attack = change
                    with self.assertRaises(ValueError):
                        self.run_flow()
                    self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0], 0)
                    self.assertEqual(self.decisions._connection.execute(
                        "SELECT COUNT(*) FROM shadow_decisions WHERE state='quarantined'").fetchone()[0], 1)

    def test_semantically_invalid_packets_and_review_are_quarantined(self):
        for target in ['manager', 'review']:
            with self.subTest(target=target):
                self.decisions.close()
                self.decisions = DurableDecisionStore(':memory:')
                self.agent = self.make_agent()
                def attack(stage, response):
                    if stage == target:
                        parsed = json.loads(response['decision']['content'])
                        if stage == 'manager':
                            parsed['plan']['tasks'][0]['worker_type'] = 'shell'
                        else:
                            parsed['aggregate_hash'] = 'wrong'
                        response['decision']['content'] = canonical(parsed)
                    return response
                self.attack = attack
                with self.assertRaises(ValueError):
                    self.run_flow()
                self.assertEqual(self.decisions._connection.execute(
                    "SELECT COUNT(*) FROM shadow_decisions WHERE state='quarantined'").fetchone()[0], 1)
                self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0], 0)

    def test_inflight_checkpoint_retries_only_unrecorded_advisory_call(self):
        def interrupt(*args):
            raise RuntimeError('crash before response persisted')
        with patch.object(self.decisions, 'record_response', side_effect=interrupt):
            with self.assertRaises(RuntimeError):
                self.run_flow()
        self.assertEqual(self.calls, ['evaluation'])
        result = self.run_flow()
        self.assertEqual(self.calls, ['evaluation', 'evaluation', 'manager', 'review'])
        states = [item['state'] for item in self.decisions.events(result['evidence'][0]['decision_id'])]
        self.assertIn('replayable', states)
        self.assertEqual(len(result['stored']['ledger']), 1)

    def test_changed_configuration_rejected_before_replay_or_new_model_calls(self):
        self.run_flow()
        self.agent = self.make_agent(runner_version='changed-runtime')
        with self.assertRaises(ValueError):
            self.run_flow()
        self.assertEqual(len(self.calls), 3)

    def test_provenance_tampering_and_rebinding_detected(self):
        result = self.run_flow()
        flow = result['stored']['flow']
        for target in ['parent', 'plan', 'aggregate', 'authority']:
            altered = copy.deepcopy(flow)
            evidence = altered['decision_provenance']
            if target == 'parent':
                evidence[2]['parent_decision_id'] = 'other'
            elif target == 'plan':
                evidence[1]['response']['plan']['tasks'][1]['inputs']['values'] = [1, -1]
                evidence[1]['response_hash'] = digest(canonical(evidence[1]['response']))
            elif target == 'aggregate':
                evidence[2]['response']['aggregate_hash'] = 'other'
                evidence[2]['response_hash'] = digest(canonical(evidence[2]['response']))
            else:
                evidence[0]['payment_authorized'] = True
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.store._check_flow(altered)
        # Hash is also checked on reopen/read, not merely on insertion.
        self.store.db.execute("UPDATE ventures SET flow_json='{}'")
        self.store.db.commit()
        with self.assertRaises(SyntheticStoreDenied):
            self.store.read('exercise-restock', portfolio_id='portfolio-synthetic')

    def test_shelving_all_ideas_is_durable_without_workers_or_allocation(self):
        def shelve(stage, response):
            parsed = json.loads(response['decision']['content'])
            parsed['selected_id'] = None
            response['decision']['content'] = canonical(parsed)
            return response
        self.attack = shelve
        self.assertEqual(self.run_flow()['status'], 'ALL_IDEAS_SHELVED')
        self.assertEqual(self.run_flow()['status'], 'ALL_IDEAS_SHELVED')
        self.assertEqual(self.calls, ['evaluation'])
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM ventures').fetchone()[0], 0)

    def test_cli_durable_mode_and_path_collision(self):
        args = ['exercise', '--durable-ceo', '--database', str(self.path / 'cli.sqlite'),
                '--report', str(self.path / 'report.json')]
        with patch.dict('os.environ', {}, clear=True), patch('sys.argv', args):
            self.assertEqual(main(), 0)
            self.assertEqual(main(), 0)
        report = json.loads((self.path / 'report.json').read_text())
        self.assertEqual(report['model_call_count'], 0)
        self.assertEqual(report['decision_mode'], 'durable_existing_shadow_ceo')
        args[-1] = str(self.path / 'cli.decisions.sqlite')
        with patch('sys.argv', args), self.assertRaises(ValueError):
            main()

    def test_exercise_refuses_non_durable_or_tool_enabled_agent(self):
        for agent in [CEOAgent(self.model, SYSTEM, self.path / 'unused'),
                      CEOAgent(self.model, SYSTEM, self.path / 'unused', durable_store=self.decisions)]:
            with self.assertRaises(ValueError):
                run_exercise(self.store, ceo_agent=agent)
        self.assertEqual(self.calls, [])

    def test_manager_contract_binds_each_candidate_amount_without_mutating_template(self):
        from agents.ceo.venture_exercise import CANDIDATES, SCHEMAS, response_contract
        original = copy.deepcopy(SCHEMAS)
        for candidate in CANDIDATES:
            contract = response_contract('manager', {'candidate': candidate})
            self.assertEqual(contract['plan']['tasks'][1]['inputs']['values'],
                             [candidate['price_cents'] * candidate['units'], -candidate['cost_cents']])
            self.assertEqual(len(contract['plan']['tasks'][0]['inputs']['evidence']), 3)
        self.assertEqual(SCHEMAS, original)

    def test_natural_manager_text_and_reordered_keys_preserve_exact_provenance(self):
        def natural(stage, response):
            if stage != 'manager':
                return response
            # Independently authored model-shaped content, not fixture deliverables.
            deliverables = {
                'validation_experiment': 'Draft five offline interview questions; no interviews have occurred.',
                'offer': 'A hypothetical pottery studio supply checklist for $20.',
                'landing_page_copy': 'Keep glaze and clay on your weekly stock list. Unpublished concept.',
            }
            manager = {'plan': {'tasks': [
                {'task_id': 'summary.1', 'title': 'Review the concept',
                 'objective': 'Summarize the supplied hypothetical copy.',
                 'worker_type': 'summarize_evidence', 'inputs': {'evidence': [
                     deliverables[k] for k in ('offer', 'landing_page_copy', 'validation_experiment')]}},
                {'task_id': 'arithmetic-2', 'title': 'Check assumed margin',
                 'objective': 'Add revenue and negative cost in cents.',
                 'worker_type': 'calculate', 'inputs': {'values': [10000, -5000]}},
                {'task_id': 'checks_3', 'title': 'Prepare offline checks',
                 'objective': 'List research still needed.',
                 'worker_type': 'checklist', 'inputs': {'checks': ['Assess free alternatives offline.']}},
            ]}, 'deliverables': deliverables}
            self.natural_manager = manager
            return {'tool_call': None, 'decision': {'content': json.dumps(manager)}}
        self.attack = natural
        result = self.run_flow()
        manager = result['evidence'][1]
        self.assertEqual(manager['response'], self.natural_manager)
        self.assertEqual(manager['response_hash'], digest(canonical(self.natural_manager)))
        self.assertEqual(manager['request']['opportunity']['response_contract']['plan']['tasks'][1]
                         ['inputs']['values'], [10000, -5000])
        self.assertIn('verbatim', manager['request']['opportunity']['response_guidance'])
        self.assertFalse(result['ai_inference_independently_verified'])
        self.assertEqual(result['external_action_count'], 0)
        self.assertTrue(self.decisions.verify_chain())
        self.assertEqual(self.run_flow()['model_call_count'], 0)

    def test_malformed_manager_has_safe_reason_and_terminal_quarantine(self):
        from agents.ceo.agent import ResponseValidationError
        cases = (
            ('json', 'JSON_INVALID'),
            ('reference', 'MANAGER_EVIDENCE_MISMATCH'),
            ('reordered', 'MANAGER_EVIDENCE_MISMATCH'),
            ('amount', 'MANAGER_ARITHMETIC_MISMATCH'),
            ('extra', 'MANAGER_PACKETS_INVALID'),
            ('worker', 'MANAGER_PACKETS_INVALID'),
        )
        for attack, code in cases:
            with self.subTest(attack=attack):
                self.decisions.close()
                self.decisions = DurableDecisionStore(':memory:')
                self.agent = self.make_agent()
                self.calls.clear()
                def change(stage, response):
                    if stage != 'manager':
                        return response
                    if attack == 'json':
                        response['decision']['content'] = 'SENSITIVE_UNTRUSTED_SENTINEL'
                        return response
                    parsed = json.loads(response['decision']['content'])
                    tasks = parsed['plan']['tasks']
                    if attack == 'reference':
                        tasks[0]['inputs']['evidence'] = ['deliverables.offer',
                            'deliverables.landing_page_copy', 'SENSITIVE_UNTRUSTED_SENTINEL']
                    elif attack == 'reordered':
                        tasks[0]['inputs']['evidence'].reverse()
                    elif attack == 'amount':
                        tasks[1]['inputs']['values'] = ['10000', '-5000']
                    elif attack == 'extra':
                        tasks[0]['command'] = 'SENSITIVE_UNTRUSTED_SENTINEL'
                    else:
                        tasks[0]['worker_type'] = 'SENSITIVE_UNTRUSTED_SENTINEL'
                    response['decision']['content'] = canonical(parsed)
                    return response
                self.attack = change
                with self.assertRaises(ResponseValidationError) as failure:
                    self.run_flow()
                self.assertEqual(str(failure.exception), code)
                row = self.decisions._connection.execute(
                    "SELECT decision_id, response_json FROM shadow_decisions WHERE state='quarantined'"
                ).fetchone()
                self.assertIsNone(row['response_json'])
                events = self.decisions.events(row['decision_id'])
                self.assertEqual(events[-1]['event']['detail'], code)
                self.assertNotIn('SENSITIVE_UNTRUSTED_SENTINEL', canonical(list(events)))
                self.assertTrue(self.decisions.verify_chain())
                self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0], 0)
                with self.assertRaises(ValueError):
                    self.run_flow()
                self.assertEqual(self.calls, ['evaluation', 'manager'])

    def test_cli_reports_only_allowlisted_response_reason(self):
        from agents.ceo.agent import ResponseValidationError
        from agents.ceo.venture_exercise import cli
        from contextlib import redirect_stdout
        from io import StringIO
        for reason in ('MANAGER_EVIDENCE_MISMATCH', 'SENSITIVE_UNTRUSTED_SENTINEL'):
            output = StringIO()
            with patch('agents.ceo.venture_exercise.main',
                       side_effect=ResponseValidationError(reason)), redirect_stdout(output):
                self.assertEqual(cli(), 4)
            self.assertNotIn('SENSITIVE_UNTRUSTED_SENTINEL', output.getvalue())
            self.assertIn('quarantine is terminal; use a fresh database', output.getvalue())
