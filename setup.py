from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='YAX',
    version='1.2.0',
    packages=['yax'],
    url='https://github.com/morta-code/YAX',
    license='LGPLv3',
    author='Móréh Tamás, MTA-PPKE-NLPG',
    author_email='morta@digitus.itk.ppke.hu',
    description='Yet Another XML parser with the power of event-based memory-safe mechanism.',
    long_description=long_description,
    keywords="xml lxml parser event-based record-oriented",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Markup :: XML"
    ]
)
