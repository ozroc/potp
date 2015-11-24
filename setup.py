#!/usr/bin/env python

from distutils.core import setup
import sys

sys.path.insert(0, 'src/')
from potp import __version__

setup(name='POTP',
      version=__version__,
      description='Python Object Transfer Protocol',
      author='Tobias Diaz',
      author_email='tobias.deb@gmail.com',
      url='https://github.com/int-0/potp/',
      packages=['potp', 'potp.services'],
      package_dir={
          'potp': 'src/potp',
          'potp.services': 'src/potp/services'
      }
  )

      
