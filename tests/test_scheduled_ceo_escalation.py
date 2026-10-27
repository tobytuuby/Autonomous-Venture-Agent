"""Synthetic signed grants and fixture transport; no real authority or inference."""
import contextlib
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agents.ceo.agent import CEOAgent
from agents.ceo.escalation_inbox import EscalationInbox, canonical
from agents.ceo.scheduled_escalation import SYSTEM, FILES
from agents.ceo.scheduled_exercise import run
from agents.ceo.scheduled_intake import ITEM_ID, PACKET_SHA256
from agents.ceo.venture_exercise import configured_provider
from tests import test_advisory_queue as queue_tests


class ScheduledEscalationTests(unittest.TestCase):
    tearDown = queue_tests.AdvisoryQueueTests.tearDown
    rows = queue_tests.AdvisoryQueueTests.rows
    seed = queue_tests.AdvisoryQueueTests.seed
    invoke = queue_tests.AdvisoryQueueTests.invoke

    def setUp(self):
        queue_tests.AdvisoryQueueTests.setUp(self)
        self.signer = Ed25519PrivateKey.generate()  # synthetic test authority only
        self.key = self.signer.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.grant_file = self.root / 'grant.json'
        self.env['CEO_KERNEL_GATE_FILE'] = str(self.gate)
        agent = CEOAgent(configured_provider(self.env, required=True), SYSTEM,
                         self.root / 'unused.jsonl', advisory_only=True,
                         runner_version='scheduled-escalation-v1')
        now = datetime.now(timezone.utc)
        self.grant = dict(grant_id='fixture-one-call', operator='fixture-operator',
            item_id=ITEM_ID, packet_hash=PACKET_SHA256, scope='SHADOW_PREPARATION_ONLY',
            configuration_fingerprint=agent.configuration_fingerprint, maximum_requests=1,
            budget_reference='TEST-ONLY-safe-worst-case-one-call-budget',
            reconciliation_reference='TEST-ONLY-previous-ambiguous-spend-accounted-for',
            issued_at=(now-timedelta(minutes=1)).isoformat(),
            expires_at=(now+timedelta(hours=1)).isoformat())
        self.review = dict(item_id=ITEM_ID, packet_hash=PACKET_SHA256,
            disposition='HANDOFF', summary='Fixture: revised online scope needs bounded preparation.',
            manager_id='manager-venture-001', instructions=['Prepare an online scope proposal.'],
            owner_action='Fixture: request independently authorized signer.', scope='PREPARATION_ONLY')
        self.failure = None
        self.write_grant()

    def write_grant(self, signer=None):
        self.grant_file.write_text(canonical(dict(grant=self.grant, signature=(
            signer or self.signer).sign(canonical(self.grant).encode()).hex())))

    def transport(self, request, **kwargs):
        body = json.loads(request.data)
        opportunity = json.loads(body['messages'][1]['content'])
        if opportunity['stage'] != 'escalation_review':
            return queue_tests.AdvisoryQueueTests.transport(self, request, **kwargs)
        self.assertEqual(set(body), {'model', 'messages'})
        self.assertEqual(opportunity['response_contract']['packet_hash'], PACKET_SHA256)
        self.assertIn('not an executed CEO decision', opportunity['context']['packet'])
        self.assertNotIn('test-secret', request.data.decode())
        self.assertTrue((self.state / FILES[0]).exists())  # durable before network
        self.calls.append('escalation_review')
        if self.failure:
            raise self.failure
        stream = Mock()
        stream.read.return_value = canonical({'choices': [{'message': {
            'content': canonical(self.review)}}]}).encode()
        return contextlib.nullcontext(stream)

    def process(self, **changes):
        options = dict(escalation_only=True, escalation_grant=self.grant_file,
                       operator_public_key=self.key)
        options.update(changes)
        with patch('agents.ceo.provider.urllib.request.OpenerDirector.open',
                   side_effect=self.transport):
            return run(self.state, self.gate, self.env, **options)

    def item(self):
        inbox = EscalationInbox(self.state / 'escalations.sqlite')
        try:
            return inbox.read(ITEM_ID)
        finally:
            inbox.close()

    def legacy_hashes(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.state.iterdir() if p.name.startswith(('queue.', 'workflow.'))
                or p.name in ('report.json', 'status.json')}

    def test_blocked_legacy_does_not_prevent_authorized_dynamic_review(self):
        self.seed()
        self.cycle = '2026-10-26T01'
        self.crash = True
        with self.assertRaises(KeyboardInterrupt):
            self.invoke()
        self.crash = False
        before = self.legacy_hashes()
        count = len(self.calls)
        code, summary = self.process()
        self.assertEqual(code, 0)
        self.assertEqual(summary['status'], 'ESCALATION_ADVISORY_REVIEW_RECORDED')
        self.assertEqual(summary['inference_requests_this_tick'], 1)
        self.assertEqual(summary['queue_status'], 'NOT_RUN')
        self.assertEqual(len(self.calls), count+1)
        self.assertEqual(before, self.legacy_hashes())
        item = self.item()
        self.assertEqual(item['review'], self.review)
        self.assertEqual(item['status'], 'REVIEWED')
        self.assertIsNone(item['decision'])
        self.assertFalse(item['handoff_exported'])
        inbox = EscalationInbox(self.state / 'escalations.sqlite')
        try:
            with self.assertRaises(ValueError):
                inbox.handoff(ITEM_ID, 'manager-venture-001')
        finally:
            inbox.close()
        for _ in range(2):
            self.assertEqual(self.process()[1]['inference_requests_this_tick'], 0)
        self.assertEqual(len(self.calls), count+1)

    def test_missing_grant_does_not_even_configure_provider_or_bootstrap(self):
        with patch('agents.ceo.scheduled_escalation.configured_provider', side_effect=AssertionError()):
            code, summary = self.process(escalation_grant=None, operator_public_key=None)
        self.assertEqual(code, 3)
        self.assertEqual(summary['status'], 'ESCALATION_AUTHORIZATION_REQUIRED')
        self.assertFalse(summary['escalation']['ceo_work_performed'])
        self.assertEqual(self.calls, [])
        self.assertFalse((self.state / 'workflow.sqlite').exists())
        self.assertEqual(self.item()['status'], 'RECEIVED')

    def test_signed_grant_bindings_and_budget_required_before_reservation(self):
        changes = ({'item_id':'other'}, {'packet_hash':'0'*64}, {'scope':'LIVE'},
            {'configuration_fingerprint':'wrong'}, {'maximum_requests':2},
            {'maximum_requests':True}, {'maximum_requests':0}, {'operator':''},
            {'budget_reference':''}, {'reconciliation_reference':''}, {'extra':True},
            {'expires_at':self.grant['issued_at']}, {'issued_at':'invalid'},
            {'issued_at':'2026-01-01T00:00:00'},
            {'expires_at':(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()})
        original = self.grant.copy()
        for change in changes:
            self.grant = dict(original, **change)
            self.write_grant()
            with self.subTest(change=change):
                self.assertEqual(self.process()[0], 4)
                self.assertFalse((self.state / FILES[0]).exists())
                self.assertEqual(self.item()['status'], 'RECEIVED')
        self.assertEqual(self.calls, [])

    def test_wrong_signer_key_missing_gate_and_configuration_denied(self):
        self.write_grant(Ed25519PrivateKey.generate())
        self.assertEqual(self.process()[0], 4)
        self.write_grant()
        self.assertEqual(self.process(operator_public_key=b'bad')[0], 4)
        self.env['CEO_MODEL_NAME'] = 'changed'
        self.assertEqual(self.process()[0], 4)
        self.gate.write_text('{}')
        self.assertEqual(self.process()[0], 4)
        self.assertEqual(self.calls, [])

    def test_transport_error_and_changed_grant_never_retry_ambiguous_attempt(self):
        self.failure = OSError('test-secret remote body')
        self.assertEqual(self.process()[0], 4)
        before = (self.state / FILES[0]).read_bytes()
        self.failure = None
        self.grant['grant_id'] = 'new-grant-does-not-reset-attempt'
        self.write_grant()
        self.assertEqual(self.process()[1]['status'], 'ESCALATION_ATTEMPT_BLOCKED')
        self.assertEqual(self.calls, ['escalation_review'])
        self.assertEqual((self.state / FILES[0]).read_bytes(), before)
        self.assertNotIn('test-secret', (self.state / 'inbox-status.json').read_text())

    def test_process_death_after_dispatch_is_not_replayed(self):
        self.failure = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.process()
        self.failure = None
        self.assertEqual(self.process()[1]['status'], 'ESCALATION_ATTEMPT_BLOCKED')
        self.assertEqual(self.calls, ['escalation_review'])

    def test_invalid_model_reviews_never_become_decisions_or_retry(self):
        for change in ({'scope':'LIVE'}, {'packet_hash':'bad'}, {'item_id':'bad'},
                       {'manager_id':'other'}, {'instructions':[]}, {'extra':True},
                       {'summary':''}, {'disposition':'APPROVED'}):
            with self.subTest(change=change):
                self.review.update(change)
                self.assertEqual(self.process()[0], 4)
                self.assertIsNone(self.item()['review'])
                self.assertEqual(self.process()[1]['status'], 'ESCALATION_ATTEMPT_BLOCKED')
            # Independent temporary state for each invalid response, never reset a real attempt.
            self.state = self.root / ('state-' + str(len(self.calls)))
            self.review = dict(item_id=ITEM_ID, packet_hash=PACKET_SHA256,
                disposition='HANDOFF', summary='Fixture', manager_id='manager-venture-001',
                instructions=['Fixture preparation'], owner_action=None, scope='PREPARATION_ONLY')

    def test_partial_import_and_inbox_tamper_deny_dispatch(self):
        self.state.mkdir()
        (self.state / FILES[1]).touch()
        self.assertEqual(self.process()[0], 4)
        self.assertEqual(self.calls, [])
        inbox = EscalationInbox(self.state / 'escalations.sqlite')
        inbox.db.execute("UPDATE inbox SET snapshot='{}'")
        inbox.close()
        self.assertEqual(self.process()[0], 4)
        self.assertEqual(self.calls, [])

    def test_reservation_failure_before_dispatch_and_ack_failure_after_reservation(self):
        with patch('agents.ceo.scheduled_exercise.sync_directory', side_effect=OSError()):
            # intake/status IO may also fail; no dispatch is allowed.
            with self.assertRaises(OSError):
                self.process()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.process()[1]['status'], 'ESCALATION_ATTEMPT_BLOCKED')

    def test_existing_operator_ack_does_not_require_impersonation(self):
        self.process(escalation_grant=None, operator_public_key=None)
        inbox = EscalationInbox(self.state / 'escalations.sqlite')
        inbox.ack(ITEM_ID, 'fixture-original-operator')
        inbox.close()
        self.assertEqual(self.process()[0], 0)
        self.assertEqual(self.item()['ack'], 'fixture-original-operator')

    def test_grant_alone_isolates_tick_and_default_schedule_exposes_missing_gate(self):
        code, summary = self.process(escalation_only=False)
        self.assertEqual(code, 0)
        self.assertEqual(self.calls, ['escalation_review'])
        self.assertEqual(summary['queue_status'], 'NOT_RUN')
        self.assertFalse((self.state / 'workflow.sqlite').exists())

    def test_aliased_and_oversized_grants_never_dispatch(self):
        original = self.grant_file
        alias = self.root / 'alias.json'
        alias.symlink_to(original)
        self.assertEqual(self.process(escalation_grant=alias)[0], 4)
        original.write_bytes(b'x'*16001)
        self.assertEqual(self.process()[0], 4)
        self.assertEqual(self.calls, [])

    def test_crash_between_model_response_and_inbox_commit_blocks_retry(self):
        with patch('agents.ceo.escalation_inbox.EscalationInbox.record_review', side_effect=OSError()):
            self.assertEqual(self.process()[0], 4)
        self.assertEqual(self.item()['status'], 'ACKNOWLEDGED')
        self.assertEqual(self.process()[1]['status'], 'ESCALATION_ATTEMPT_BLOCKED')
        self.assertEqual(self.calls, ['escalation_review'])

    def test_status_publication_failure_after_review_commit_replays_review(self):
        from agents.ceo.scheduled_exercise import write_json
        def fail_status(path, value, **kw):
            if path.name == 'inbox-status.json':
                raise OSError('status interrupted')
            return write_json(path, value, **kw)
        with patch('agents.ceo.scheduled_exercise.write_json', side_effect=fail_status):
            with self.assertRaises(OSError):
                self.process()
        self.assertEqual(self.item()['review'], self.review)
        self.assertEqual(self.process()[1]['status'], 'ESCALATION_REVIEW_PRESENT')
        self.assertEqual(self.calls, ['escalation_review'])

    def test_hold_recommendation_is_reviewed_not_authenticated_hold(self):
        self.review.update(disposition='HOLD', instructions=[])
        self.assertEqual(self.process()[0], 0)
        self.assertEqual(self.item()['status'], 'REVIEWED')
        self.assertIsNone(self.item()['decision'])

    def test_tools_and_duplicate_json_keys_denied_and_terminal(self):
        from agents.ceo.provider import OpenAICompatibleShadowModel
        for raw in ({'decision': {'content': canonical(self.review)}, 'tool_call': {'schema':'shell'}},
                    {'decision': {'content':'{"scope":"LIVE","scope":"PREPARATION_ONLY"}'},
                     'tool_call':None}):
            with patch.object(OpenAICompatibleShadowModel, '__call__', return_value=raw):
                self.assertEqual(self.process()[0], 4)
                self.assertIsNone(self.item()['review'])
                self.assertEqual(self.process()[1]['status'], 'ESCALATION_ATTEMPT_BLOCKED')
            self.state = self.root / 'second-invalid-fixture'

    def test_orphan_sidecars_and_aliased_state_files_cannot_start_new_attempt(self):
        self.state.mkdir()
        for suffix in ('-journal', '-wal', '-shm'):
            path = self.state / (FILES[1]+suffix)
            path.write_bytes(b'')
            self.assertEqual(self.process()[0], 4)
            self.assertFalse((self.state / FILES[0]).exists())
            path.unlink()
        target = self.root / 'original'
        target.write_text('preserve')
        (self.state / FILES[0]).hardlink_to(target)
        with self.assertRaises(ValueError):
            self.process()
        self.assertEqual(target.read_text(), 'preserve')
        self.assertEqual(self.calls, [])

    def test_scheduler_lock_also_serializes_escalation_dispatch(self):
        import fcntl
        self.state.mkdir()
        with (self.state / 'runner.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.assertEqual(self.process()[1]['status'], 'BUSY')
        self.assertEqual(self.calls, [])

    def test_no_grant_default_tick_reports_gate_alongside_legacy_block(self):
        self.seed()
        self.cycle = '2026-10-26T01'
        self.crash = True
        with self.assertRaises(KeyboardInterrupt):
            self.invoke()
        self.crash = False
        count = len(self.calls)
        code, summary = self.invoke()
        self.assertEqual(code, 4)
        self.assertEqual(summary['status'], 'QUEUE_BLOCKED')
        self.assertEqual(summary['escalation']['status'], 'ESCALATION_AUTHORIZATION_REQUIRED')
        self.assertEqual(len(self.calls), count)
