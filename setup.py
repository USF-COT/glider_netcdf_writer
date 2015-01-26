from distutils.core import setup

setup(
    name='Glider NetCDF Writer Library',
    version='1.0',
    author='Michael Lindemuth',
    author_email='mlindemu@usf.edu',
    packages=['glider_netcdf_writer'],
    package_data={'glider_netcdf_writer': ['glider_netcdf_writer/*.json']},
    scripts=[
        'scripts/scripts-bin/check_glider_netcdf.py',
        'scripts/scripts-bin/create_glider_netcdf.py'
    ],
    data_files=[
        ('etc', ['scripts/etc/glider_DAC-2.0.json'])
    ]
)
