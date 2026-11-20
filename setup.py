# Copyright (c) Tudor Oancea, EPFL Racing Team Driverless 2022
from setuptools import setup

with open("README.md") as f:
    readme = f.read()

with open("requirements.txt") as f:
    requirements = f.read().splitlines()
    # delete lines starting with # and empty lines
    requirements = [
        r
        for r in requirements
        if not (r.startswith("#") or r.startswith("-e git+") or r.startswith("git+"))
    ]

setup(
    name="track_database",
    version="4.0.0",
    packages=["track_database"],
    package_dir={"track_database": "track_database"},
    url="https://github.com/EPFL-RT-Driverless/track_database",
    author="tudoroancea",
    description="Python and C++ utilities to load, save and create Formula Student tracks stored as CSV files in an external tracks folder.",
    long_description=readme,
    install_requires=requirements,
)
