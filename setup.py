from setuptools import setup, find_packages

install_requires = [
    # "gurobipy",  	# install this manually
    "pytest",
    "click",
    "numpy",
    "matplotlib<=2.9"
]

setup(
    name="network_update",
    # version="0.1",
    packages=["network_update"],
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "network-update = network_update.cli:cli",
        ]
    }
)
