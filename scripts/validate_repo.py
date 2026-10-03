#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
errors=[]
# Validate JSON files
for p in ROOT.rglob('*.json'):
    try:
        json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        errors.append(f'JSON invalid: {p.relative_to(ROOT)}: {e}')
# Validate JSONL
for p in ROOT.rglob('*.jsonl'):
    for i,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
        if not line.strip(): continue
        try: json.loads(line)
        except Exception as e: errors.append(f'JSONL invalid: {p.relative_to(ROOT)}:{i}: {e}')
# Validate relative markdown links to local files
link_re = re.compile(r'\[[^\]]+\]\(([^)]+)\)')
for p in ROOT.rglob('*.md'):
    text=p.read_text(encoding='utf-8',errors='replace')
    for target in link_re.findall(text):
        if target.startswith(('http://','https://','#','mailto:')): continue
        clean=target.split('#',1)[0]
        if not clean: continue
        dest=(p.parent/clean).resolve()
        try: dest.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f'Link escapes repo: {p.relative_to(ROOT)} -> {target}')
            continue
        if not dest.exists(): errors.append(f'Broken link: {p.relative_to(ROOT)} -> {target}')
# Required files
for req in ['SKILL.md','README.md','skill-manifest.json','runtime/stage-machine.md','evals/cases.jsonl']:
    if not (ROOT/req).exists(): errors.append(f'Missing required file: {req}')
if errors:
    print('\n'.join(errors)); sys.exit(1)
print('Repository validation passed')
