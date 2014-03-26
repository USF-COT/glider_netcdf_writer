# GLIDER_NETCDF_WRITER - Creates a file like object into which
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
from netCDF4 import default_fillvals as NC_FILL_VALUES
from netCDF4 import Dataset


def open_glider_netcdf(output_path, mode='w', COMP_LEVEL=1):
    return GliderNetCDFWriter(output_path, mode, COMP_LEVEL)


class GliderNetCDFWriter(object):
    """Writes a NetCDF file for glider datasets

    """

    def __init__(self, output_path, mode='w', COMP_LEVEL=1):
        self.nc = None
        self.output_path = output_path
        self.mode = mode
        self.COMP_LEVEL = COMP_LEVEL
        self.datatypes = None

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
            self.time.setncattr(key, value)

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
            self.time_uv.setncattr(key, value)

    def __enter__(self):
        self.nc = Dataset(
            self.output_path, self.mode,
            format='NETCDF4_CLASSIC'
        )

        self.__setup_qaqc()
        if 'time' not in self.nc.variables:
            self.__setup_time()

        return self

    def __exit__(self, type, value, tb):
        self.nc.close()
        self.nc = None

    # Warning!
    # Each file must have different values for the following parameters:
    # date_created, date_issued, date_modified
    # geospatial_
    #     lat_max
    #     lat_min
    #     lat_resolution
    #     lat_units
    #     lon_max
    #     lon_min
    #     lon_resolution
    #     lon_units
    #     vertical_max
    #     vertical_min
    #     vertical_positive
    #     vertical_resolution
    #     vertical_units
    # history
    # id
    # time_coverage_end
    # time_coverage_resolution
    # time_coverage_start
    def set_global_attributes(self, global_attributes):
        for key, value in sorted(global_attributes.items()):
            self.nc.setncattr(key, value)

    def set_trajectory_id(self, trajectory_id):
        if 'trajectory' not in self.nc.variables:
            self.trajectory_dimension = (
                self.nc.createDimension('trajectory', 1)
            )
            trajectory_var = self.nc.createVariable(
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
                trajectory_var.setncattr(key, value)
        else:
            trajectory_var = self.nc.variables['trajectory']

        trajectory_var[0] = trajectory_id

    # SEGMENT_ID
    # segment_id: 2 byte integer
    # kerfoot@marine.rutgers.edu: explicitly specify fill_value when creating
    # variable so that it shows up as a variable attribute.  Use the default
    # fill_value based on the data type
    def set_segment_id(self, segment_id):
        segment_var = self.nc.createVariable(
            'segment_id',
            'i2',
            ('trajectory',),
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
            segment_var.setncattr(key, value)

        segment_var[0] = segment_id

    # PROFILE_ID
    # profile_id: 2 byte integer
    # kerfoot@marine.rutgers.edu: explicitly specify fill_value when creating
    # variable so that it shows up as a variable attribute.  Use the default
    # fill_value based on the data type.
    def set_profile_id(self, profile_id):
        profile_var = self.nc.createVariable(
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
            profile_var.setncattr(key, value)

        profile_var[0] = profile_id

    def set_platform(self, platform_attrs):
        platform = self.nc.createVariable('platform', 'i1')

        for key, value in sorted(platform_attrs.items()):
            platform.setncattr(key, value)

    def set_instrument(self, name, attrs):
        instrument = self.nc.createVariable(name, 'i1')

        for key, value in sorted(attrs.items()):
            instrument.setncattr(key, value)

    def set_instruments(self, instruments_array):
        for description in instruments_array:
            self.set_instrument(description['name'], description['attrs'])

    def set_times(self, times):
        self.nc.variables['time'][:] = times

    def set_time_uv(self, time_uv):
        self.nc.variables['time_uv'][0] = time_uv

    def set_datatype(self, key, desc):
        if 'is_dimension' in desc and desc['is_dimension']:
            return  # Skip independent fields

        if len(desc) == 0:
            return  # Skip empty configurations

        if desc['name'] in self.nc.variables:
            return  # This variable already exists

        self.datatypes[key] = desc

        datatype = self.nc.createVariable(
            desc['name'],
            desc['type'],
            (desc['dimension'],),
            zlib=True,
            complevel=self.COMP_LEVEL,
            fill_value=NC_FILL_VALUES[desc['type']]
        )

        for key, value in sorted(desc['attrs'].items()):
            datatype.setncattr(key, value)

        if 'status_flag' in desc:
            status_flag = desc['status_flag']
            status_flag_name = desc['name'] + "_status_flag"
            datatype.setncattr('ancillary_variables', status_flag_name)
            status_flag_var = self.nc.createVariable(
                status_flag_name,
                'i1',
                (desc['dimension'],),
                zlib=True,
                complevel=self.COMP_LEVEL,
                fill_value=NC_FILL_VALUES['i1']
            )
            # Append defaults
            sf_standard_name = desc['attrs']['standard_name'] + ' status_flag'
            status_flag['attrs'].update({
                'standard_name': sf_standard_name,
                'flag_meanings': self.QC_FLAG_MEANINGS,
                'valid_min': self.QC_FLAGS[0],
                'valid_max': self.QC_FLAGS[-1],
                'flag_values': self.QC_FLAGS
            })
            for key, value in sorted(status_flag['attrs'].items()):
                status_flag_var.setncattr(key, value)

    def set_datatypes(self, datatypes):
        self.datatypes = {}
        for key, desc in sorted(datatypes.items()):
            self.set_datatype(key, desc)

    def insert_data(self, datatype, data):
        if datatype in self.datatypes:
            desc = self.datatypes[datatype]
            try:
                if desc['dimension'] == 'time':
                    self.nc.variables[desc['name']][:] = data
                else:
                    # TODO: Fix this hack for values in the time_uv
                    # dimension
                    value = NC_FILL_VALUES['f8']
                    for datum in data:
                        if datum != NC_FILL_VALUES['f8']:
                            value = datum
                    self.nc.variables[desc['name']][0] = value
            except Exception, e:
                print '%s: %s - %s' % (datatype, data, e)
        else:
            print "%s not in datatype" % (datatype)
