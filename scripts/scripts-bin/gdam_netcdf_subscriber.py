import daemon
import zmq

import os
import sys
import subprocess

import argparse

import logging
logger = logging.getLogger('gdam_netcdf_subscriber')

import lockfile


def parse_args():
    parser = argparse.ArgumentParser(
        description='Listens for GDAM to process new glider binary data '
                    'files. Runs create_glider_netcdf.py script in a '
                    'subprocess on new files to produce a NetCDF file.'
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
        '-g', '--gps_prefix',
        help="Set prefix for gps parameters to use for location estimation",
        default="m_gps_"
    )

    parser.add_argument(
        "--zmq_url",
        default="tcp://localhost:8008",
        help="ZMQ url for the GDAM publisher. Default: tcp://localhost:8008"
    )

    parser.add_argument(
        "--daemonize",
        type=bool,
        help="To daemonize or not to daemonize.  Default: false",
        default=False
    )
    parser.add_argument(
        "--log_file",
        help="Path of log file.  Default: ./gdam_netcdf_sub.log",
        default="./gdam_netcdf_sub.log"
    )
    parser.add_argument(
        "--pid_file",
        help="Path of PID file for daemon.  Default: ./gdam_netcdf_sub.pid",
        default="./gdam_netcdf_subscriber.pid"
    )

    return parser.parse_args()


MODE_MAPPING = {
    "rt": [".sbd", ".tbd", ".mbd", ".nbd"],
    "delayed": [".dbd", ".ebd"]
}


def process_files(message, args):
    mode = 'rt'

    filename, extension = os.path.splitext(message['flight_file'])
    if extension in MODE_MAPPING['delayed']:
        mode = 'delayed'
    else:
        mode = 'rt'

    flight_path = os.path.join(
        message['path'],
        message['flight_file']
    )
    science_path = os.path.join(
        message['path'],
        message['science_path']
    )

    subprocess.call([
        "create_glider_netcdf.py",
        message['glider'],
        args.config_path,
        args.output_path,
        "--mode",
        mode,
        "-f",
        flight_path,
        "-s",
        science_path
    ])


def run_subscriber(args):
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(args.zmq_url)
    socket.setsockopt(zmq.SUBSCRIBE, '')

    while True:
        try:
            message = socket.recv_json()
            process_files(message, args)
        except Exception, e:
            logger.error("Subscriber exited: %s" % (e))
            break


def main():
    args = parse_args()

    # Setup logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s "
                                  "- %(levelname)s - %(message)s")
    if args.daemonize:
        log_handler = logging.FileHandler(args.log_file)
    else:
        log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    if args.daemonize:
        logger.info('Starting')
        daemon_context = daemon.DaemonContext(
            pidfile=lockfile.FileLock(args.pid_file),
            files_preserve=[log_handler.stream.fileno()],
        )
        with daemon_context:
            run_subscriber(args)
    else:
        run_subscriber(args)

    logger.info('Stopped')

if __name__ == '__main__':
    sys.exit(main())
