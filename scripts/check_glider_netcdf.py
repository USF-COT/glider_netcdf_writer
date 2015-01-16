#!/usr/bin/python
# check_glider_netcdf.py - Verifies that a glider NetCDF file from a provider
#   contains all the required global attributes, dimensions, scalar variables
#   and dimensioned variables. Prints out missing items.
#
# Returns:
#   0 - File complies to NGDAC standard
#   1+ - Number of errors
#
# By: Michael Lindemuth <mlindemu@usf.edu>
# University of South Florida
# College of Marine Science
# Ocean Technology Group

import argparse
import sys
from os import path

import json
from netCDF4 import Dataset


def main():
    parser = argparse.ArgumentParser(
        description='Verifies that a glider NetCDF file from a provider '
                    'contains all the required global attributes, dimensions,'
                    'scalar variables and dimensioned variables.'
    )

    default_standard_path = (
        path.join(
            path.dirname(__file__),
            'glider_DAC-2.0.json'
        )
    )
    parser.add_argument(
        '-s', '--path_to_standard',
        default=default_standard_path
    )

    parser.add_argument(
        'path_to_glider_netcdf',
        help='Path to Glider NetCDF file.'
    )

    args = parser.parse_args()

    # Load requirements spec
    with open(args.path_to_standard, 'r') as f:
        contents = f.read()
    requirements = json.loads(contents)

    # Load NetCDF file
    nc = Dataset(
        args.path_to_glider_netcdf, 'r',
        format='NETCDF4_CLASSIC'
    )

    # Initialize return value
    retVal = 0

    # Check Global Attributes
    global_attributes = nc.ncattrs()
    for req_attribute in requirements['global_attributes']:
        if req_attribute not in global_attributes:
            print "Global Attribute Missing: %s" % (req_attribute)
            retVal += 1

    # Check dimensions
    for req_dimension in requirements['dimensions']:
        if req_dimension not in nc.dimensions:
            print "Dimension Missing: %s" % (req_dimension)
            retVal += 1

    return retVal

if __name__ == '__main__':
    sys.exit(main())
