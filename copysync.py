#!/usr/bin/env python
#-*- encoding: utf-8 -*-
import sys
import os
import platform

__author__ = "Damian Kęska"
__license__ = "LGPLv3"
__maintainer__ = "Damian Kęska"
__copyright__ = "Copyleft by CopySync Team"

# get current working directory to include local files (debugging mode)
t = sys.argv[0].replace(os.path.basename(sys.argv[0]), "") + "src/"

if os.path.isdir(t):
    sys.path.append(t)
    
if platform.system() == 'Windows':
    print("Windows is not supported by copysync")
    
import libcopysync
libcopysync.runInstance(True)
