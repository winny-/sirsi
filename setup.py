from setuptools import setup
from sirsi import __version__, __author__

setup(
    name='sirsi',
    version=__version__,
    author=__author__,
    author_email='winston@ml1.net',
    description='Manage a sirsi enterprise-based library account',
    url='https://github.com/-winny/sirsi',
    license='MIT',
    packages=['sirsi'],
    install_requires=[
        'argparse==1.2.1',
        'beautifulsoup4==4.3.2',
        'mechanize==0.2.5',
        'python-dateutil==2.2',
    ],
)
