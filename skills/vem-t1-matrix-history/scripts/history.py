"""Maintain an append-only VEM T1 experiment ledger; never score a prediction."""
import argparse
from contextlib import contextmanager
from decimal import Decimal
import json
import math
import os
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
from urllib.parse import quote, urlsplit

KEYS = ('de_score', 'de_direction', 'mmd_u', 'variogram')
STATUS = {'scored':'有分', 'score_missing':'缺回执或分数', 'candidate':'仅有文件', 'failed':'执行失败',
          'not_run':'未执行', 'identical':'预测相同', 'unknown':'状态未确定'}
BASIS = {'paired':'同底稿', 'combination':'多项合改', 'family':'同族不同设置', 'included':'已包含、无单项增益', 'unpaired':'无可比父件'}
CHANNEL = {'official':'官网', 'local':'本地回放', 'artifact':'文件', 'development':'开发记录'}

def fail(msg):
    raise ValueError(msg)

def read_rows(path):
    rows = []
    for n, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.strip(): continue
        try: rows.append(json.loads(line))
        except ValueError as e: fail(f'{path}:{n}: {e}')
    return rows

def validate(rows):
    by = {}
    for row in rows:
        if not isinstance(row, dict): fail('记录必须是 JSON 对象')
        ident = row.get('id', '')
        if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*', ident) or ident in by:
            fail(f'无效或重复 ID: {ident}')
        by[ident] = row
        k = row.get('kind')
        required = {'direction': ['title','example'], 'run':['channel','protocol','status','label','sources'],
                    'comparison':['direction','child','basis','change','data','sources'], 'snapshot':['text']}
        if k not in required: fail(f'{ident}: 未知记录类型')
        for field in required[k]:
            if not row.get(field): fail(f'{ident}: 缺 {field}')
        if k in ('run','comparison'):
            if not isinstance(row['sources'],list) or not all(isinstance(s,str) and s for s in row['sources']):
                fail(f'{ident}: 来源必须是非空字符串列表')
        if k == 'run':
            if row['status'] not in STATUS or row['channel'] not in CHANNEL: fail(f'{ident}: 未知状态或来源')
            t, m = row.get('total'), row.get('metrics') or {}
            def number(x): return type(x) in (float,int) and math.isfinite(x)
            if t is not None and not number(t): fail(f'{ident}: 总分无效')
            if not isinstance(m,dict) or set(m)-set(KEYS) or not all(v is None or number(v) for v in m.values()):
                fail(f'{ident}: 分项无效')
            if row['status']=='scored' and t is None: fail(f'{ident}: 有分记录缺少总分')
            if row['status']!='scored' and (t is not None or any(v is not None for v in m.values())):
                fail(f'{ident}: 无评分状态不可填分；实测同矩阵另加 scored 行')
            if any(v is not None for v in m.values()) and row.get('units') not in ('skill100','raw'):
                fail(f'{ident}: 必须注明分项尺度')
    for r in rows:
        if r.get('status')=='identical':
            anchor=by.get(r.get('same_as'))
            if not anchor or anchor is r or anchor.get('kind')!='run': fail('同矩阵记录必须指向另一条 run 并给出校验来源')
        if r['kind']!='comparison': continue
        def ref(key, kind):
            val=by.get(r.get(key))
            if not val or val['kind']!=kind: fail(f"{r['id']}: {key} 引用无效")
            return val
        ref('direction','direction')
        y=ref('child','run')
        if r['basis'] not in BASIS: fail(f"{r['id']}: 未知比较类型")
        if r.get('parent'):
            if r['basis'] in ('included','unpaired'): fail(f"{r['id']}: 无可比父件的记录不能填写 parent 或计算分项增益")
            x=ref('parent','run')
            if x is y or (x['channel'],x['protocol'])!=(y['channel'],y['protocol']):
                fail(f"{r['id']}: 不可在不同来源或协议之间算差")
            if x.get('metrics') and y.get('metrics') and x.get('units')!=y.get('units'): fail('分项尺度不同')
        elif r['basis'] not in ('included','unpaired'): fail(f"{r['id']}: 此类比较需要父件")
    return by

