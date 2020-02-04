import versioneer
from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand

PACKAGE_NAME = "scmdata"
DESCRIPTION = "Simple data handling for Simple Climate Model data"
KEYWORDS = ["data", "simple climate model", "climate", "scm"]

AUTHORS = [
    ("Jared Lewis", "jared.lewis@climate-energy-college.org"),
    ("Zeb Nicholls", "zebedee.nicholls@climate-energy-college.org"),
]
EMAIL = "jared.lewis@climate-energy-college.org"
URL = "https://github.com/lewisjared/scmdata"
PROJECT_URLS = {
    "Bug Reports": "https://github.com/lewisjared/scmdata/issues",
    "Documentation": "https://scmdata.readthedocs.io/en/latest",
    "Source": "https://github.com/lewisjared/scmdata",
}
LICENSE = "3-Clause BSD License"
CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "License :: OSI Approved :: BSD License",
    "Intended Audience :: Developers",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
]

REQUIREMENTS = ["numpy", "python-dateutil", "pint", "pandas"]
REQUIREMENTS_EXTRAS = ["pyam-iamc>=0.3.0", "scipy", "netcdf4", "xlrd"]
REQUIREMENTS_TESTS = ["codecov", "nbval", "pytest-cov", "pytest>=5.0.0"]
REQUIREMENTS_DOCS = ["sphinx>=1.4,<2.1", "sphinx_rtd_theme"]
REQUIREMENTS_DEPLOY = ["twine>=1.11.0", "setuptools>=38.6.0", "wheel>=0.31.0"]

REQUIREMENTS_DEV = [
    *["flake8", "isort", "nbdime", "notebook", "scipy", "netcdf4"],
    *REQUIREMENTS_EXTRAS,
    *REQUIREMENTS_TESTS,
    *REQUIREMENTS_DOCS,
    *REQUIREMENTS_DEPLOY,
]

REQUIREMENTS_EXTRAS = {
    "extras": REQUIREMENTS_EXTRAS,
    "docs": REQUIREMENTS_DOCS,
    "tests": REQUIREMENTS_TESTS,
    "deploy": REQUIREMENTS_DEPLOY,
    "dev": REQUIREMENTS_DEV,
}


SOURCE_DIR = "src"

PACKAGES = find_packages(SOURCE_DIR)  # no exclude as only searching in `src`
PACKAGE_DIR = {"": SOURCE_DIR}
PACKAGE_DATA = {"scmdata": ["data/*.csv"]}


README = "README.rst"

with open(README, "r") as readme_file:
    README_TEXT = readme_file.read()


class ScmData(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest

        pytest.main(self.test_args)


cmdclass = versioneer.get_cmdclass()
cmdclass.update({"test": ScmData})

setup(
    name=PACKAGE_NAME,
    version=versioneer.get_version(),
    description=DESCRIPTION,
    long_description=README_TEXT,
    long_description_content_type="text/x-rst",
    author=", ".join([author[0] for author in AUTHORS]),
    author_email=", ".join([author[1] for author in AUTHORS]),
    url=URL,
    project_urls=PROJECT_URLS,
    license=LICENSE,
    classifiers=CLASSIFIERS,
    keywords=KEYWORDS,
    packages=PACKAGES,
    package_dir=PACKAGE_DIR,
    package_data=PACKAGE_DATA,
    include_package_data=True,
    install_requires=REQUIREMENTS,
    extras_require=REQUIREMENTS_EXTRAS,
    cmdclass=cmdclass,
)
