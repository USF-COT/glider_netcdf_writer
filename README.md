# Glider NetCDF Writer

A library for creating NetCDF files for Teledyne Slocum Glider datasets.

## Dependencies

* [NumPy and SciPy](http://www.scipy.org/install.html)
* [Gibbs Seawater Oceanographic Package](https://pypi.python.org/pypi/gsw/)
* [Glider Binary Data Reader](https://github.com/USF-COT/glider_binary_data_reader)
* [Glider Utils](https://github.com/USF-COT/glider_utils)

## Installation

1. Install dependencies (see above)
2. git clone https://github.com/USF-COT/glider_netcdf_writer
3. cd glider_netcdf_writer
4. sudo python setup.py install

## Configuration

Example configuration files from the University of South Florida Glider Group can be found in the [example_config directory](https://github.com/USF-COT/glider_netcdf_writer/tree/master/example_config).  Please edit these files for your institution, possible datatypes, and gliders.  *Do not delete any parameters from these files, only adjust their values for your institution.  Otherwise, your NetCDF files will not pass the check_glider_netcdf.py script.*

A brief overview of each file and folder follows:

* [global_attributes.json](https://github.com/USF-COT/glider_netcdf_writer/blob/master/example_config/global_attributes.json) contains parameters that are specific to the glider institution.
* [your-glider-name-here/deployment.json](https://github.com/USF-COT/glider_netcdf_writer/blob/master/example_config/usf-bass/deployment.json) describes the current deployment for a given glider.  Includes global attribute details that change between deployments and information about the glider/platform deployed.
* [your-glider-name-here/instruments.json](https://github.com/USF-COT/glider_netcdf_writer/blob/master/example_config/usf-bass/instruments.json) provides details about instruments deployed with a single glider.  instrument_ctd is the only required instrument in this file.
* [glider_netcdf_writer/config/datatypes.json](https://github.com/USF-COT/glider_netcdf_writer/blob/master/glider_netcdf_writer/config/datatypes.json) maps between glider generated types (e.g., m_depth-m) and types to be output to a NetCDF file (e.g., depth).  You will only need to edit this file if you need to add datatypes to the NetCDF files.  *Types in here that are not produced by your glider will NOT cause errors.*  Hopefully, through collaboration, we will be able to produce a complete mapping of glider types to NetCDF variables.

## Usage Examples

### Command Line

#### Create NetCDF File
```bash
create_glider_netcdf.py -f <path to flight file> -s <path to science file> <glider name> <base config directory> <NetCDF output directory>
```
Outputs a set of profile NetCDF files to the output directory

#### Check NetCDF File
```bash
check_glider_netcdf.py <path to NetCDF file>
```
Prints errors and returns number of errors.  Prints PASS and returns 0 on success.


#### For Help
```bash
create_glider_netcdf.py -h
```

```bash
check_glider_netcdf.py -h
```

### In Code
```python
from glider_binary_data_reader import (
    GliderBDReader,
    MergedGliderBDReader
)
from glider_netcdf_writer import (
    open_glider_netcdf
)

flightReader = GliderBDReader(
    ['./test_data/usf-bass/usf-bass-2014-061-1-0.sbd']
)
scienceReader = GliderBDReader(
    ['./test_data/usf-bass/usf-bass-2014-061-1-0.tbd']
)
reader = MergedGliderBDReader(flightReader, scienceReader)

with open_glider_netcdf(self.test_path, self.mode) as glider_nc:
    for line in reader:
        glider_nc.insert_dict(line)
```

See a larger example in [tests.py](https://github.com/USF-COT/glider_netcdf_writer/blob/master/tests.py)
