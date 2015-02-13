import unittest

from glider_binary_data_reader import (
    GliderBDReader,
    MergedGliderBDReader
)

import os
import json

from glider_netcdf_writer import (
    open_glider_netcdf
)


class TestMergedGliderDataReader(unittest.TestCase):

    def setUp(self):
        # Load NetCDF Configs
        contents = ''
        global_attr_path = (
            './example_config/global_attributes.json'  # NOQA
        )
        self.global_attributes = {}
        with open(global_attr_path, 'r') as f:
            contents = f.read()
        self.global_attributes = json.loads(contents)

        bass_global_attr_path = (
            './example_config/usf-bass/deployment.json'  # NOQA
        )
        with open(bass_global_attr_path, 'r') as f:
            contents = f.read()
        self.deployment = json.loads(contents)
        self.global_attributes.update(self.deployment['global_attributes'])

        datatype_config_path = (
            './example_config/datatypes.json'  # NOQA
        )
        self.datatypes = {}
        with open(datatype_config_path, 'r') as f:
            contents = f.read()
        self.datatypes = json.loads(contents)

        instruments_config_path = (
            './example_config/usf-bass/instruments.json'  # NOQA
        )
        self.instruments = {}
        with open(instruments_config_path, 'r') as f:
            contents = f.read()
        self.instruments = json.loads(contents)

        self.test_path = './nc_test.nc'
        if os.path.isfile(self.test_path):
            self.mode = 'a'
        else:
            self.mode = 'w'

    def test_with(self):
        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_global_attributes(self.global_attributes)
        self.assertTrue(os.path.isfile(self.test_path))

    def test_set_trajectory_id(self):
        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_trajectory_id(
                self.deployment['glider'],
                self.deployment['trajectory_date']
            )
            nc = glider_nc.nc
            traj_str = "%s-%s" % (
                self.deployment['glider'],
                self.deployment['trajectory_date']
            )

            self.assertEqual(
                nc.variables['trajectory'][:].tostring(), traj_str
            )

    def test_segment_id(self):
        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_segment_id(3)
            nc = glider_nc.nc
            self.assertEqual(nc.variables['segment_id'].getValue(), 3)

    def test_profile_ids(self):
        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_profile_id(4)
            nc = glider_nc.nc
            self.assertEqual(nc.variables['profile_id'].getValue(), 4)

    def test_set_platform(self):
        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_platform(self.deployment['platform'])
            nc = glider_nc.nc
            self.assertEqual(
                nc.variables['platform'].getncattr('wmo_id'),
                4801516
            )

    def test_set_instruments(self):
        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_instruments(self.instruments)
            nc = glider_nc.nc
            self.assertIn('instrument_ctd', nc.variables)

    def test_set_datatypes(self):
        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_datatypes(self.datatypes)
            nc = glider_nc.nc
            self.assertIn('depth', nc.variables)

    def test_data_insert(self):
        flightReader = GliderBDReader(
            ['./test_data/usf-bass/usf-bass-2014-061-1-0.sbd']
        )
        scienceReader = GliderBDReader(
            ['./test_data/usf-bass/usf-bass-2014-061-1-0.tbd']
        )
        reader = MergedGliderBDReader(flightReader, scienceReader)

        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_datatypes(self.datatypes)
            for line in reader:
                glider_nc.insert_dict(line)
            glider_nc.update_calculated()


if __name__ == '__main__':
    unittest.main()
