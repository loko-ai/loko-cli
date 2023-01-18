import setuptools, os


def get_requirements():
    return [x for x in open("./requirements.txt").read().split("\n") if not x.startswith("pkg_resources")]


import json

ppom = json.load(open("./ppom.json"))
version = ppom['version']

setuptools.setup(
    name="loko-cli",
    version=version,
    author="Live Tech",
    author_email="f.dantonio@ilivetech.it",
    description="",
    long_description="",
    python_requires='>3.5.0',
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': ['loko=loko_cli.apps.cl:loko'],
    },
    install_requires=get_requirements()

)
