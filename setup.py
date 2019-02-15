from setuptools import setup

setup(name='mapmanager',
      version='0.1',
      description="Sync your gmod maps in sync with a server's listing",
      url='http://github.com/krzygorz/MapManager',
      author='krzygorz',
      author_email='krzygorz@gmail.com',
      license='MIT',
      packages=['mapmanager'],
      install_requires=['beautifulsoup4'],
      zip_safe=True,
      entry_points = {
        'console_scripts': ['mapmanager=mapmanager.cli:main'],
      },
      )