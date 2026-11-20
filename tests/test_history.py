import importlib.util
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

ROOT=Path(__file__).resolve().parents[1]
def module(n,p):
    s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=module('history',ROOT/'skills/vem-t1-matrix-history/scripts/history.py')
installer=module('installer',ROOT/'install.py')
LEDGER=ROOT/'catalog/history.jsonl'

class HistoryTest(unittest.TestCase):
    def test_real_source_conditions(self):
        h.act('check',LEDGER)
        b=h.validate(h.read_rows(LEDGER))
        def pair(i):
            c=b[i];return b[c['parent']],b[c['child']]
        x,y=pair('C06')
        self.assertEqual(h.diff(x['total'],y['total']),h.dec('.51'))
        self.assertEqual([float(h.diff(x['metrics'][k],y['metrics'][k])) for k in h.KEYS],[-1.1,-.7,2.3,1.2])
        self.assertEqual(b['C13-1.5']['child'],b['C14-225']['parent'])
        self.assertNotEqual(b['C13-1.5']['parent'],b['C14-225']['parent'])
        for case,expected in [('native',.0513),('cm',.0025),('endo',.0588)]:
            a,z=pair('C26-'+case)
            self.assertEqual((a['channel'],z['channel']),('local','local'))
            self.assertAlmostEqual(z['total']-a['total'],expected,places=4)
        self.assertNotEqual(b['C17']['child'],b['C17-repeat']['child'])
        self.assertEqual(b[b['C17-repeat']['child']]['file'],b[b['C17']['child']]['file'])
        self.assertIsNone(b['C02']['parent'])
        for basis in ('included','unpaired'):
            bad=dict(b['C06'],id='uncertain-ablation',basis=basis)
            with self.assertRaisesRegex(ValueError,'parent'):h.validate(list(b.values())+[bad])

    def test_new_direction_batch_and_failed_update(self):
        with TemporaryDirectory() as folder:
            p=Path(folder); ledger=p/'history.jsonl';shutil.copyfile(LEDGER,ledger)
            before=ledger.read_bytes()
            batch=p/'batch.jsonl'
            def run(i,status,**values):
                return dict(kind='run',id=i,label=i,channel='development',protocol='example',status=status,
                            sources=['source:smoke-only'],**values)
            def comparison(i,target):
                return dict(kind='comparison',id=i,direction='D13',child=target,parent=None,basis='unpaired',
                            change='测试组别',data='合成验收，不是实验结果',sources=['source:smoke-only'])
            new=[dict(kind='direction',id='D13',title='临时验收新方向',example='清单外'),
                 run('ex-notrun','not_run'),run('ex-failed','failed'),run('ex-unchanged','identical',same_as='ex-failed-anchor'),
                 run('ex-failed-anchor','candidate'),run('ex-no-score','score_missing')]
            new.extend(comparison('try-'+x,x) for x in ['ex-notrun','ex-failed','ex-unchanged','ex-no-score'])
            batch.write_bytes(h.encode(new))
            self.assertEqual(h.act('append',ledger,batch=batch)['direction'],13)
            self.assertTrue(ledger.read_bytes().startswith(before))
            ok=ledger.read_bytes();view=ledger.with_name('DIRECTIONS.md');okview=view.read_bytes()
            self.assertIn('临时验收新方向',okview.decode())
            self.assertIn('预测相同',okview.decode())
            with self.assertRaises(ValueError):h.act('append',ledger,batch=batch)
            pair=dict(comparison('bad','ex-no-score'),parent='R001',basis='paired')
            batch.write_bytes(h.encode([pair]))
            with self.assertRaises(ValueError):h.act('append',ledger,batch=batch)
            self.assertEqual(ledger.read_bytes(),ok); self.assertEqual(view.read_bytes(),okview)
            h.act('check',ledger)
            view.write_bytes(b'out of date')
            with self.assertRaises(ValueError): h.act('check',ledger)
            h.act('render',ledger); h.act('check',ledger)
    def test_portable_install_cannot_clobber(self):
        with TemporaryDirectory() as folder:
            d=Path(folder);installer.install(['codex','claude'],'project',d,True)
            a=d/'.agents/skills'/installer.NAME/'SKILL.md';b=d/'.claude/skills'/installer.NAME/'SKILL.md'
            self.assertEqual(a.read_bytes(),b.read_bytes())
            installer.install(['codex','claude'],'project',d,True)
            target=d/'catalog/history.jsonl';target.write_bytes(b'other team data')
            with self.assertRaises(ValueError): installer.install(['codex','claude'],'project',d,True)
            self.assertEqual(target.read_bytes(),b'other team data')
if __name__=='__main__':unittest.main()
