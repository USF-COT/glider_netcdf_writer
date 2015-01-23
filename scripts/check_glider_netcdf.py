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


def test_global_attributes(nc, requirements):
    """ Tests for required global attributes
    """
    retVal = 0

    global_attributes = nc.ncattrs()
    for req_attribute in requirements['global_attributes']:
        if req_attribute not in global_attributes:
            print "Global Attribute Missing: %s" % (req_attribute)
            retVal += 1
    return retVal


def test_dimensions(nc, requirements):
    """ Tests for required dimensions
    """
    retVal = 0

    for req_dimension in requirements['dimensions']:
        if req_dimension not in nc.dimensions:
            print "Dimension Missing: %s" % (req_dimension)
            retVal += 1

    return retVal


def test_required_variables(nc, requirements):
    """ Tests for required variables
    """
    retVal = 0

    for req_variable in requirements['required_variables']:
        variables = nc.variables
        if req_variable not in variables:
            print "Missing required variable %s" % req_variable
            retVal += 1

    return retVal


def test_variable_attributes(nc, requirements):
    """ Tests for required variable attributes
    """
    retVal = 0

    for variable_name in nc.variables:
        # Skip QC variables
        if variable_name[-2:] == "qc":
            continue

        # Ignore configured variables
        if variable_name in requirements['ignore_variable_check']:
            continue

        variable = nc.variables[variable_name]
        # Skip scalar and descriptive variables
        if variable.size < 2:
            continue

        var_attrs = nc.variables[variable_name].ncattrs()
        for req_var_attr in requirements['variable_attributes']:
            if req_var_attr not in var_attrs:
                print("Variable attribute %s "
                      "missing in %s variable" % (req_var_attr, variable_name))
                retVal += 1

    return retVal


def test_qc_variables(nc, requirements):
    """ Tests that all variables have a corresponding qc variable
    """
    retVal = 0

    for variable_name in nc.variables:
        # Skip QC variables
        if variable_name[-2:] == "qc":
            continue

        # Ignore configured variables
        if variable_name in requirements['ignore_variable_check']:
            continue

        variable = nc.variables[variable_name]
        if variable.size < 2:
            continue

        qc_name = "%s_qc" % variable_name
        if qc_name not in nc.variables:
            print("QC variable missing for %s" % variable_name)
            retVal += 1

    return retVal


def test_platform_attributes(nc, requirements):
    """ Tests for required platform attributes
    """
    retVal = 0

    platform_attrs = nc.variables['platform'].ncattrs()
    for req_platform_attr in requirements['platform_attributes']:
        if req_platform_attr not in platform_attrs:
            print "Platform attribute %s missing" % req_platform_attr
            retVal += 1

    return retVal


def test_ctd_attributes(nc, requirements):
    """ Tests for required ctd attributes
    """
    retVal = 0

    ctd_attrs = nc.variables['instrument_ctd'].ncattrs()
    for req_ctd_attr in requirements['ctd_attributes']:
        if req_ctd_attr not in ctd_attrs:
            print "CTD attribute %s missing" % req_ctd_attr
            retVal += 1

    return retVal


test_functions = [
    test_global_attributes,
    test_dimensions,
    test_required_variables,
    test_variable_attributes,
    test_qc_variables,
    test_platform_attributes,
    test_ctd_attributes
]


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

    for test_fun in test_functions:
        retVal += test_fun(nc, requirements)

    if retVal == 0:
        print "PASS"

    return retVal

if __name__ == '__main__':
    sys.exit(main())
