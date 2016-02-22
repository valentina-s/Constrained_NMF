from setuptools import setup
from os import path
#import os
#import numpy as np


"""
    Installation script for anaconda installers

"""
here = path.abspath(path.dirname(__file__))

with open('README.md','r') as rmf:
    readme = rmf.read()

#incdir = os.path.join(get_python_inc(plat_specific=1), 'Numerical')

setup(
    name = 'Constrained_NMF',
    version = '0.1',
    author = 'Andrea Giovannucci and Eftychios Pnevmatikakis',
    author_email = 'agiovannucci@simonsfoundation.org',
    url = 'https://github.com/agiovann/Constrained_NMF',
    license = 'GPL-2',
    description = 'Advanced algorithms for ROI detection and deconvolution of Calcium Imaging datasets.',
    long_description = readme,
    		# See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
    # How mature is this project? Common values are
    #   3 - Alpha
    #   4 - Beta
    #   5 - Production/Stable
    'Development Status :: 3 - Alpha',

    # Indicate who your project is intended for
    'Intended Audience :: Testers',
    'Topic :: Calcium Imaging :: Analysis Tools',

    # Pick your license as you wish (should match "license" above)
    'License :: OSI Approved :: GPL-2 License',

    # Specify the Python versions you support here. In particular, ensure
    # that you indicate whether you support Python 2, Python 3 or both.
    'Programming Language :: Python :: 2.7',
    ],
    keywords = 'fluorescence calcium ca imaging deconvolution ROI identification',
    packages = ['ca_source_extraction','SPGL1_python_port'],
    data_files = [	('', ['LICENSE.txt']),
                  ('', ['README.md'])],
    install_requires = [ 'python==2.7.*','matplotlib', 'scikit-learn', 'scikit-image', 'ipyparallel','ipython','scipy','numpy','tifffile','cvxopt','picos','cvxpy','joblib>=0.8.4']
    #include_dirs = [incdir, np.get_include()]
    #,'bokeh','jupyter',

)
