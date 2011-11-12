from setuptools import setup, find_packages
import sys, os

if __name__ == '__main__':
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
          packages=find_packages(exclude=['*.test','*.test.*']),
          include_package_data=True,
          package_data = {
              # Non-.py files to distribute as part of each package
              'lg_authority': ['static/*','templates/*']
          },
          data_files = [
              # Loose files to distribute with install
              # List of tuples of (destFolder, [ local_files ])
          ],
          zip_safe=False,
          install_requires=[
              # -*- Extra requirements: -*-
          ],
          entry_points="""
          # -*- Entry points: -*-
          """
          )
