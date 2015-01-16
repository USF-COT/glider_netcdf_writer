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
from netCDF4 import Dataset, stringtoarr
import sys
from datetime import datetime


def open_glider_netcdf(output_path, mode='w', COMP_LEVEL=1):
    return GliderNetCDFWriter(output_path, mode, COMP_LEVEL)


class GliderNetCDFWriter(object):
    """Writes a NetCDF file for glider datasets

    """

    def __init__(self, output_path, mode='w', COMP_LEVEL=1):
        """Initializes a Glider NetCDF Writer
        NOTE: Does not open the file.

        Input:
        - output_path: Path to new or existing NetCDF file.
        - mode: 'w' to create or overwrite a NetCDF file.
                'a' to append to an existing NetCDF file.
                Default: 'w'
        - COMP_LEVEL: NetCDF compression level.
        """

        self.nc = None
        self.output_path = output_path
        self.mode = mode
        self.COMP_LEVEL = COMP_LEVEL
        self.datatypes = {}

    def __setup_qaqc(self):
        """ Internal function for qaqc variable setup
        """

        # Create array of unsigned 8-bit integers to use for _qc flag values
        self.QC_FLAGS = np.array(range(0, 10), 'int8')
        # Meanings of QC_FLAGS
        self.QC_FLAG_MEANINGS = "no_qc_performed good_data probably_good_data bad_data_that_are_potentially_correc  table bad_data value_changed not_used not_used interpolated_value missing_value"  # NOQA

    def __setup_time(self):
        """ Internal function for time variable setup
        """

        # Skip creation if this variable already exists
        if 'time' in self.nc.variables:
            return

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

    def __update_history(self):
        """ Updates the history, date_created, date_modified
        and date_issued variables
        """

        # Get timestamp for this access
        # Cannot use datetime.isoformat()
        # does not append Z at end of string
        now_time = datetime.utcnow()
        time_string = now_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        history_string = "%s: %s\r\n" % (time_string, sys.argv[0])

        if 'history' not in self.nc.ncattrs():
            self.nc.setncattr("history", history_string)
            self.nc.setncattr("date_created", time_string)
        else:
            self.nc.history += history_string

        self.nc.setncattr("date_modified", time_string)
        self.nc.setncattr("date_issued", time_string)

    def __enter__(self):
        """ Opens the NetCDF file. Sets up QAQC and time variables.
        Updates global history variables.
        Called at beginning of Python with block.
        """

        self.nc = Dataset(
            self.output_path, self.mode,
            format='NETCDF4_CLASSIC'
        )

        self.__setup_qaqc()
        self.__setup_time()

        self.__update_history()
        self.insert_index = 0

        return self

    def __exit__(self, type, value, tb):
        """ Updates bounds and closes file.  Called at end of "with" block
        """

        self.__update_bounds()
        self.nc.close()
        self.nc = None

    def set_global_attributes(self, global_attributes):
        """ Sets a dictionary of values as global attributes

        Warning!
        Each file must have different values for the following parameters:
        date_created, date_issued, date_modified
        geospatial_
            lat_max
            lat_min
            lat_resolution
            lat_units
            lon_max
            lon_min
            lon_resolution
            lon_units
            vertical_max
            vertical_min
            vertical_positive
            vertical_resolution
            vertical_units
        history
        id
        time_coverage_end
        time_coverage_resolution
        time_coverage_start
        """

        for key, value in sorted(global_attributes.items()):
            self.nc.setncattr(key, value)

    def set_trajectory_id(self, glider, deployment_date):
        """ Sets the trajectory dimension and variable for the dataset

        Input:
            - glider: Name of the glider deployed.
            - deployment_date: String or DateTime of when glider was
                first deployed.
        """

        if(type(deployment_date) is datetime):
            deployment_date = deployment_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        traj_str = "%s-%s" % (glider, deployment_date)

        if 'trajectory' not in self.nc.variables:
            # Setup Trajectory Dimension
            self.nc.createDimension('traj_strlen', len(traj_str))

            # Setup Trajectory Variable
            trajectory_var = self.nc.createVariable(
                'trajectory',
                'S1',
                ('traj_strlen',),
                zlib=True,
                complevel=self.COMP_LEVEL
            )

            attrs = {
                'cf_role': 'trajectory_id',
                'long_name': 'Trajectory/Deployment Name',  # NOQA
                'comment': 'A trajectory is a single deployment of a glider and may span multiple data files.'  # NOQA
            }
            for key, value in sorted(attrs.items()):
                trajectory_var.setncattr(key, value)
        else:
            trajectory_var = self.nc.variables['trajectory']

        trajectory_var[:] = stringtoarr(traj_str, len(traj_str))

    def set_segment_id(self, segment_id):
        """ Sets the segment ID as a variable

        SEGMENT_ID
        segment_id: 2 byte integer
        kerfoot@marine.rutgers.edu: explicitly specify fill_value when creating
        variable so that it shows up as a variable attribute.  Use the default
        fill_value based on the data type
        """

        segment_var = self.nc.createVariable(
            'segment_id',
            'i2',
            (),
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

    def set_profile_ids(self, profile_ids):
        """ Sets Profile ID as a variable

        PROFILE_ID
        profile_id: 2 byte integer
        kerfoot@marine.rutgers.edu: explicitly specify fill_value when creating
        variable so that it shows up as a variable attribute.  Use the default
        fill_value based on the data type.
        """

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

        profile_var[:] = profile_ids

    def set_platform(self, platform_attrs):
        """ Creates a variable that describes the glider
        """

        platform = self.nc.createVariable('platform', 'i1')

        for key, value in sorted(platform_attrs.items()):
            platform.setncattr(key, value)

    def set_instrument(self, name, attrs):
        """ Adds a description for a single instrument
        """

        instrument = self.nc.createVariable(name, 'i1')

        for key, value in sorted(attrs.items()):
            instrument.setncattr(key, value)

    def set_instruments(self, instruments_array):
        """ Adds a list of instrument descriptions to the dataset
        """

        for description in instruments_array:
            self.set_instrument(description['name'], description['attrs'])

    def set_datatype(self, key, desc):
        """ Sets up a datatype description for the dataset
        """

        if 'is_dimension' in desc and desc['is_dimension']:
            return  # Skip independent fields

        if len(desc) == 0:
            return  # Skip empty configurations

        if desc['name'] in self.nc.variables:
            return  # This variable already exists

        self.datatypes[key] = desc

        if desc['dimension'] is None:
            dimension = ()
        else:
            dimension = (desc['dimension'],)

        datatype = self.nc.createVariable(
            desc['name'],
            desc['type'],
            dimensions=dimension,
            zlib=True,
            complevel=self.COMP_LEVEL,
            fill_value=NC_FILL_VALUES[desc['type']]
        )

        for key, value in sorted(desc['attrs'].items()):
            datatype.setncattr(key, value)

        if 'status_flag' in desc:
            status_flag = desc['status_flag']
            status_flag_name = desc['name'] + "_qc"
            datatype.setncattr('ancillary_variables', status_flag_name)
            status_flag_var = self.nc.createVariable(
                status_flag_name,
                'i1',
                dimension,
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
        """ Sets an array of datatype descriptions in the dataset
        """

        for key, desc in sorted(datatypes.items()):
            self.set_datatype(key, desc)

    def insert_dict(self, line):
        """ Adds a data point glider_binary_data_reader library to NetCDF

        Input:
        - line: A dictionary of values where the key is a given
                <value name>-<units> pair that matches a description
                in the datatypes.json file.
        """

        for name, desc in self.datatypes.items():
            if desc['dimension'] == 'time':
                if name in line:
                    value = line[name]
                else:
                    value = NC_FILL_VALUES['f8']
                self.nc.variables[desc['name']][self.insert_index] = value
            else:
                if desc['name'] in line:
                    self.nc.variables[desc['name']].setValue(value)

        self.insert_index += 1

    def __find_min(self, dataset):
        min_val = sys.maxint
        for value in dataset:
            if value == NC_FILL_VALUES['f8']:
                continue
            else:
                if value < min_val:
                    min_val = value

        return min_val

    def __find_max(self, dataset):
        max_val = -sys.maxint - 1
        for value in dataset:
            if value == NC_FILL_VALUES['f8']:
                continue
            else:
                if value > max_val:
                    max_val = value

        return max_val

    def __update_bounds(self):
        """ Internal description that updates all global attribute bounds
        before closing a file.
        """

        for key, desc in self.datatypes.items():
            if 'global_bound' in desc:
                prefix = desc['global_bound']
                self.nc.setncattr(
                    prefix + '_min',
                    self.__find_min(self.nc.variables[desc['name']])
                )
                self.nc.setncattr(
                    prefix + '_max',
                    self.__find_max(self.nc.variables[desc['name']])
                )
                self.nc.setncattr(
                    prefix + '_units',
                    desc['attrs']['units']
                )
                self.nc.setncattr(
                    prefix + '_resolution',
                    desc['attrs']['resolution']
                )
                self.nc.setncattr(
                    prefix + '_accuracy',
                    desc['attrs']['accuracy']
                )
                self.nc.setncattr(
                    prefix + '_precision',
                    desc['attrs']['precision']
                )
