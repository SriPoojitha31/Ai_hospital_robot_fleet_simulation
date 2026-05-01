from setuptools import setup
import os
from glob import glob

package_name = 'hospital_fleet_manager'


def _files(pattern, recursive=False):
    return [p for p in glob(pattern, recursive=recursive) if os.path.isfile(p)]

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    include_package_data=True,
    data_files=[
        ('share/ament_index/resource_index/packages', [os.path.join('resource', package_name)]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name), _files(os.path.join('resource', package_name))),
        (os.path.join('share', package_name, 'launch'), _files(os.path.join(package_name, 'launch', '*.py'))),
        (os.path.join('share', package_name, 'worlds'), _files(os.path.join(package_name, 'worlds', '*'))),
        (os.path.join('share', package_name, 'models'), _files(os.path.join(package_name, 'models', '*'))),
        (os.path.join('share', package_name, 'models'), _files(os.path.join(package_name, 'models', '**', '*'), recursive=True)),
        (os.path.join('share', package_name, 'models', 'hospital_robot'), _files(os.path.join(package_name, 'models', 'hospital_robot', '*'))),
        (os.path.join('share', package_name, 'config'), _files(os.path.join(package_name, 'config', '*'))),
        (os.path.join('share', package_name, 'maps'), _files(os.path.join(package_name, 'maps', '*'))),
        (os.path.join('share', package_name, 'config'), _files(os.path.join(package_name, 'config', '**', '*'), recursive=True)),
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
        'prometheus-client',
    ],
    zip_safe=True,
    author='AI Hospital Team',
    description='AI-Based Hospital Robot Fleet Simulation package',
    entry_points={
        'console_scripts': [
            'fleet_scheduler = hospital_fleet_manager.fleet_scheduler:main',
            'robot_simulator = hospital_fleet_manager.robot_simulator:main',
            'dashboard = hospital_fleet_manager.dashboard:main',
            'dashboard_visual = hospital_fleet_manager.dashboard_visual:main',
        ],
    },
)
