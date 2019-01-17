# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages


def read_requirements(filename):
    specifiers = []
    dep_links = []

    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('-r') or line.strip() == '':
                continue
            if line.startswith('git+'):
                dep_links.append(line.strip())
            else:
                specifiers.append(line.strip())

    return specifiers, dep_links


setup_py_path = os.path.dirname(os.path.realpath(__file__))
requirements_file = os.path.join(setup_py_path, 'requirements.txt')
test_requirements_file = os.path.join(setup_py_path, 'test-requirements.txt')
install_requires, deps_links = read_requirements(requirements_file)
tests_require, _ = read_requirements(test_requirements_file)
if _:
    deps_links.extend(_)


setup(name='moksha-monitor-exporter',
      description=('A nanoservice written in Python providing Prometheus '
                   'export(s) from moksha.monitoring.socket data.'),
      version='0.0.1',
      classifiers=[
          "Programming Language :: Python",
      ],
      keywords='moksha monitoring socket prometheus exporter flask',
      author='The Factory 2.0 Team',
      author_email='fivaldi@redhat.com',
      url='https://github.com/redhat-developer/moksha-monitor-exporter',
      license='MIT',
      packages=find_packages(exclude=['tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      tests_require=tests_require,
      dependency_links=deps_links,
      )
