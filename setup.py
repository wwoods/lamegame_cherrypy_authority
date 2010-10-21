from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(name='lamegame_cherrypy_authority',
      version=version,
      description="Authentication and authorization package for cherrypy.",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='cherrypy lamegame authentication authorization openid',
      author='Walt Woods',
      author_email='woodswalben@gmail.com',
      url='http://www.lamegameproductions.com',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      package_data = {
        '': ['static/*']
      },
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      test_suite='tests'
      )
