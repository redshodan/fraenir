import os
import runpy

from setuptools import setup, find_packages

# Extract the version from the code
here = os.path.abspath(os.path.dirname(__file__))
VERSION = runpy.run_path(os.path.join(here, "fraenir/version.py"))["VERSION"]


def requirements(filename):
    if os.path.exists(filename):
        return [l for l in open(filename).read().splitlines()
                    if not l.startswith("#") and not l.startswith("git+")]
    else:
        return ""


setup(name='fraenir',
      version=VERSION,
      description='A matrix bot',
      long_description="",
      classifiers=[
          "Operating System :: POSIX",
          "Natural Language :: English",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Development Status :: 3 - Alpha",
          ],
      author='Chris Newton',
      author_email='redshodan@gmail.com',
      url='https://github.com/redshodan',
      keywords=["matrix", "python", "bot"],
      packages=find_packages(),
      python_requires='>=3.6',
      include_package_data=True,
      zip_safe=False,
      platforms=["Any"],
      test_suite='fraenir',
      install_requires=requirements("requirements.txt"),
      setup_requires=['pytest-runner'],
      tests_require=requirements("requirements-test.txt"),
      license="GPLv2",
      entry_points={'console_scripts': ['fraenir = fraenir.__main__:run']},
      )
