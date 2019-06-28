from setuptools import setup, find_packages

setup(
    name='multi_map', 
    version='0.1', 
    packages=['multi_map'],
    scripts=['bin/multi_map'], 
    install_requires=[
        'mapscript_publisher', 
        'ogcserver>=0.1.4',
        'psutil', 
        'daemon', 
        'requests', 
    ]
)