import unittest

from glider_binary_data_reader.glider_bd_reader import (
    GliderBDReader,
    MergedGliderBDReader
)

import os
import json

from glider_netcdf_writer import (
    open_glider_netcdf
)

from netCDF4 import default_fillvals as NC_FILL_VALUES


class TestMergedGliderDataReader(unittest.TestCase):

    def setUp(self):
        # Load NetCDF Configs
        contents = ''
        global_attr_path = (
            '/home/localuser/glider_netcdf_writer/example_config/global_attributes.json'  # NOQA
        )
        self.global_attributes = {}
        with open(global_attr_path, 'r') as f:
            contents = f.read()
        self.global_attributes = json.loads(contents)

        bass_global_attr_path = (
            '/home/localuser/glider_netcdf_writer/example_config/usf-bass/deployment.json'  # NOQA
        )
        with open(bass_global_attr_path, 'r') as f:
            contents = f.read()
        self.deployment = json.loads(contents)
        self.global_attributes.update(self.deployment['global_attributes'])

        datatype_config_path = (
            '/home/localuser/glider_netcdf_writer/example_config/datatypes.json'  # NOQA
        )
        self.datatypes = {}
        with open(datatype_config_path, 'r') as f:
            contents = f.read()
        self.datatypes = json.loads(contents)

        instruments_config_path = (
            '/home/localuser/glider_netcdf_writer/example_config/usf-bass/instruments.json'  # NOQA
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

        self.sbd_tbd_path = '/home/localuser/glider_netcdf_writer/test_data/usf-bass'  # NOQA
        self.sbd_file = 'usf-bass-2014-061-1-0.sbd'
        self.tbd_file = 'usf-bass-2014-061-1-0.tbd'

    def test_with(self):
        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_global_attributes(self.global_attributes)
        self.assertTrue(os.path.isfile(self.test_path))

    def test_set_trajectory_id(self):
        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_trajectory_id(self.deployment['trajectory_id'])
            nc = glider_nc.nc
            self.assertEqual(
                nc.variables['trajectory'][0], self.deployment['trajectory_id']
            )

    def test_segment_id(self):
        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_trajectory_id(self.deployment['trajectory_id'])
            glider_nc.set_segment_id(3)
            nc = glider_nc.nc
            self.assertEqual(nc.variables['segment_id'][0], 3)

    def test_profile_ids(self):
        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_profile_ids([4])
            nc = glider_nc.nc
            self.assertEqual(nc.variables['profile_id'][0], 4)

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

    def test_set_times(self):
        flightReader = GliderBDReader(
            self.sbd_tbd_path,
            'sbd',
            [self.sbd_file]
        )
        scienceReader = GliderBDReader(
            self.sbd_tbd_path,
            'tbd',
            [self.tbd_file]
        )
        reader = MergedGliderBDReader(flightReader, scienceReader)

        times = []
        for line in reader:
            times.append(line['timestamp'])

        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_times(times)
            nc = glider_nc.nc
            self.assertEqual(
                nc.variables['time'][0],
                times[0]
            )

    def test_set_datatypes(self):
        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_datatypes(self.datatypes)
            nc = glider_nc.nc
            self.assertIn('depth', nc.variables)

    def test_data_insert(self):
        flightReader = GliderBDReader(
            self.sbd_tbd_path,
            'sbd',
            [self.sbd_file]
        )
        scienceReader = GliderBDReader(
            self.sbd_tbd_path,
            'tbd',
            [self.tbd_file]
        )
        reader = MergedGliderBDReader(flightReader, scienceReader)

        times = []
        data_by_type = {}

        for header in reader.headers:
            key = header['name'] + '-' + header['units']
            data_by_type[key] = []

        time_uv = NC_FILL_VALUES['f8']
        for line in reader:
            times.append(line['timestamp'])
            for key in data_by_type.keys():
                if key in line:
                    datum = line[key]
                    if key == 'm_water_vx-m/s':
                        time_uv = line['timestamp']
                else:
                    datum = NC_FILL_VALUES['f8']
                data_by_type[key].append(datum)

        with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
            glider_nc.set_times(times)
            glider_nc.set_time_uv(time_uv)
            glider_nc.set_datatypes(self.datatypes)
            for datatype, data in data_by_type.items():
                glider_nc.insert_data(datatype, data)


if __name__ == '__main__':
    unittest.main()
