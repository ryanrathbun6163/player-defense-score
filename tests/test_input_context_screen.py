"""Scientific geometry and unchanged-input checks; no model imports."""
import numpy as np
import unittest
from PIL import Image

from src.ball_tracking.input_context_screen import geometry, paired_inputs
from src.ball_tracking.candidate_quality_model import point_geometry


def test_fractional_candidate_stays_same_point_across_views():
    xy=[100.875,77.125]
    assert geometry(xy,192)==[4,-19,196,173]
    assert point_geometry(xy,256,192)['crop_box']==[68,45,132,109]
    # Wider crop uses candidate position, never an accepted reference center.
    wide=geometry(xy,192)
    mapped=[(xy[j]-wide[j]+.5)*224/192-.5 for j in (0,1)]
    assert np.allclose(mapped,[113.10416666666667,112.22916666666667])


def test_local_pixels_are_old_pipeline_even_with_wider_padding():
    rng=np.random.default_rng(17)
    image=Image.fromarray(rng.integers(0,256,(80,90,3),dtype=np.uint8))
    for xy in ([.2,.9],[89.9,79.1],[40.75,39.4]):
        raw,local,chw,wide,box=paired_inputs(image,xy)
        original=image.crop(geometry(xy,64))
        expected=original.resize((256,256),Image.Resampling.BICUBIC).crop((16,16,240,240))
        assert np.array_equal(np.asarray(raw),np.asarray(original))
        assert np.array_equal(np.asarray(local),np.asarray(expected))
        assert wide.size==(224,224) and chw.shape==(3,224,224)
        assert box==geometry(xy,192)
        # PIL's off-source padding must be black, not a clamped/shifted crop.
        assert tuple(np.asarray(image.crop(box))[0,0])==(0,0,0)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(test) for test in (
        test_fractional_candidate_stays_same_point_across_views,
        test_local_pixels_are_old_pipeline_even_with_wider_padding))
