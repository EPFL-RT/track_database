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
    package_data={"track_database": ["LICENSE.eufs_sim"]},
    url="https://github.com/EPFL-RT/track_database",
    author="tudoroancea",
    license="MIT",
    description="Command line tool to check, plot, generate and mirror Formula Student track folders (CSV files).",
    long_description=readme,
    long_description_content_type="text/markdown",
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={"console_scripts": ["track-db=track_database.cli:main"]},
)
