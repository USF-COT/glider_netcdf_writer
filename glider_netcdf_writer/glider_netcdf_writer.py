# GLIDER_NETCDF_WRITER.PY - Creates a file like object into which
#   glider binary data readers can insert data.
#
# Depends on the glider_binary_data_reader library:
# https://github.com/USF-COT/glider_binary_data_reader
#
# By: Michael Lindemuth
# University of South Florida
# College of Marine Science
# Ocean Technology Group
#
# Much of the code below is derived from John Kerfoot's ioos_template_example.py  # NOQA
# https://github.com/IOOSProfilingGliders/Real-Time-File-Format/blob/master/util/ioos_template_example.py#L136  # NOQA

import numpy as np
from datetime import datetime, timedelta
from netCDF4 import default_fillvals as NC_FILL_VALUES
from netCDF4 import num2date, date2num
from netCDF4 import Dataset
import time as t


def open_glider_netcdf(output_path, COMP_LEVEL=1):
    return GliderNetCDFWriter(output_path, COMP_LEVEL)


class GliderNetCDFWriter(object):
    """Writes a NetCDF file for glider datasets

    """

    def __init__(self, output_path, COMP_LEVEL=1):
        self.nc = None
        self.output_path = output_path
        self.COMP_LEVEL = COMP_LEVEL

    def __setup_qaqc(self):
        # Create array of unsigned 8-bit integers to use for _qc flag values
        self.QC_FLAGS = np.array(range(0, 10), 'int8')
        # Meanings of QC_FLAGS
        self.QC_FLAG_MEANINGS = "no_qc_performed good_data probably_good_data bad_data_that_are_potentially_correc  table bad_data value_changed not_used not_used interpolated_value missing_value"  # NOQA

    def __setup_time(self):
        # Setup time dimension
        self.time_dimension = self.nc.createDimension('time', None)
        self.time = self.nc.createVariable(
            'time',
            'f8',
            ('time',),
            zlib=True,
            complevel=self.COMP_LEVEL
        )

        attrs = {
            'axis': "T",
            'calendar': 'gregorian',
            'units': 'seconds since 1970-01-01 00:00:00 UTC',
            'standard_name': 'time',
            'long_name': 'Time',
            'observation_type': 'measured',
            'sensor_name': ' ',
        }
        for key, value in sorted(attrs.items()):
            self.time.setncattrs(key, value)

        # TIME_QC
        # time_qc: 1 byte integer (ie: byte)
        # kerfoot@marine.rutgers.edu: explicitly specify
        # fill_value when creating variable so that it shows
        # up as a variable attribute.  Use the default
        # fill_value based on the data type.
        self.time_qc = self.nc.createVariable(
            'time_qc',
            'i1',
            ('time',),
            zlib=True,
            complevel=self.COMP_LEVEL,
            fill_value=NC_FILL_VALUES['i1']
        )

        attrs = {
            'long_name': 'time Quality Flag',
            'standard_name': 'time status_flag',
            'flag_meanings': self.QC_FLAG_MEANINGS,
            'valid_min': self.QC_FLAGS[0],
            'valid_max': self.QC_FLAGS[-1],
            'flag_values': self.QC_FLAGS
        }
        for key, value in sorted(attrs.items()):
            self.time_qc.setncattr(key, value)

        # Setup time_uv dimension
        # time_uv: 64 bit float - no _Fill_Value since dimension
        self.time_uv_dimension = self.nc.createDimension('time_uv', 1)
        self.time_uv = self.nc.createVariable(
            'time_uv',
            'f8',
            ('time_uv',),
            zlib=True,
            complevel=self.COMP_LEVEL
        )
        attrs = {
            'axis': "T",
            'calendar': 'gregorian',
            'units': 'seconds since 1970-01-01 00:00:00 UTC',
            'standard_name': 'time',
            'long_name': 'Approximate time midpoint of each segment',
            'observation_type': 'estimated'
        }
        for key, value in sorted(attrs.items()):
            self.time_uv.setncattrs(key, value)

    def __enter__(self):
        self.nc = Dataset(self.output_path, 'w', format='NetCDF4_CLASSIC')

        self.__setup_qaqc()
        self.__setup_time()
        self.__setup_trajectory()

    def __exit__(self):
        self.nc.close()
        self.nc = None

    def set_global_attributes(self, global_attributes):
        for key, value in sorted(global_attributes.items()):
            self.nc.setncattr(key, value)

    def set_trajectory_id(self, trajectory_id):
        if self.trajectory_dimension is None:
            self.trajectory_dimension = (
                self.nc.createDimension('trajectory', 1)
            )
            self.trajectory = self.nc.createVariable(
                'trajectory',
                'i2',
                ('trajectory',),
                zlib=True,
                complevel=self.COMP_LEVEL
            )

            attrs = {
                'cf_role': 'trajectory_id',
                'long_name': 'Unique identifier for each trajectory feature contained in the file',  # NOQA
                'comment': 'A trajectory can span multiple data files each containing a single segment.'  # NOQA
            }
            for key, value in sorted(attrs.items()):
                self.trajectory.setncattrs(key, value)

        self.trajectory = [trajectory_id]

    # SEGMENT_ID
    # segment_id: 2 byte integer
    # kerfoot@marine.rutgers.edu: explicitly specify fill_value when creating
    # variable so that it shows up as a variable attribute.  Use the default
    # fill_value based on the data type
    def set_segment_id(self, segment_id):
        if self.segment_id is None:
            self.segment_id = self.nc.createVariable(
                'segment_id',
                'i2',
                ('time',),
                zlib=True,
                complevel=self.COMP_LEVEL,
                fill_value=NC_FILL_VALUES['i2']
            )

            attrs = {
                'comment': 'Sequential segment number within a trajectory/deployment. A segment corresponds to the set of data collected between 2 gps fixes obtained when the glider surfaces.',  # NOQA
                'long_name': 'Segment ID',
                'valid_min': 1,
                'valid_max': 999,
                'observation_type': 'calculated',
            }
            for key, value in sorted(attrs.items()):
                self.segment_id.setncattrs(key, value)

        self.segment_id = [segment_id]

    # PROFILE_ID
    # profile_id: 2 byte integer
    # kerfoot@marine.rutgers.edu: explicitly specify fill_value when creating
    # variable so that it shows up as a variable attribute.  Use the default
    # fill_value based on the data type.
    def set_profile_id(self, profile_id):
        if self.profile_id is None:
            self.profile_id = self.nc.createVariable(
                'profile_id',
                'i2',
                ('time',),
                zlib=True,
                complevel=self.COMP_LEVEL,
                fill_value=NC_FILL_VALUES['i2']
            )

            attrs = {
                'comment': 'Sequential profile number within the current segment. A profile is defined as a single dive or climb',  # NOQA
                'long_name': 'Profile ID',
                'valid_min': 1,
                'valid_max': 999,
                'observation_type': 'calculated',
            }
            for key, value in sorted(attrs.items()):
                self.profile_id.setncattrs(key, value)

    # Use this method to feed the generator in
    def set_variable_config(self, variable_config_json):
        self.variable_config = variable_config_json

    
