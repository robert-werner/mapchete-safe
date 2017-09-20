#!/usr/bin/env python

from setuptools import setup

setup(
    name='mapchete-safe',
    version='0.2',
    description='Mapchete SAFE file read extension',
    author='Joachim Ungar',
    author_email='joachim.ungar@eox.at',
    url='https://github.com/ungarj/mapchete-safe',
    license='MIT',
    packages=['mapchete_safe'],
    install_requires=[
        'mapchete>=0.7',
        's2reader>=0.4',
        'cached_property'
        ],
    entry_points={'mapchete.formats.drivers': ['safe=mapchete_safe']},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: GIS',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest']
)
