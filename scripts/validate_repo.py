#!/usr/bin/env python3
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors=[]

for p in ROOT.rglob('*.json'):
    try:
        json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        errors.append(f'JSON invalid: {p.relative_to(ROOT)}: {e}')

for p in ROOT.rglob('*.jsonl'):
    for i,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except Exception as e:
            errors.append(f'JSONL invalid: {p.relative_to(ROOT)}:{i}: {e}')

link_re = re.compile(r'\[[^\]]+\]\(([^)]+)\)')
for p in ROOT.rglob('*.md'):
    text=p.read_text(encoding='utf-8',errors='replace')
    for target in link_re.findall(text):
        if target.startswith(('http://','https://','#','mailto:')):
            continue
        clean=target.split('#',1)[0]
        if not clean:
            continue
        dest=(p.parent/clean).resolve()
        try:
            dest.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f'Link escapes repo: {p.relative_to(ROOT)} -> {target}')
            continue
        if not dest.exists():
            errors.append(f'Broken link: {p.relative_to(ROOT)} -> {target}')

required = [
    'SKILL.md','README.md','skill-manifest.json','runtime/stage-machine.md',
    'evals/cases.jsonl','pyproject.toml','src/saasskill/state.py',
    'src/saasskill/gates.py','src/saasskill/orchestrator.py',
    'src/saasskill/cli.py','src/saasskill/capabilities.py',
    'src/saasskill/providers.py','src/saasskill/ahrefs.py','src/saasskill/semrush.py','src/saasskill/ads.py','src/saasskill/ad_requests.py','src/saasskill/direct_ads_transport.py','src/saasskill/executors.py','src/saasskill/camoufox_parser.py','src/saasskill/parser_normalizer.py','src/saasskill/analytics.py','src/saasskill/crm.py','src/saasskill/payments.py','src/saasskill/integration_status.py','src/saasskill/host_executor.py','src/saasskill/audit.py','src/saasskill/audit_workplan.py','src/saasskill/autopilot.py',
    'src/saasskill/mcp_server.py','tests/test_runtime.py',
    'tests/test_provider_routing.py','tests/test_ahrefs_normalizer.py','tests/test_semrush_normalizer.py','tests/test_ads_normalizers.py','tests/test_ad_requests.py','tests/test_direct_ads_transport.py','tests/test_ads_launch_gate.py','tests/test_executors.py','tests/test_camoufox_parser.py','tests/test_parser_normalizer.py','tests/test_analytics_normalizer.py','tests/test_crm_normalizer.py','tests/test_payments_normalizer.py','tests/test_merge_patch.py','tests/test_integration_status.py','tests/test_audit_workflow.py','tests/test_runner.py','docs/mcp.md','docs/provider-routing.md','docs/ahrefs.md','docs/semrush.md','docs/ads-integrations.md','docs/camoufox-parser.md','docs/integrations.md','docs/existing-project-audit.md',
    'CLAUDE.md','AGENTS.md','.mcp.json.example','evals/audit_cases.jsonl','references/audit-source-trace.md','references/github-reuse.md',
]
for req in required:
    if not (ROOT/req).exists():
        errors.append(f'Missing required file: {req}')

try:
    manifest=json.loads((ROOT/'skill-manifest.json').read_text(encoding='utf-8'))
    if manifest.get('version') != '1.5.0':
        errors.append(f"skill-manifest version must be 1.5.0, got {manifest.get('version')!r}")
    runtime=manifest.get('runtime') or {}
    if runtime.get('package') != 'saasskill':
        errors.append('skill-manifest.runtime.package must be saasskill')
    if not (manifest.get('hosts') or {}).get('mcp'):
        errors.append('skill-manifest.hosts.mcp must be enabled')
except Exception:
    pass

if errors:
    print('\n'.join(errors))
    sys.exit(1)
print('Repository validation passed')
