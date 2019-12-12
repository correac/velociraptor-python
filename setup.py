import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="velociraptor",
    version="0.2.0",
    description="Velociraptor catalogue reading routines.",
    url="https://github.com/swiftsim/velociraptor-python",
    author="Josh Borrow",
    author_email="joshua.borrow@durham.ac.uk",
    packages=setuptools.find_packages(),
    scripts=["velociraptor-plot"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: OS Independent",
    ],
    install_requires=["numpy", "unyt>=2.3.0", "h5py"],
)
