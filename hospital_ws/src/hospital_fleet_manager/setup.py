from setuptools import setup
import os
from glob import glob

package_name = 'hospital_fleet_manager'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', [os.path.join('resource', package_name)]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name), glob(os.path.join('resource', package_name))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    author='AI Hospital Team',
    description='AI-Based Hospital Robot Fleet Simulation package',
)