def dec(x): return Decimal(str(x))
def fmt(x, places, signed=False):
    if x is None: return '—'
    return f'{dec(x):+.{places}f}' if signed else f'{dec(x):.{places}f}'
def diff(a,b):
    return None if a is None or b is None else dec(b)-dec(a)
def esc(v):
    return str(v).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('|','\\|').replace('\n',' ')

def evidence(src, out_dir, project):
    # The portable edition keeps stable evidence keys, not broken links to a private checkout.
    if src.startswith('source:'): return esc(src)
    if src.startswith('https://') and urlsplit(src).netloc:
        return '[公开证据]('+quote(src,safe='/:#?&=%.-_')+')'
    path,_,locator=src.partition('#')
    if Path(path).is_absolute() or '..' in Path(path).parts or path.replace('\\','/').casefold().startswith('isolated_analyses/'):
        fail('常规方向表只接受项目内非隔离证据或公开链接：'+path)
    if project is None: return esc(src)
    p = (project/path).resolve()
    if not p.is_relative_to(project.resolve()) or not p.is_file(): fail('找不到项目内证据：'+path)
    rel = os.path.relpath(p,out_dir).replace(os.sep,'/')
    return '['+esc(p.name)+']('+quote(rel,safe='/.-_')+')'+(' '+esc(locator) if locator else '')

def render(rows, dest, project=None):
    by=validate(rows)
    ds=[r for r in rows if r['kind']=='direction']; cs=[r for r in rows if r['kind']=='comparison']
    runs=[r for r in rows if r['kind']=='run']
    def stats(c):
        y=by[c['child']]; x=by.get(c.get('parent'),{}); places=2 if y['channel']=='official' else 4
        return y,x,places,diff(x.get('total'),y.get('total'))
    def result(c):
        y,x,n,d=stats(c)
        if y['status']!='scored': return STATUS[y['status']]
        start=fmt(x.get('total'),n)+' → ' if x.get('total') is not None else ''
        return start+fmt(y.get('total'),n)+(' ('+fmt(d,n,True)+')' if d is not None else '（无单项差值）')
    def axis(c):
        y,x,_,_=stats(c)
        m=x.get('metrics') or {}; t=y.get('metrics') or {}
        if not m or not t: return '—'
        n=1 if y['channel']=='official' else (6 if y['units']=='raw' else 4)
        return ' / '.join(fmt(diff(m.get(k),t.get(k)),n,True) for k in KEYS)
    def mode(y):
        return CHANNEL[y['channel']]+('·原始量' if y.get('units')=='raw' else '')
    def link(s): return evidence(s,dest.parent,project)
    for s in {s for r in rows for s in r.get('sources',[])}: link(s)
    head=['# VEM T1｜细胞 × 基因表达矩阵预测：方向清单','',
          '每个方向保留涨、跌和缺分结果。右列只是例子；可新增方向，排列次序不代表优先级。',
          '分项顺序：**DE / 方向 / MMD / 基因对差异**。官网为 T1 E10.5 验证榜显示分；按各自显示精度相减。非官网结果单列，不能视为 E12.5 成绩。',
          '原始距离与 0–100 分项分开。— 表示缺项或无可比父件，不是零。','',
          '[机器可读明细](history.jsonl) · [未配对记录](#inventory)','']
    head += [r['text']+'\n' for r in rows if r['kind']=='snapshot']
    head += ['| 方向 | 历史做法和总分（父 → 子） | 对应四项变化（与左列逐行对应） | 还可怎样试（举例） |','|---|---|---|---|']
    for d in ds:
        group=[c for c in cs if c['direction']==d['id']]
        shown=[c for c in group if c.get('featured', True)]
        brief='<br>'.join(f"{mode(by[c['child']])}：{esc(c.get('short',c['change']))} {result(c)}" for c in shown)
        deltas='<br>'.join(axis(c) for c in shown) or '—'
        head.append(f"| [{esc(d['title'])}](#dir-{d['id'].lower()}) | {brief or '尚无展示案例，见明细'} | {deltas} | {esc(d['example'])} |")
    for d in ds:
        head+=['',f'<a id="dir-{d["id"].lower()}"></a>',f"## {d['id']} · {d['title']}",'']
        for c in (s for s in cs if s['direction']==d['id']):
            y,x,_,_=stats(c)
            head+=['- **'+esc(c['change'])+'**　'+mode(y)+' '+result(c)+'；四项差：'+axis(c)+'。']
            names=(x.get('file') or x.get('label') or '无单独父件')+' → '+(y.get('file') or y['label'])
            head+=['  '+esc(names)+'；'+esc(y['protocol'])+'。<br>',
                   '  '+esc(c['data'])+'；'+BASIS[c['basis']]+('。'+esc(c['note']) if c.get('note') else '。')+'<br>']
            sources=list(dict.fromkeys(c['sources']+y['sources'][:1]+x.get('sources',[])[:1]))
            head+=['  '+' · '.join(link(s) for s in sources)+'　('+c['id']+')','']
    used={c[key] for c in cs for key in ('parent','child') if c.get(key)}
    head+=['','<a id="inventory"></a>','## 未配对记录与身份缺口','',
          '下列记录不冒认直接父件；包含同名、多次上传、候选和部分只有总分的早期记录。各分项及原来源见同 ID 的明细。','',
          '| 记录 | 来源 / 状态 | 预测名称 | 总分 |','|---|---|---|---:|']
    for r in runs:
        if r['id'] not in used:
            head.append(f"| {r['id']} | {mode(r)} / {STATUS[r['status']]} | {esc(r.get('file') or r['label'])} | {fmt(r.get('total'),2 if r['channel']=='official' else 4)} |")
    return ('\n'.join(head).rstrip()+'\n').encode('utf8')

