import pytest
import numpy as np
import os
import unittest
from unittest.mock import MagicMock, PropertyMock, patch, call
import spiceypy as spice
import json

import ale
from ale import util
from ale.drivers import AleJsonEncoder
from ale.drivers.kplo_drivers import KploShadowCamPds3LabelNaifSpiceDriver
from ale.drivers.kplo_drivers import KploShadowCamIsisLabelNaifSpiceDriver
from ale.drivers.kplo_drivers import LroLrocWacIsisLabelNaifSpiceDriver
from ale.drivers.kplo_drivers import LroLrocWacIsisLabelIsisSpiceDriver
from ale.drivers.kplo_drivers import LroMiniRfIsisLabelNaifSpiceDriver
from ale.base.data_naif import NaifSpice
from ale.transformation import TimeDependentRotation

from conftest import get_image, get_image_label, get_isd, get_image_kernels, convert_kernels, compare_dicts

image_dict = {
    'M017663765SE': get_isd("ShadowCam"),
    #'03821_16N196_S1': get_isd("lrominirf"),
    #'wac0000a1c4.uv.even': get_isd('lrokplowac')-JP
}

# LROC test kernels
@pytest.fixture(scope="module")
def test_kernels():
    updated_kernels = {}
    binary_kernels = {}
    for image in image_dict.keys():
        kernels = get_image_kernels(image)
        updated_kernels[image], binary_kernels[image] = convert_kernels(kernels)
    yield updated_kernels
    for kern_list in binary_kernels.values():
        for kern in kern_list:
            os.remove(kern)

# Test load of LROC labels
@pytest.mark.parametrize("label_type, kernel_type", [('isis3', 'naif'), ('isis3', 'isis')])
#@pytest.mark.parametrize("image", image_dict.keys()) Add this when when all are supported by ale isd.
@pytest.mark.parametrize("image", ['M017663765SE'])
def test_load_kplo_nac(test_kernels, label_type, image, kernel_type):
    if kernel_type == 'naif':
        label_file = get_image_label(image, label_type)
        isd_str = ale.loads(label_file, props={'kernels': test_kernels[image]}, verbose=False)
        compare_isd = image_dict[image]
    else:
        label_file = get_image(image)
        isd_str = ale.loads(label_file)
        #compare_isd = get_isd('lro_isis')
        compare_isd = get_isd('kplo_isis')
        
    print(isd_str)
    isd_obj = json.loads(isd_str)
    comparison = compare_dicts(isd_obj, compare_isd)
    assert comparison == []

# Test load of LROC labels
@pytest.mark.parametrize("label_type, kernel_type", [('isis3', 'naif')])
#@pytest.mark.parametrize("image", image_dict.keys()) Add this when when all are supported by ale isd.
#@pytest.mark.parametrize("image", ['wac0000a1c4.uv.even'])
def test_load_kplo_wac(test_kernels, label_type, image, kernel_type):
    label_file = get_image_label(image, label_type)
    isd_str = ale.loads(label_file, props={'kernels': test_kernels[image]})
    compare_isd = image_dict[image]
    isd_obj = json.loads(isd_str)
    print(json.dumps(isd_obj))
    comparison = compare_dicts(isd_obj, compare_isd)
    assert comparison == []


# Test load of MiniRF labels
#def test_load_minirf(test_kernels):
#    label_file = get_image_label('03821_16N196_S1', 'isis3')
#    isd_str = ale.loads(label_file, props={'kernels': test_kernels['03821_16N196_S1']})
#    isd_obj = json.loads(isd_str)
#    comparison = compare_dicts(isd_obj, image_dict['03821_16N196_S1'])
#   assert comparison == []

# ========= Test pdslabel and naifspice driver =========
class test_pds_naif(unittest.TestCase):

    def setUp(self):
        label = get_image_label('M017663765SE', 'pds3')
        self.driver = KploShadowCamPds3LabelNaifSpiceDriver(label)

    def test_short_mission_name(self):
        #assert self.driver.short_mission_name=='lro'
        assert self.driver.short_mission_name=='kplo'

    def test_instrument_id(self)
        self.driver.label = 'ShadowCam'
    #def test_instrument_id_left(self):
    #    self.driver.label['FRAME_ID'] = 'LEFT'
    #    assert self.driver.instrument_id == 'ShadowCam'

    #def test_instrument_id_right(self):
    #    self.driver.label['FRAME_ID'] = 'RIGHT'
    #    assert self.driver.instrument_id == 'LRO_LROCNACR'
