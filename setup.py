from distutils.core import setup

setup(
    name='Glider NetCDF Writer Library',
    version='1.0',
    author='Michael Lindemuth',
    author_email='mlindemu@usf.edu',
    packages=['glider_netcdf_writer'],
    package_data={'glider_netcdf_writer': ['config/*.json']},
    scripts=[
        'scripts/scripts-bin/check_glider_netcdf.py',
        'scripts/scripts-bin/create_glider_netcdf.py',
        'scripts/scripts-bin/gdam_netcdf_subscriber.py'
    ],
    data_files=[
        ('etc', ['scripts/etc/glider_DAC-2.0.json'])
    ]
)
