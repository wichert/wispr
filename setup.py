from setuptools import find_packages
from setuptools import setup

version = '1.0'

setup(
        version=version,
        name='wispr',
        description='WISPr command line client',
        long_description=open('README.rst').read(),
        keywords='wispr wifi hotspot',
        classifiers=[
            'Environment :: Console',
            'License :: DFSG approved',
            'License :: OSI Approved :: BSD License',
            'Operating System :: OS Independent',
            'Intended Audience :: End Users/Desktop',
        ],
        author='Wichert Akkerman',
        author_email='wichert@wiggy.net',
        url='https://github.com/wichert/wispr',
        license='BSD',
        packages=find_packages('src'),
        package_dir={'': 'src'},
        install_requires=[
            'requests',
        ],
        entry_points='''
        [console_scripts]
        wispr = wispr:main
        ''')