def encode(rows):
    return ''.join(json.dumps(r,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n' for r in rows).encode()
def write(path, content):
    with NamedTemporaryFile(dir=path.parent,delete=False) as f:
        name=f.name
        try: f.write(content); f.flush(); os.fsync(f.fileno())
        except BaseException:
            f.close(); Path(name).unlink(missing_ok=True); raise
    try: os.replace(name, path)
    finally: Path(name).unlink(missing_ok=True)

@contextmanager
def lock(folder):
    p=folder/'.history-write.lock'
    try: h=p.open('x')
    except FileExistsError: fail('另一写者持锁；若异常中止请先确认写者已退出')
    try:
        with h: h.write(str(os.getpid()))
        yield
    finally: p.unlink()

def act(op,ledger,project=None,batch=None):
    if ledger.name!='history.jsonl': fail('指定目录中的 history.jsonl')
    dest=ledger.with_name('DIRECTIONS.md')
    def handle():
        rows=read_rows(ledger)
        if op=='append':
            new=read_rows(batch)
            if not new: fail('追加内容为空')
            rows+=new
        view=render(rows,dest,project)
        if op=='check':
            if not dest.exists() or dest.read_bytes()!=view: fail('方向表过期，请先 render')
        else:
            if op=='append':
                old=ledger.read_bytes()
                write(ledger,old+(b'\n' if old and not old.endswith(b'\n') else b'')+encode(new))
            write(dest,view)
        return {k:sum(r['kind']==k for r in rows) for k in ('direction','run','comparison')}
    if op=='check': return handle()
    with lock(ledger.parent): return handle()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['render','check','append'])
    p.add_argument('--ledger',type=Path,required=True)
    p.add_argument('--project',type=Path,help='VEM 项目根目录；本地证据转可点链接')
    p.add_argument('--batch',type=Path,help='要追加的 JSONL；不就地修订历史')
    a=p.parse_args()
    if (a.action=='append') != bool(a.batch): p.error('仅 append 需要 --batch')
    try: print(json.dumps(act(a.action,a.ledger.resolve(),a.project.resolve() if a.project else None,a.batch)))
    except (OSError,ValueError,KeyError,TypeError) as e: sys.exit(str(e))
if __name__=='__main__': main()
