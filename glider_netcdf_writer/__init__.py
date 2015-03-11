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
from os import path
import json


DEFAULT_GLIDER_BASE = path.join(path.dirname(__file__), "config")

GLIDER_QC = {
    "no_qc_performed": 0,
    "good_data": 1,
    "probably_good_data": 2,
    "bad_data_that_are_potentially_correctable": 3,
    "bad_data": 4,
    "value_changed": 5,
    "interpolated_value": 8,
    "missing_value": 9
}


def open_glider_netcdf(output_path, mode='w', COMP_LEVEL=1,
                       config_path=DEFAULT_GLIDER_BASE):
    return GliderNetCDFWriter(output_path, mode, COMP_LEVEL, config_path)


class GliderNetCDFWriter(object):
    """Writes a NetCDF file for glider datasets

    """

    def __init__(self, output_path, mode='w', COMP_LEVEL=1,
                 config_path=DEFAULT_GLIDER_BASE):
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
        self.config_path = config_path
        self.datatypes = {}

    def __setup_qaqc(self):
        """ Internal function for qaqc variable setup
        """

        # Create array of unsigned 8-bit integers to use for _qc flag values
        self.QC_FLAGS = np.array(range(0, 10), 'int8')
        # Meanings of QC_FLAGS
        self.QC_FLAG_MEANINGS = "no_qc_performed good_data probably_good_data bad_data_that_are_potentially_correctable bad_data value_changed not_used not_used interpolated_value missing_value"  # NOQA

        self.qaqc_methods = {}

    def __load_datatypes(self):
        """ Internal function to setup known datatypes

            Adds variables from base_variables.json
        """

        datatypes_path = path.join(
            self.config_path,
            'datatypes.json'
        )

        with open(datatypes_path, 'r') as f:
            contents = f.read()
        self.datatypes = json.loads(contents)

    def __update_history(self):
        """ Updates the history, date_created, date_modified
        and date_issued file attributes
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

    def __get_time_len(self):
        if 'time' in self.nc.variables:
            return len(self.nc.variables['time'])
        else:
            return 0

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
        self.__load_datatypes()

        self.__update_history()
        self.stream_index = self.__get_time_len()

        return self

    def __exit__(self, type, value, tb):
        """ Updates bounds and closes file.  Called at end of "with" block
        """

        if self.__get_time_len() > 0:
            self.update_bounds()

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

    def check_datatype_exists(self, key):
        if key not in self.datatypes:
            raise KeyError('Unknown datatype %s cannot '
                           'be inserted to NetCDF' % key)

        datatype = self.datatypes[key]
        if datatype['name'] not in self.nc.variables:
            self.set_datatype(key, datatype)

        return datatype

    def get_status_flag_name(self, name):
        return name + "_qc"

    def set_datatype(self, key, desc):
        """ Sets up a datatype description for the dataset
        """

        if 'is_dimension' in desc and desc['is_dimension']:
            self.nc.createDimension(desc['name'], desc['dimension_length'])

        if len(desc) == 0:
            return  # Skip empty configurations

        if desc['name'] in self.nc.variables:
            return  # This variable already exists

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
            status_flag_name = self.get_status_flag_name(desc['name'])
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

    def perform_qaqc(self, key, value):
        if key in self.qaqc_methods:
            flag = self.qaqc_methods[key](value)
        elif value == NC_FILL_VALUES['f8']:
            flag = GLIDER_QC["missing_value"]
        else:
            flag = GLIDER_QC['no_qc_performed']

        return flag

    def set_scalar(self, key, value=None):
        datatype = self.check_datatype_exists(key)

        if value is None:
            value = NC_FILL_VALUES[datatype['type']]

        self.nc.variables[datatype['name']].assignValue(value)

        if "status_flag" in datatype:
            status_flag_name = self.get_status_flag_name(datatype['name'])
            flag = self.perform_qaqc(key, value)
            self.nc.variables[status_flag_name].assignValue(flag)

    def set_array_value(self, key, index, value=None):
        datatype = self.check_datatype_exists(key)

        if value is None:
            value = NC_FILL_VALUES[datatype['type']]

        self.nc.variables[datatype['name']][index] = value

        if "status_flag" in datatype:
            status_flag_name = self.get_status_flag_name(datatype['name'])
            flag = self.perform_qaqc(key, value)
            self.nc.variables[status_flag_name][index] = flag

    def set_array(self, key, values):
        datatype = self.check_datatype_exists(key)

        self.nc.variables[datatype['name']][:] = values
        if "status_flag" in datatype:
            status_flag_name = self.get_status_flag_name(datatype['name'])
            for i, value in enumerate(values):
                flag = self.perform_qaqc(key, value)
                self.nc.variables[status_flag_name][i] = flag

    def set_segment_id(self, segment_id):
        """ Sets the segment ID as a variable

        SEGMENT_ID
        segment_id: 2 byte integer
        kerfoot@marine.rutgers.edu: explicitly specify fill_value when creating
        variable so that it shows up as a variable attribute.  Use the default
        fill_value based on the data type
        """

        self.set_scalar('segment_id', segment_id)

    def set_profile_id(self, profile_id):
        """ Sets Profile ID in NetCDF File

        """

        self.set_scalar('profile_id', profile_id)

    def set_platform(self, platform_attrs):
        """ Creates a variable that describes the glider
        """

        self.set_scalar('platform')
        for key, value in sorted(platform_attrs.items()):
            self.nc.variables['platform'].setncattr(key, value)

    def set_instrument(self, name, attrs):
        """ Adds a description for a single instrument
        """

        if name not in self.nc.variables:
            self.nc.createVariable(name, 'i1')

        for key, value in sorted(attrs.items()):
            self.nc.variables[name].setncattr(key, value)

    def set_instruments(self, instruments_array):
        """ Adds a list of instrument descriptions to the dataset
        """

        for description in instruments_array:
            self.set_instrument(description['name'], description['attrs'])

    def fill_uv_vars(self, line):
        self.set_scalar('time_uv', line['m_present_time-timestamp'])
        self.set_scalar('lat_uv', line['m_gps_lat-lat'])
        self.set_scalar('lon_uv', line['m_gps_lon-lon'])

    def stream_dict_insert(self, line, qaqc_methods={}):
        """ Adds a data point glider_binary_data_reader library to NetCDF

        Input:
        - line: A dictionary of values where the key is a given
                <value name>-<units> pair that matches a description
                in the datatypes.json file.
        """

        if 'timestamp' not in line:
            print line
            raise ValueError('No timestamp found for line')

        self.set_array_value('timestamp', self.stream_index, line['timestamp'])

        for name, value in line.items():
            if name == 'timestamp':
                continue  # Skip timestamp, inserted above

            try:
                datatype = self.check_datatype_exists(name)
            except KeyError, e:
                print e
                continue

            datatype = self.datatypes[name]
            if datatype['dimension'] == 'time':
                self.set_array_value(name, self.stream_index, value)
            else:
                self.set_scalar(name, value)
                if name == "m_water_vx-m/s":
                    self.fill_uv_vars(line)

        self.stream_index += 1

    def __find_min(self, dataset):
        min_val = sys.maxint
        for value in dataset:
            if value != NC_FILL_VALUES['f8'] and \
               value < min_val:
                min_val = value

        return min_val

    def __find_max(self, dataset):
        max_val = -sys.maxint - 1
        for value in dataset:
            if value != NC_FILL_VALUES['f8'] and \
               value > max_val:
                max_val = value

        return max_val

    def __find_avg(self, dataset):
        avg_sum = 0
        num_points = 0
        for value in dataset:
            avg_sum += value
            num_points += 1

        if num_points == 0:
            return NC_FILL_VALUES['f8']
        else:
            return avg_sum / num_points

    def __netcdf_to_np_op(self, variable_data, operation):
        array = np.array(variable_data)
        array[array == NC_FILL_VALUES['f8']] = float('nan')

        return operation(array)

    def __update_profile_vars(self):
        """ Internal function that updates all profile variables
        before closing a file
        """

        if 'time' in self.nc.variables:
            self.nc.variables['profile_time'].assignValue(
                self.__netcdf_to_np_op(
                    self.nc.variables['time'][:],
                    np.nanmin
                )
            )

        if 'lon' in self.nc.variables:
            self.nc.variables['profile_lon'].assignValue(
                self.__netcdf_to_np_op(
                    self.nc.variables['lon'][:],
                    np.average
                )
            )

        if 'lat' in self.nc.variables:
            self.nc.variables['profile_lat'].assignValue(
                self.__netcdf_to_np_op(
                    self.nc.variables['lat'][:],
                    np.average
                )
            )

    def update_bounds(self):
        """ Internal function that updates all global attribute bounds
        before closing a file.
        """

        for key, desc in self.datatypes.items():
            if 'global_bound' in desc:
                prefix = desc['global_bound']
                dataset = self.nc.variables[desc['name']][:]
                self.nc.setncattr(
                    prefix + '_min',
                    self.__find_min(dataset)
                )
                self.nc.setncattr(
                    prefix + '_max',
                    self.__find_max(dataset)
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
