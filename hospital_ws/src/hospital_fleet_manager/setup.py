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
        (os.path.join('share', package_name, 'launch'), glob(os.path.join(package_name, 'launch', '*.py'))),
        (os.path.join('share', package_name, 'worlds'), glob(os.path.join(package_name, 'worlds', '*'))),
        (os.path.join('share', package_name, 'models'), glob(os.path.join(package_name, 'models', '*'))),
        (os.path.join('share', package_name, 'config'), glob(os.path.join(package_name, 'config', '*'))),
        (os.path.join('share', package_name, 'maps'), glob(os.path.join(package_name, 'maps', '*'))),
    ],
    install_requires=[
        'setuptools',
        'numpy',
        'scipy',
        'networkx',
        'scikit-learn',
        'joblib',
        'pyyaml',
        'flask',
    ],
    zip_safe=True,
    author='AI Hospital Team',
    description='AI-Based Hospital Robot Fleet Simulation package',
)
