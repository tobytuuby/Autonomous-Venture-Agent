import unittest
from datetime import datetime, timedelta, timezone
from kernel.compliance import AuditSampler, Breaker, Manifest


class ComplianceTests(unittest.TestCase):
    def test_expired_manifest_denies_without_grace_period(self):
        now = datetime.now(timezone.utc)
        manifest = Manifest("email", "operator", "v1", now - timedelta(hours=2), now - timedelta(seconds=1), frozenset({"send"}), frozenset())
        self.assertFalse(manifest.permits("send", now))

    def test_prohibited_action_overrides_permitted_action(self):
        now = datetime.now(timezone.utc)
        manifest = Manifest("email", "operator", "v1", now, now + timedelta(hours=1), frozenset({"send"}), frozenset({"send"}))
        self.assertFalse(manifest.permits("send", now))

    def test_latching_requires_human_reset(self):
        breaker = Breaker("latching")
        breaker.trip()
        self.assertEqual(breaker.observe_clean(), "OPEN")
        with self.assertRaises(PermissionError):
            breaker.reset()
        self.assertEqual(breaker.reset(human_operator=True), "CLOSED")

    def test_cooldown_requires_clean_window(self):
        breaker = Breaker("cooldown")
        breaker.trip()
        self.assertEqual(breaker.observe_clean(), "OPEN")
        self.assertEqual(breaker.observe_clean(), "CLOSED")

    def test_progressive_requires_staged_clean_recovery(self):
        breaker = Breaker("progressive")
        breaker.trip()
        breaker.observe_clean()
        breaker.observe_clean()
        self.assertEqual(breaker.observe_clean(), "HALF_OPEN")

    def test_audit_sampler_has_operator_independent_selection(self):
        sampler = AuditSampler(("a", "b", "c", "d"))
        first = sampler.sample(2)
        self.assertEqual(len(first), 2)
        self.assertEqual(len(sampler.samples), 1)


if __name__ == "__main__":
    unittest.main()
