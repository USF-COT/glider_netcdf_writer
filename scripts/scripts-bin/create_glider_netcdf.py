#!/usr/bin/python

# create_glider_netcdf.py - A command line script for generating NetCDF files
# from a subset of glider binary data files.
#
# By: Michael Lindemuth <mlindemu@usf.edu>
# University of South Florida
# College of Marine Science
# Ocean Technology Group

import argparse

from glider_binary_data_reader import (
    GliderBDReader,
    MergedGliderBDReader
)

from glider_netcdf_writer import (
    open_glider_netcdf
)

import sys
import os
import json


def main():
    parser = argparse.ArgumentParser(
        description='Parses a set of glider binary data files to a '
                    'single NetCDF file according to configurations '
                    'for institution, deployment, glider, and datatypes.'
    )

    parser.add_argument(
        'glider_name',
        help='Name of glider that generated given binary files.'
    )

    parser.add_argument(
        'glider_config_path',
        help='Path to configuration files for institution.'
    )

    parser.add_argument(
        'output_path',
        help='Path to file for NetCDF output.'
    )

    parser.add_argument(
        '-f', '--flight', nargs='+',
        help="Set of flight data files to process."
    )

    parser.add_argument(
        '-s', '--science', nargs='+',
        help="Set of science data files to process."
    )

    args = parser.parse_args()

    # Check if the output path already exists
    mode = 'w'
    if os.path.isfile(args.output_path):
        mode = 'a'

    # Load in configurations
    global_attrs = {}
    deployment_attrs = {}
    datatypes_attrs = {}
    instruments_attrs = {}

    # Load institute global attributes
    global_attrs_path = (
        os.path.join(args.glider_config_path, "global_attributes.json")
    )
    with open(global_attrs_path, 'r') as f:
        global_attrs = json.load(f)

    # Load deployment attributes (including global attributes)
    deployment_attrs_path = (
        os.path.join(args.glider_config_path, args.glider_name,
                     "deployment.json")
    )
    with open(deployment_attrs_path, 'r') as f:
        deployment_attrs = json.load(f)

    # Load datatypes
    datatypes_attrs_path = (
        os.path.join(args.glider_config_path, "datatypes.json")
    )
    with open(datatypes_attrs_path, 'r') as f:
        datatypes_attrs = json.load(f)

    # Load instruments
    instruments_attrs_path = (
        os.path.join(args.glider_config_path, args.glider_name,
                     "instruments.json")
    )
    with open(instruments_attrs_path, 'r') as f:
        instruments_attrs = json.load(f)

    # Fill in global attributes
    global_attrs.update(deployment_attrs['global_attributes'])

    with open_glider_netcdf(args.output_path, mode) as glider_nc:
        # Set global attributes
        glider_nc.set_global_attributes(global_attrs)

        # Set Trajectory
        glider_nc.set_trajectory_id(
            deployment_attrs['glider'],
            deployment_attrs['trajectory_date']
        )

        # Set Platform
        glider_nc.set_platform(deployment_attrs['platform'])

        # Set Instruments
        glider_nc.set_instruments(instruments_attrs)

        # Set Datatypes
        glider_nc.set_datatypes(datatypes_attrs)

        # Read binary data files
        # Create binary data readers
        flight_reader = GliderBDReader(
            args.flight
        )
        science_reader = GliderBDReader(
            args.science
        )
        reader = MergedGliderBDReader(flight_reader, science_reader)
        for line in reader:
            glider_nc.insert_dict(line)


if __name__ == '__main__':
    sys.exit(main())
