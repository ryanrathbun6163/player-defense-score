"""Synthetic readout/storage tests: no real image features or model imports."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import subprocess
import tempfile
import unittest

import numpy as np

from src.ball_tracking import point_feature_inference as p


def produced_output():
    # The installed producer's final output interface is independently checked
    # by AST below. This synthetic sequence supplies controlled float32 values.
    sequence=np.arange(257*384,dtype=np.float32).reshape(1,257,384)/np.float32(1000)
    return SimpleNamespace(last_hidden_state=sequence,pooler_output=sequence[:,0,:])


def geometry(weights=(.1,.2,.3,.4)):
    return {'tokens':[{'sequence_index':int(i),'weight':w} for i,w in zip(p.TOKEN_INDICES,weights,strict=True)]}


class PointFeatureInferenceTests(unittest.TestCase):
    def test_module_and_metadata_source_inspection_do_not_import_Torch(self):
        script = (
            "import sys; from src.ball_tracking import point_feature_inference as p; "
            "library=p.ROOT/'.venv/Lib/site-packages/transformers/models/dinov2/modeling_dinov2.py'; "
            "p.row_major_evidence(library) if library.exists() else None; "
            "assert 'torch' not in sys.modules; print('no_torch_import')"
        )
        output = subprocess.check_output([sys.executable, '-B', '-c', script], cwd=p.ROOT, text=True)
        self.assertEqual(output.strip(), 'no_torch_import')

    def test_actual_config_required_guards_accept_explanatory_metadata(self):
        path=p.ROOT/p.CONFIG
        if not path.exists():self.skipTest('Prospective local configuration not present')
        config=p.read(path);p.validate_config(config)
        altered=deepcopy(config);altered['execution']['device']='cuda'
        with self.assertRaises(ValueError):p.validate_config(altered)
        altered=deepcopy(config);altered['CLS_parity']['before_HOU_inference']=False
        with self.assertRaises(ValueError):p.validate_config(altered)

    def test_installed_producer_patch_sequence_contract_without_import(self):
        location=p.ROOT/'.venv/Lib/site-packages/transformers/models/dinov2/modeling_dinov2.py'
        if not location.exists():self.skipTest('Pinned local runtime is not present')
        self.assertTrue(all(p.row_major_evidence(location).values()))
        # flatten(2).transpose(1,2) traverses width before height: token index
        # 1+16*y+x includes the prepended CLS; it is not column-major.
        grid=np.empty((1,384,16,16),np.float32)
        for y in range(16):
            for x in range(16):grid[0,:,y,x]=100*y+x
        flat=grid.reshape(1,384,-1).transpose(0,2,1)
        for index,y,x in ((120,7,7),(121,7,8),(136,8,7),(137,8,8)):
            np.testing.assert_array_equal(flat[0,index-1],np.full(384,100*y+x))

    def test_actual_output_interface_witnesses_and_input_preservation(self):
        output=produced_output();before=output.last_hidden_state.copy()
        witness=p.extract_witnesses(output)
        np.testing.assert_array_equal(witness['cls'],before[0,0])
        np.testing.assert_array_equal(witness['tokens'],before[0,[120,121,136,137]])
        np.testing.assert_array_equal(output.last_hidden_state,before)
        self.assertFalse(np.shares_memory(witness['tokens'],output.last_hidden_state))
        self.assertEqual(witness['sequence_sha256'],p.sha(before.tobytes()))
        for malformed in (SimpleNamespace(last_hidden_state=before[:,:256],pooler_output=before[:,0]),
                          SimpleNamespace(last_hidden_state=before.astype(np.float64),pooler_output=before[:,0]),
                          SimpleNamespace(last_hidden_state=before,pooler_output=before[:,1])):
            with self.assertRaises(ValueError):p.extract_witnesses(malformed)
        invalid=before.copy();invalid[0,5,8]=np.nan
        with self.assertRaises(ValueError):p.extract_witnesses(SimpleNamespace(last_hidden_state=invalid,pooler_output=invalid[:,0]))

    def test_raw_interpolation_then_one_L2_not_per_token_normalization(self):
        tokens=np.zeros((4,384),np.float32)
        tokens[0,0]=1;tokens[1,1]=10;tokens[2,2]=100;tokens[3,3]=1000
        raw,unit,reason=p.point_readout(tokens,geometry())
        expected=np.zeros(384);expected[:4]=[.1,2,30,400]
        np.testing.assert_array_equal(raw,expected)
        np.testing.assert_allclose(unit,expected/np.linalg.norm(expected),rtol=0,atol=1e-16)
        self.assertIsNone(reason)
        self.assertGreater(unit[3],.99)
        self.assertLess(unit[0],.001)
        changed=geometry();changed['tokens'][0]['sequence_index']=119
        with self.assertRaises(ValueError):p.point_readout(tokens,changed)

    def test_unknown_vectors_and_exact_historical_tolerance(self):
        raw,unit,reason=p.point_readout(np.zeros((4,384),np.float32),geometry())
        self.assertIsNone(unit);self.assertEqual(reason,'zero_norm_descriptor')
        original=np.ones(384,np.float32)
        near=original.copy();near[12]+=np.float32(1e-5)
        far=original.copy();far[12]+=np.float32(3e-5)
        self.assertTrue(p.cls_parity(near,original)['passed'])
        self.assertFalse(p.cls_parity(far,original)['passed'])
        self.assertEqual(p.normalize(np.full(384,np.nan))[1],'nonfinite_descriptor')

    def test_immutable_actual_witness_serialization_and_resume_validation(self):
        witness=p.extract_witnesses(produced_output())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'input.npz'
            p.save_npz(path,witness)
            with self.assertRaises(FileExistsError):p.save_npz(path,witness)
            item={'input_id':'synthetic'};config={'path':'synthetic-config'}
            record={'status':'completed','input':item,'config':config,'witness':p.bind(root,path),
                    'CLS_float32_sha256':p.sha(witness['cls'].tobytes()),'historical_CLS_parity':[{'passed':True}]}
            p.validate_cached(root,record,item,config)
            with np.load(path,allow_pickle=False) as actual:
                raw,unit,reason=p.point_readout(actual['tokens'],geometry())
            expected=sum(witness['tokens'][i].astype(np.float64)*w for i,w in enumerate((.1,.2,.3,.4)))
            np.testing.assert_allclose(raw,expected,rtol=0,atol=1e-13);self.assertIsNone(reason)
            broken=deepcopy(record);broken['historical_CLS_parity'][0]['passed']=False
            with self.assertRaises(ValueError):p.validate_cached(root,broken,item,config)
            path.write_bytes(path.read_bytes()+b'altered')
            with self.assertRaises(ValueError):p.validate_cached(root,record,item,config)

    def test_resumed_call_accounting_preserves_unreturned_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);paths=[]
            for index,rows in enumerate((
                [{'event':'model_load_start'},{'event':'model_load_complete'},
                 {'event':'forward_start','input_id':'a'},{'event':'forward_returned','input_id':'a'},
                 {'event':'input_sealed'},{'event':'forward_start','input_id':'b'}],
                [{'event':'forward_start','input_id':'b'},{'event':'forward_returned','input_id':'b'},
                 {'event':'input_sealed'}])):
                folder=root/str(index);folder.mkdir();path=folder/'events.jsonl'
                path.write_text(''.join(json.dumps(row)+'\n' for row in rows));paths.append(path)
            actual=p.aggregate_journals(paths)
            self.assertEqual(actual['forward_calls_attempted'],3)
            self.assertEqual(actual['forward_calls_returned'],2)
            self.assertEqual(actual['forward_starts_without_recorded_return'],1)
            self.assertEqual(actual['input_sealed'],2)


if __name__=='__main__':unittest.main()
