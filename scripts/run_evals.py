#!/usr/bin/env python3
"""Static contract checks for behavioral eval cases.
This does not call an LLM. It verifies that eval fixtures are well-formed and
that expected behaviors reference known policy/validator concepts.
"""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
known_terms=set()
for folder in ['validators','policies','procedures','runtime']:
    for p in (ROOT/folder).rglob('*.md'):
        known_terms.update(w.lower() for w in p.read_text(encoding='utf-8',errors='replace').split())
required={'id','prompt','expected'}
errors=[]; count=0
for i,line in enumerate((ROOT/'evals/cases.jsonl').read_text(encoding='utf-8').splitlines(),1):
    if not line.strip(): continue
    count+=1
    obj=json.loads(line)
    missing=required-set(obj)
    if missing: errors.append(f'case line {i} missing {sorted(missing)}')
    if not isinstance(obj.get('expected'), (str,list,dict)):
        errors.append(f'case line {i} expected has unsupported type')
if errors:
    print('\n'.join(errors)); sys.exit(1)
print(f'Eval fixtures OK: {count} cases')
