from setuptools import setup
import os

def read(filename):
    print open(os.path.join(os.path.dirname(__file__), filename)).read()

version = '0.1.0'

setup(
    name='python_daemon',
    version=version,
    description="A simple python daemon that daemonizes python applications",
    long_description=read('README.rst'),
    classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords='python, daemon,',
    author='jtsomnium',
    author_email='kimjt@telcoware.com',
    url='https://github.com/snsol2/sonaWatcher',
    license='MIT',
    py_modules=['watcher'],
    zip_safe=False,
    install_requires=[],
    include_package_data=True,
)
