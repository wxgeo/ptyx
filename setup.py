from setuptools import setup, find_packages


with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="ptyx",
    version="20.5",
    author="Nicolas Pourcelot",
    author_email="nicolas.pourcelot@gmail.com",
    description="pTyX is a python precompiler for LaTeX",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wxgeo/ptyx",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
                'ptyx=ptyx.script:ptyx',
                'autoqcm=ptyx.extensions.autoqcm.cli:main',
		'scan=ptyx.extensions.autoqcm.cli:scan'],
    },
    python_requires='>=3.6',
    install_requires=['numpy', 'sympy', 'Pillow'],
)

