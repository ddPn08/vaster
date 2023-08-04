from setuptools import setup, find_packages


REQUIREMENTS = [
    "fire",
    "requests",
    "pydantic",
    "paramiko",
    "tqdm",
    "pyyaml",
]

setup(
    name="vaster",
    packages=find_packages(),
    version="0.0.1",
    url="https://github.com/ddPn08/vaster",
    description="",
    author="ddPn08",
    author_email="contact@ddpn.world",
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "vaster=vaster.main:cli",
        ]
    },
    install_requires=REQUIREMENTS,
)
