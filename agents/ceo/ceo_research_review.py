"""One durable, signed CEO model review of stalled, Owner-approved research.

Strictly internal: findings are hypotheses, not customer research evidence or
authorization to launch, spend venture capital, or contact customers.
"""
import json
import os
import pathlib
import tempfile
from datetime import datetime,timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from agents.ceo.escalation_inbox import canonical
from agents.ceo.venture_workflow import hashed

SYSTEM=(
    "You are the venture CEO reviewing signed internal research artifacts after "
    "a bounded research round or Manager escalation. You may not contact customers, "
    "spend, launch, or claim public market validation. Make a substantive assessment, "
    "identifying strong work, missing externally verified demand/competitor "
    "evidence, and the smallest next research task. Return strict JSON with "
    "exactly recommendation,assessment,evidence_gaps,next_internal_task. "
    "Recommendation must be NEEDS_MORE_RESEARCH, READY_FOR_OWNER_DISCUSSION, or "
    "REJECT_OR_DEFER. At Round 3, choose PROCEED_TO_MVP or REJECT_OR_DEFER. "
    "Each other field must be 40 to 500 characters. Do not fabricate citations."
)


def write_atomic(path,value):
    path=pathlib.Path(path)
    fd,name=tempfile.mkstemp(prefix='.ceo-review-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as file:
            file.write((canonical(value)+'\n').encode())
            file.flush()
            os.fsync(file.fileno())
        os.chmod(name,0o600)
        os.replace(name,path)
        dirfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(dirfd)
        finally:os.close(dirfd)
    finally:
        if os.path.exists(name):os.unlink(name)


def review(config,state,client,provider=None):
    flow=state['id']
    if (config['role']!='ceo' or config['actor_id']!='service-ceo'
            or not flow.startswith('research-') or state['state'] not in ('HOLD','CEO_REVIEW','OWNER_REVIEW','CEO_REDIRECTION')
            or state['mode']!='PREPARATION_ONLY'
            or any(state[k] is not False for k in (
                'operational_authority','external_actions_allowed',
                'execution_performed','money_released'))):
        raise ValueError('only bounded Owner research hold may receive CEO review')
    root=pathlib.Path(config['state_dir']).parent/'research-reviews'
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    from agents.ceo.venture_workflow import research_rounds, research_session
    number=len(research_rounds(state)) if 'handoff' in state else 1
    path=root/(research_session(state)+'.json') if 'handoff' in state else root/(flow+'.json')
    current=hashed(state)
    if path.is_symlink():
        raise ValueError('CEO review state alias denied')
    if path.exists():
        prior=json.loads(path.read_text())
        if prior.get('snapshot_hash') != current:
            raise ValueError('prior CEO review bound to changed workflow')
        if prior.get('state')=='COMPLETE':
            return prior
        raise ValueError('ambiguous CEO provider outcome; manual reconciliation required')
    # Verify artifact digests before sending bounded text to the provider.
    import hashlib
    artifacts=[]
    for ref,sha in list(state['evidence'].items())[-9:]:
        if not ref.startswith('preparation-') or not ref.endswith(sha):
            continue
        raw=client.load(ref)
        if hashlib.sha256(raw).hexdigest()!=sha:
            raise ValueError('CEO research evidence digest mismatch')
        data=json.loads(raw)
        # Research rounds deliberately change scope_hash as objectives narrow.
        # The signed workflow's cumulative evidence map binds each digest to this
        # Owner-approved proposal, so retain prior-round evidence after verifying
        # its content hash. Manager and Worker records only are review material.
        if data.get('role') not in ('worker','manager'):
            continue
        if data.get('action') not in ('submit','improve','reject_premise','manager_approve'):
            continue
        artifacts.append(dict(role=data['role'],action=data['action'],
            deliverable=data['deliverable'][:500],explanation=data['explanation'][:160]))
    if not artifacts:
        raise ValueError('no signed Worker or Manager evidence to review')
    system = SYSTEM if number < 3 else SYSTEM.replace(
        'NEEDS_MORE_RESEARCH or READY_FOR_OWNER_DISCUSSION',
        'PROCEED_TO_MVP or REJECT_OR_DEFER (internal recommendation only, never launch)')
    request=dict(system=system,json_object_mode=True,
        opportunity=dict(workflow_id=flow,goal=state['scope']['tasks'][0],
            role='ceo',state=state['state'],scope_hash=state['scope_hash'],
            snapshot_sha256=current,research_round=number,
            research_state='QUOTA_HOLD',signed_artifacts=artifacts,
            external_market_evidence_verified=False))
    from agents.ceo.venture_exercise import configured_provider,strict_json
    model=provider or configured_provider(os.environ,required=True)
    if model.model!='gpt-6-sol':
        raise ValueError('CEO model identity denied')
    model.maximum_output_tokens=950
    # Persist the exact intent before external I/O. Ambiguity cannot trigger
    # a second paid request without an operator reconciliation.
    write_atomic(path,dict(state='PENDING',snapshot_hash=current,
        request_hash=hashed(request),created_utc=datetime.now(timezone.utc).isoformat()))
    if provider is None:
        from agents.ceo.hierarchy_providers import HierarchyProvider
        policy=json.loads(pathlib.Path(config['policy']).read_text())
        context=dict(config['context'],session_id=research_session(state),
            venture_id=flow,objective='; '.join(state['scope']['tasks']),rounds=number)
        metered=HierarchyProvider(role='ceo',actor='service-ceo',workflow_id=flow,
            client=client,policy=policy,context=context,local_provider=model,
            state_path=pathlib.Path(config['state_dir'])/'research-review-inference.sqlite')
        response=metered(request,())
    else:
        response=model(request,())  # Explicit isolated-test provider; no runtime fallback.
    if type(response) is not dict or response.get('tool_call') is not None:
        raise ValueError('CEO tool call forbidden')
    result=strict_json(response['decision']['content'])
    if type(result) is not dict or set(result)!={
            'recommendation','assessment','evidence_gaps','next_internal_task'}:
        raise ValueError('CEO bounded review fields required')
    permitted = ('NEEDS_MORE_RESEARCH','READY_FOR_OWNER_DISCUSSION','REJECT_OR_DEFER') if number < 3 else ('PROCEED_TO_MVP','REJECT_OR_DEFER')
    if result['recommendation'] not in permitted:
        raise ValueError('CEO recommendation outside internal scope')
    for field in ('assessment','evidence_gaps','next_internal_task'):
        if type(result[field]) is not str or not 40<=len(result[field])<=500:
            raise ValueError('CEO review text length bound')
    packet=dict(domain='owner-internal-research-ceo-review-v1',
        workflow_id=flow,snapshot_hash=current,model=model.model,
        assessment=result,external_market_evidence_verified=False,
        venture_admission=False,financial_authority=False,
        reviewed_utc=datetime.now(timezone.utc).isoformat())
    key=Ed25519PrivateKey.from_private_bytes(pathlib.Path(config['signing_key']).read_bytes())
    signed=dict(state='COMPLETE',snapshot_hash=current,packet=packet,
        signature=key.sign(canonical(packet).encode()).hex())
    write_atomic(path,signed)
    return signed
