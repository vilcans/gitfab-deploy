#!/usr/bin/env python

from distutils.core import setup

with open('README.txt') as stream:
    long_description = stream.read()

setup(
    name='gitfab-deploy',
    version='0.1',
    description='Git-based releases and deployment for Fabric',
    author='Martin Vilcans',
    author_email='martin@librador.com',
    url='https://github.com/vilcans/gitfab-deploy',
    packages=['gitfab'],
    long_description=long_description,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python',
    ],
)
