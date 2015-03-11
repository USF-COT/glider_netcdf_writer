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

from datetime import datetime

import numpy as np
from glider_utils.yo import find_yo_extrema
from glider_utils.yo.filters import default_filter
from glider_utils.gps import interpolate_gps


def create_reader(flight_paths, science_paths):
    flight_reader = GliderBDReader(
        flight_paths
    )
    science_reader = GliderBDReader(
        science_paths
    )
    return MergedGliderBDReader(flight_reader, science_reader)


def find_profiles(args):
    profile_values = []
    reader = create_reader(args.flight, args.science)
    for line in reader:
        if args.depth in line:
            profile_values.append([line[args.time], line[args.depth]])

    profile_values = np.array(profile_values)
    profile_dataset = find_yo_extrema(
        profile_values[:, 0], profile_values[:, 1]
    )
    return default_filter(profile_dataset)


def get_file_set_gps(args):
    gps_values = []
    reader = create_reader(args.flight, args.science)
    lat_name = args.gps + 'lat-lat'
    lon_name = args.gps + 'lon-lon'
    for line in reader:
        if lat_name in line:
            gps_values.append(
                [line[args.time], line[lat_name], line[lon_name]]
            )
        else:
            gps_values.append([line[args.time], np.nan, np.nan])

    gps_values = np.array(gps_values)
    gps_values[:, 1], gps_values[:, 2] = interpolate_gps(
        gps_values[:, 0], gps_values[:, 1], gps_values[:, 2]
    )

    return gps_values


def fill_gps(args, line, interp_gps):
    lat_name = args.gps + 'lat-lat'
    lon_name = args.gps + 'lon-lon'
    if lat_name not in line:
        timestamp = line[args.time]
        line[lat_name] = interp_gps[interp_gps[:, 0] == timestamp, 1][0]
        line[lon_name] = interp_gps[interp_gps[:, 0] == timestamp, 2][0]

    return line


def init_netcdf(file_path, global_attrs, deployment_attrs,
                instruments_attrs, profile_id):
    # Check if the output path already exists
    mode = 'w'
    if os.path.isfile(file_path):
        mode = 'a'

    with open_glider_netcdf(file_path, mode) as glider_nc:
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

        # Set Profile ID
        glider_nc.set_profile_id(profile_id)


def read_args():
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
        '-m', '--mode',
        help="Set the mode for the file nameing convention (rt or delayed?)",
        default="delayed"
    )

    parser.add_argument(
        '-t', '--time',
        help="Set time parameter to use for profile recognition",
        default="timestamp"
    )

    parser.add_argument(
        '-d', '--depth',
        help="Set depth parameter to use for profile recognition",
        default="m_depth-m"
    )

    parser.add_argument(
        '-g', '--gps',
        help="Set prefix for gps parameters to use for location estimation",
        default="m_gps_"
    )

    parser.add_argument(
        '-f', '--flight', nargs='+',
        help="Set of flight data files to process."
    )

    parser.add_argument(
        '-s', '--science', nargs='+',
        help="Set of science data files to process."
    )

    return parser.parse_args()


def read_attrs(glider_config_path, glider_name):
    # Load in configurations
    attrs = {}

    # Load institute global attributes
    global_attrs_path = (
        os.path.join(glider_config_path, "global_attributes.json")
    )
    with open(global_attrs_path, 'r') as f:
        attrs['global'] = json.load(f)

    # Load deployment attributes (including global attributes)
    deployment_attrs_path = (
        os.path.join(glider_config_path, glider_name,
                     "deployment.json")
    )
    with open(deployment_attrs_path, 'r') as f:
        attrs['deployment'] = json.load(f)

    # Load datatypes
    datatypes_attrs_path = (
        os.path.join(glider_config_path, "datatypes.json")
    )
    with open(datatypes_attrs_path, 'r') as f:
        attrs['datatypes'] = json.load(f)

    # Load instruments
    instruments_attrs_path = (
        os.path.join(glider_config_path, glider_name,
                     "instruments.json")
    )
    with open(instruments_attrs_path, 'r') as f:
        attrs['instruments'] = json.load(f)

    # Fill in global attributes
    attrs['global'].update(attrs['deployment']['global_attributes'])

    return attrs


def main():
    args = read_args()
    print args
    attrs = read_attrs(args.glider_config_path, args.glider_name)

    # Find profile breaks
    profiles = find_profiles(args)
    print "Profiles:\n %s" % profiles

    # Interpolate GPS
    interp_gps = get_file_set_gps(args)

    # Create NetCDF Files for Each Profile
    profile_id = 0
    profile_end = 0
    file_path = None
    reader = create_reader(args.flight, args.science)
    for line in reader:
        if profile_end < line['timestamp']:
            # Open new NetCDF
            begin_time = datetime.fromtimestamp(line['timestamp'])
            filename = "%s_%s_%s.nc" % (
                args.glider_name,
                begin_time.isoformat(),
                args.mode
            )
            file_path = os.path.join(
                args.output_path,
                filename
            )

            profile = profiles[profiles[:, 2] == profile_id]

            init_netcdf(
                file_path,
                attrs['global'],
                attrs['deployment'],
                attrs['instruments'],
                profile_id + 1  # Store 1 based profile id
            )
            profile = profiles[profiles[:, 2] == profile_id]
            profile_end = max(profile[:, 0])

        with open_glider_netcdf(file_path, 'a') as glider_nc:
            while line['timestamp'] <= profile_end:
                line = fill_gps(args, line, interp_gps)
                glider_nc.stream_dict_insert(line)
                try:
                    line = reader.next()
                except StopIteration:
                    break

        profile_id += 1


if __name__ == '__main__':
    sys.exit(main())
