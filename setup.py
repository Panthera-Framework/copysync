#!/usr/bin/env python
#-*- encoding: utf-8 -*-

"""
    Setup for Panthera buildZip application
"""
 
from distutils.core import setup 

setup(
    name='Copysync is monitoring directories for changes and copying files from local to remote destination on every file change',
    author='Damian Kęska',
    license = "LGPLv3",
    package_dir={'': 'src'},      
    packages=['libcopysync', 'libcopysync.watchers', 'libcopysync.handlers'],
    author_email='webnull.www@gmail.com',
    scripts=['copysync']
)