#########JP

#    def test_spacecraft_name(self):
#        assert self.driver.spacecraft_name == 'LRO'
    def test_spacecraft_name(self):
        assert self.driver.spacecraft_name == 'KPLO'

    def test_sensor_model_version(self):
        assert self.driver.sensor_model_version == 2

    def test_odtk(self):
        with patch('ale.spiceql_access.spiceql_call', side_effect=[-12345]) as spiceql_call, \
             patch('ale.drivers.kplo_drivers.KploShadowCamPds3LabelNaifSpiceDriver.naif_keywords', new_callable=PropertyMock) as naif_keywords:
            naif_keywords.return_value = {"INS-12345_OD_K": [1.0]}
            assert self.driver.odtk == [1.0]
            calls = [call('translateNameToCode', {'frame': 'ShadowCam', 'mission': 'ShadowCam', 'searchKernels': False}, False)]
            #calls = [call('translateNameToCode', {'frame': 'ShadowCam', 'mission': 'kplo', 'searchKernels': False}, False)]
            spiceql_call.assert_has_calls(calls)
            assert spiceql_call.call_count == 1
#######JP
    def test_usgscsm_distortion_model(self):
        with patch('ale.drivers.kplo_drivers.KploShadowCamNacPds3LabelNaifSpiceDriver.odtk', \
                   new_callable=PropertyMock) as odtk:
            odtk.return_value = [1.0]
            distortion_model = self.driver.usgscsm_distortion_model
            assert distortion_model['ShadowCam']['coefficients'] == [1.0]

    def test_ephemeris_start_time(self):
        with patch('ale.spiceql_access.spiceql_call', side_effect=[5]) as spiceql_call, \
             patch('ale.drivers.kplo_drivers.KploShadowCamPds3LabelNaifSpiceDriver.exposure_duration', \
                   new_callable=PropertyMock) as exposure_duration, \
             patch('ale.drivers.kplo_drivers.KploShadowCam3LabelNaifSpiceDriver.spacecraft_id', \
                   new_callable=PropertyMock) as spacecraft_id:
            exposure_duration.return_value = 0.1
            spacecraft_id.return_value = 1234
            assert self.driver.ephemeris_start_time == 107.4
            calls = [call('strSclkToEt', {'frameCode': 1234, 'sclk': '1/270649237:07208', 'mission': 'kplo', 'searchKernels': False}, False)]
            spiceql_call.assert_has_calls(calls)
            assert spiceql_call.call_count == 1

    def test_exposure_duration(self):
        with patch('ale.base.label_pds3.Pds3Label.exposure_duration', \
                   new_callable=PropertyMock) as exposure_duration:
            exposure_duration.return_value = 1
            assert self.driver.exposure_duration == 1.0045
######### ? -JP^^^^^^^^^


    @patch('ale.transformation.FrameChain')
    @patch('ale.transformation.FrameChain.from_spice', return_value=ale.transformation.FrameChain())
    @patch('ale.transformation.FrameChain.compute_rotation', return_value=TimeDependentRotation([[0, 0, 1, 0]], [0], 0, 0))
    def test_spacecraft_direction(self, compute_rotation, from_spice, frame_chain):
        with patch('ale.spiceql_access.spiceql_call', side_effect=[-12345, -12345, [[1, 1, 1, 1, 1, 1, 1]]]) as spiceql_call, \
             patch('ale.drivers.kplo_drivers.spice.mxv', return_value=[1, 1, 1]) as mxv, \
             patch('ale.drivers.kplo_drivers.KploShadowCamPds3LabelNaifSpiceDriver.target_frame_id', \
             new_callable=PropertyMock) as target_frame_id, \
             patch('ale.drivers.kplo_drivers.KploShadowCamPds3LabelNaifSpiceDriver.ephemeris_start_time', \
             new_callable=PropertyMock) as ephemeris_start_time:
            ephemeris_start_time.return_value = 0
            assert self.driver.spacecraft_direction > 0
            calls = [call('translateNameToCode', {'frame': 'ShadowCam', 'mission': 'kplo', 'searchKernels': False}, False),
                     call('translateNameToCode', {'frame': 'ShadowCam', 'mission': 'kplo', 'searchKernels': False}, False),
                     call('getTargetStates', {'ets': [0], 'target': 'LRO', 'observer': 'MOON', 'frame': 'J2000', 'abcorr': 'None', 'mission': 'kplo', 'searchKernels': False}, False)]
            spiceql_call.assert_has_calls(calls)
            assert spiceql_call.call_count == 3
            compute_rotation.assert_called_with(1, -12345)
            np.testing.assert_array_equal(np.array([[-1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0]]), mxv.call_args[0][0])
            np.testing.assert_array_equal(np.array([1, 1, 1]), mxv.call_args[0][1])

    def test_focal2pixel_lines(self):
        with patch('ale.drivers..KploShadowCamPds3LabelNaifSpiceDriver.naif_keywords', new_callable=PropertyMock) as naif_keywords, \
             patch('ale.spiceql_access.spiceql_call', side_effect=[-12345, 321]) as spiceql_call, \
             patch('ale.drivers.kplo_drivers.KploShadowCamPds3LabelNaifSpiceDriver.spacecraft_direction', \
             new_callable=PropertyMock) as spacecraft_direction:
            naif_keywords.return_value = {"INS-12345_ITRANSL": [0, 1, 0]}
            spacecraft_direction.return_value = -1
            np.testing.assert_array_equal(self.driver.focal2pixel_lines, [0, -1, 0])
            spacecraft_direction.return_value = 1
            np.testing.assert_array_equal(self.driver.focal2pixel_lines, [0, 1, 0])
            calls = [call('translateNameToCode', {'frame': 'ShadowCam', 'mission': 'kplo', 'searchKernels': False}, False)]
            spiceql_call.assert_has_calls(calls)
            assert spiceql_call.call_count == 1


