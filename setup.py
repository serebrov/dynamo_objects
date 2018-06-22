import os
import sys

from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

REQUIREMENTS = [
    'boto==2.38.0'
]

TEST_REQUIREMENTS = [
    'nose'
]

setup(
    name='dynamo_objects',
    version='1.0.18',
    packages=find_packages(exclude=('tests', 'tool')),
    url='https://github.com/serebrov/dynamo_objects',
    author='Boris Serebrov',
    author_email='dynamo_objects@googlegroups.com',
    description='Simple DynamoDB object mapper and utils',
    long_description=long_description,
    license='MIT',
    keywords='python dynamodb orm odm',
    install_requires=REQUIREMENTS,
    tests_require=REQUIREMENTS + TEST_REQUIREMENTS,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'License :: OSI Approved :: MIT License',
        'Topic :: Database'
    ],
)
