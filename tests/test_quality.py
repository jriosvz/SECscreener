from pathlib import Path
import sys
import unittest
import hashlib
import json
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from demo import load_tables,validate,procesar_extraido

class QualityTests(unittest.TestCase):
    def setUp(self): self.t=load_tables()
    def test_sample_byte_integrity(self):
        data=Path(__file__).resolve().parents[1]/'data'
        provenance=json.loads((data/'provenance.json').read_text())
        for name,entry in provenance['files'].items():
            self.assertEqual(hashlib.sha256((data/name).read_bytes()).hexdigest(),entry['sha256'])
    def checks(self): return {x['check'] for x in validate(self.t)}
    def test_real_sample(self): self.assertEqual(validate(self.t),[])
    def test_orphan(self):
        self.t['num'].loc[0,'adsh']='unknown';self.assertIn('orphan_accession',self.checks())
    def test_missing_tag_definition(self):
        self.t['tag']=self.t['tag'].iloc[0:0];self.assertIn('undefined_tag',self.checks())
    def test_duplicate_document(self):
        self.t['sub']=pd.concat([self.t['sub']]*2);self.assertIn('duplicate_key',self.checks())
    def test_conflicting_fact(self):
        extra=self.t['num'].iloc[[0]].copy();extra['value']='123456789'
        self.t['num']=pd.concat([self.t['num'],extra]);self.assertIn('conflicting_values',self.checks())
    def test_invalid_number(self):
        for bad in ['broken','NaN','inf','-inf']:
            with self.subTest(value=bad):
                self.t['num'].loc[0,'value']=bad;self.assertIn('invalid_numeric_value',self.checks())
    def test_duplicate_fact(self):
        self.t['num']=pd.concat([self.t['num'],self.t['num'].iloc[[0]]]);self.assertIn('duplicate_row',self.checks())
    def test_missing_schema(self):
        self.t['num']=self.t['num'].drop(columns='value');self.assertIn('missing_columns',self.checks())
    def test_missing_assets_stays_missing(self):
        self.t['num']=self.t['num'].loc[self.t['num'].tag.ne('AssetsCurrent')]
        result=procesar_extraido(self.t,320193)
        self.assertTrue(pd.isna(result.tabla.iloc[0].activos_corrientes))
        self.assertTrue(pd.isna(result.tabla.iloc[0].ncav))
    def test_context_is_not_mixed(self):
        baseline=procesar_extraido(self.t,320193).tabla.iloc[0].activos_totales
        extra=self.t['num'].loc[self.t['num'].tag.eq('Assets')].copy()
        extra['uom']='EUR';extra['value']='1'
        self.t['num']=pd.concat([self.t['num'],extra])
        self.assertEqual(procesar_extraido(self.t,320193).tabla.iloc[0].activos_totales,baseline)

if __name__=='__main__': unittest.main()