# ========= Test isislabel and naifspice driver =========
class test_isis_naif(unittest.TestCase):

    def setUp(self):
        label = get_image_label('M017663765SE', 'isis3')
        self.driver = KploShadowCamIsisLabelNaifSpiceDriver(label)

    def test_short_mission_name(self):
        #assert self.driver.short_mission_name == 'lro'
        assert self.driver.short_mission_name == 'kplo'

    def test_instrument_id(self):
        assert self.driver.instrument_id == 'ShadowCam'

    def test_usgscsm_distortion_model(self):
        with patch('ale.spiceql_access.spiceql_call', side_effect=[-12345]) as spiceql_call, \
             patch('ale.drivers.kplo_drivers.KploShadowCamIsisLabelNaifSpiceDriver.naif_keywords', new_callable=PropertyMock) as naif_keywords:
            naif_keywords.return_value = {"INS-12345_OD_K": [1.0]}
            distortion_model = self.driver.usgscsm_distortion_model
            assert distortion_model['ShadowCam']['coefficients'] == [1.0]
            calls = [call('translateNameToCode', {'frame': 'ShadowCam', 'mission': 'kplo', 'searchKernels': False}, False)]
            spiceql_call.assert_has_calls(calls)
            assert spiceql_call.call_count == 1

    def test_odtk(self):
        with patch('ale.spiceql_access.spiceql_call', side_effect=[-12345]) as spiceql_call, \
             patch('ale.drivers.kplo_drivers.KploShadowCamIsisLabelNaifSpiceDriver.naif_keywords', new_callable=PropertyMock) as naif_keywords:
            naif_keywords.return_value = {"INS-12345_OD_K": [1.0]}
            assert self.driver.odtk == [1.0]
            calls = [call('translateNameToCode', {'frame': 'ShadowCam', 'mission': 'kplo', 'searchKernels': False}, False)]
            spiceql_call.assert_has_calls(calls)
            assert spiceql_call.call_count == 1

    def test_light_time_correction(self):
        assert self.driver.light_time_correction == 'NONE'

    def test_detector_center_sample(self):
        with patch('ale.spiceql_access.spiceql_call', side_effect=[-12345, 321]) as spiceql_call, \
             patch('ale.drivers.kplo_drivers.KploShadowCamIsisLabelNaifSpiceDriver.naif_keywords', new_callable=PropertyMock) as naif_keywords:
            naif_keywords.return_value = {"INS-12345_BORESIGHT_SAMPLE": 1.0}
            assert self.driver.detector_center_sample == 0.5
            calls = [call('translateNameToCode', {'frame': 'ShadowCam', 'mission': 'kplo', 'searchKernels': False}, False)]
            spiceql_call.assert_has_calls(calls)
            assert spiceql_call.call_count == 1

    def test_exposure_duration(self):
        np.testing.assert_almost_equal(self.driver.exposure_duration, .0010334296)

    #Group of numerical stats I have not a clue about -JP
    def test_ephemeris_start_time(self):
        with patch('ale.spiceql_access.spiceql_call', side_effect=[-85, 321]) as spiceql_call:
            np.testing.assert_almost_equal(self.driver.ephemeris_start_time, 322.05823191)
            calls = [call('translateNameToCode', {'frame': 'KOREAN PATHFINDER LUNAR ORBITER', 'mission': 'kplo', 'searchKernels': False}, False),
                     call('strSclkToEt', {'frameCode': -85, 'sclk': '1/270649237:07208', 'mission': 'kplo', 'searchKernels': False}, False)]
            spiceql_call.assert_has_calls(calls)
            assert spiceql_call.call_count == 2

    def test_multiplicative_line_error(self):
        assert self.driver.multiplicative_line_error == 0.0045

    def test_additive_line_error(self):
        assert self.driver.additive_line_error == 0

    def test_constant_time_offset(self):
        assert self.driver.constant_time_offset == 0

    def test_additional_preroll(self):
        assert self.driver.additional_preroll == 1024

    def test_sampling_factor(self):
        assert self.driver.sampling_factor == 1

    @patch('ale.transformation.FrameChain')
    @patch('ale.transformation.FrameChain.from_spice', return_value=ale.transformation.FrameChain())
    @patch('ale.transformation.FrameChain.compute_rotation', return_value=TimeDependentRotation([[0, 0, 1, 0]], [0], 0, 0))
    def test_spacecraft_direction(self, compute_rotation, from_spice, frame_chain):
        with patch('ale.spiceql_access.spiceql_call', side_effect=[-12345, -12345, [[1, 1, 1, 1, 1, 1, 1]]]) as spiceql_call, \
             patch('ale.drivers.kplo_drivers.spice.mxv', return_value=[1, 1, 1]) as mxv, \
             patch('ale.drivers.kplo_drivers.KploShadowCamIsisLabelNaifSpiceDriver.target_frame_id', \
             new_callable=PropertyMock) as target_frame_id, \
             patch('ale.drivers.kplo_drivers.KploShadowCamIsisLabelNaifSpiceDriver.ephemeris_start_time', \
             new_callable=PropertyMock) as ephemeris_start_time:
            ephemeris_start_time.return_value = 0
            assert self.driver.spacecraft_direction > 0
            calls = [call('translateNameToCode', {'frame': 'ShadowCam', 'mission': 'kplo', 'searchKernels': False}, False),
                     call('translateNameToCode', {'frame': 'ShadowCam', 'mission': 'kplo', 'searchKernels': False}, False),
                     call('getTargetStates', {'ets': [0], 'target': 'KOREAN PATHFINDER LUNAR ORBITER', 'observer': 'MOON', 'frame': 'J2000', 'abcorr': 'None', 'mission': 'kplo', 'searchKernels': False}, False)]
            spiceql_call.assert_has_calls(calls)
            assert spiceql_call.call_count == 3
            compute_rotation.assert_called_with(1, -12345)
            np.testing.assert_array_equal(np.array([[-1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0]]), mxv.call_args[0][0])
            np.testing.assert_array_equal(np.array([1, 1, 1]), mxv.call_args[0][1])

    def test_focal2pixel_lines(self):
        with patch('ale.drivers.kplo_drivers.KploShadowCamIsisLabelNaifSpiceDriver.naif_keywords', new_callable=PropertyMock) as naif_keywords, \
             patch('ale.spiceql_access.spiceql_call', side_effect=[-12345, 321]) as spiceql_call, \
             patch('ale.drivers.kplo_drivers.KploShadowCamIsisLabelNaifSpiceDriver.spacecraft_direction', \
             new_callable=PropertyMock) as spacecraft_direction:
            naif_keywords.return_value = {"INS-12345_ITRANSL": [0, 1, 0]}
            spacecraft_direction.return_value = -1
            np.testing.assert_array_equal(self.driver.focal2pixel_lines, [0, -1, 0])
            spacecraft_direction.return_value = 1
            np.testing.assert_array_equal(self.driver.focal2pixel_lines, [0, 1, 0])
            calls = [call('translateNameToCode', {'frame': 'ShadowCam', 'mission': 'kplo', 'searchKernels': False}, False)]
            spiceql_call.assert_has_calls(calls)
            assert spiceql_call.call_count == 1

# ========= Test MiniRf isislabel and naifspice driver (deleted)=========

# ========= Test WAC isislabel and naifspice driver (deleted-JP)=========
