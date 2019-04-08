from setuptools import setup, find_packages
from os import path
from io import open

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='tungsten_ci_utils',
    version='0.0.1',
    description='Tungsten Fabric CI/Build utilities',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tungsten-infra/ci-utils',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=[
        'PyYAML',
        'pygit2',
        'requests',
    ],
)
