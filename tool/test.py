#!/usr/bin/env python

from unittest import TestLoader, TextTestRunner
from os import path
import sys

here = path.abspath(path.dirname(__file__))
sys.path.append(path.join(here, '../'))

tests = TestLoader().discover(path.join(here, '../tests'))
testRunner = TextTestRunner()
testRunner.run(tests)
