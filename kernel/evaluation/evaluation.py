"""Mode-independent evaluation boundary for adversarial certification."""
class EvaluationViolation(PermissionError): pass
class EvaluationBoundary:
    def authorize(self, *, mode: str, action: str, allowed: bool) -> bool:
        if mode not in {"known", "covert"}: raise EvaluationViolation("unknown evaluation mode")
        if not allowed: raise EvaluationViolation("action denied consistently in every evaluation mode")
        return True
