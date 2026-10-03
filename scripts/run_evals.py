#!/usr/bin/env python3
"""Static contract checks for behavioral eval cases.
This does not call an LLM. It verifies that eval fixtures are well-formed.
"""
import json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required={'id','prompt','expected'}
errors=[]; count=0; seen=set()

files=sorted((ROOT/'evals').glob('*.jsonl'))
if not files:
    errors.append('no eval jsonl files found')

for path in files:
    for i,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
        if not line.strip():
            continue
        count+=1
        try:
            obj=json.loads(line)
        except Exception as e:
            errors.append(f'{path.name}:{i} invalid JSON: {e}')
            continue
        missing=required-set(obj)
        if missing:
            errors.append(f'{path.name}:{i} missing {sorted(missing)}')
        case_id=obj.get('id')
        if case_id in seen:
            errors.append(f'duplicate eval id: {case_id}')
        seen.add(case_id)
        if not isinstance(obj.get('expected'), (str,list,dict)):
            errors.append(f'{path.name}:{i} expected has unsupported type')

if errors:
    print('\n'.join(errors))
    sys.exit(1)
print(f'Eval fixtures OK: {count} cases across {len(files)} files')
