"""Install one identical skill for Codex and/or Claude Code, using only Python."""
import argparse
from pathlib import Path
import os
import shutil
import sys

NAME='vem-t1-matrix-history'
HERE=Path(__file__).resolve().parent
FILES=('SKILL.md','agents/openai.yaml','scripts/history.py','references/ledger.md')
def install(clients, scope, project, with_catalog=False):
    if scope=='user':
        targets={'codex':Path(os.getenv('CODEX_HOME') or (Path.home()/'.codex'))/'skills',
                 'claude':Path(os.getenv('CLAUDE_CONFIG_DIR') or (Path.home()/'.claude'))/'skills'}
    else: targets={'codex':project/'.agents/skills','claude':project/'.claude/skills'}
    pairs=[(HERE/'skills'/NAME/f, targets[c]/NAME/f) for c in clients for f in FILES]
    if with_catalog:
        pairs.extend((HERE/'catalog'/f,project/'catalog'/f) for f in ('history.jsonl','DIRECTIONS.md'))
    # Check all destinations first. Never replace another skill or an evolved project ledger.
    for src,dst in pairs:
        if dst.exists() and (not dst.is_file() or dst.read_bytes()!=src.read_bytes()):
            raise ValueError(f'目标已有不同内容，未覆盖：{dst}。请先比对；更新 skill 不需要重装项目清单。')
    for src,dst in pairs:
        if not dst.exists():
            dst.parent.mkdir(parents=True,exist_ok=True)
            with src.open('rb') as inp,dst.open('xb') as out: shutil.copyfileobj(inp,out)
    for c in clients: print(c,targets[c]/NAME)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--client',choices=['codex','claude','both'],default='both')
    p.add_argument('--scope',choices=['user','project'],default='user');p.add_argument('--project',type=Path,default=Path.cwd())
    p.add_argument('--with-catalog',action='store_true',help='将初始公开清单复制到目标项目 catalog，不覆盖已有历史')
    a=p.parse_args()
    try: install(('codex','claude') if a.client=='both' else (a.client,),a.scope,a.project.resolve(),a.with_catalog)
    except (OSError,ValueError) as e: sys.exit(str(e))
