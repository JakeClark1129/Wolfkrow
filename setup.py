from setuptools import setup
from setuptools import find_packages

import os
# Find the scripts:
# os.path.listdir()

print("=" * 80)
packages = find_packages(where="src", include=["wolfkrow", "wolfkrow.*"])
# packages.append("bin")
print packages
print("=" * 80)

print("=" * 80)
import glob
scripts = glob.glob("src/bin/*")
print scripts
print("=" * 80)

setup(
    name='wolfkrow',
    version='0.1.0',
    description='A example Python package',
    url='https://github.com/shuds13/pyexample',
    author='Stephen Hudson',
    author_email='shudson@anl.gov',
    license='BSD 2-clause',
    packages=packages,
    entry_points={
    'console_scripts': [
        'wolfkrow_run_task=wolfkrow.core.engine.wolfkrow_run_task:main',
    ],
    },
    package_dir={
        "": "src"
        # "wolfkrow": ["./src/bin", "./src/wolfkrow"],
    },
    install_requires=[
        'deadline',
        'networkx',
        'yaml',   
    ],
)
