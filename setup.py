from setuptools import find_packages, setup

cmdclass_dict = {}  # type:ignore

# MANIFEST.in ensures that readme and version included into sdist

install_requires = ["pyyaml", "python-dateutil"]

dev_requires = [
    "hs-build-tools",
    "coverage",
    "mypy",
    "wheel",
    "twine",
    "black",
    "isort",
    "pytest",
    "pytest-mypy",
    "pytest-cov",
    "types-python-dateutil",
    "types-pyyaml",
]


def read_file(f):
    with open(f, "r") as fh:
        return fh.read()


long_description = read_file("README.md")

try:
    from hs_build_tools.release import get_version_and_add_release_cmd

    version = get_version_and_add_release_cmd("version.txt", cmdclass_dict)
except ModuleNotFoundError:
    version = read_file("version.txt").strip()

setup(
    name="azup",
    version=str(version),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: System :: Archiving :: Backup",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Work with azure cloud using `az` cli",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/walnutgeek/azup",
    author="Walnut Geek",
    author_email="wg@walnutgeek.com",
    license="Apache 2.0",
    packages=find_packages(exclude=("*.tests",)),
    cmdclass=cmdclass_dict,
    entry_points={"console_scripts": ["azup=azup.main:print_main"]},
    install_requires=install_requires,
    extras_require={"dev": dev_requires},
    zip_safe=False,
)
