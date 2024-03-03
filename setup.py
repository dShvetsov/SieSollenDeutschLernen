from setuptools import setup, find_packages

setup(
    name='ssdl',
    version='0.1',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'ssdl_bot_start=ssdl.main:main',
        ]
    }

)
