from setuptools import setup, find_packages

setup(
    name='multi_map', 
    version='0.5', 
    packages=[
        'multi_map',
        'multi_map.map_requests', 
    ],
    scripts=['bin/multi_map'], 
    install_requires=[
        'mapscript_publisher', 
        'ogcserver>=0.1.4',
        'wfs_geocoder', 
        'psutil', 
        'daemon', 
        'requests', 
    ]
)