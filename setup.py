from setuptools import setup

version = '1.0'

setup(
        name='wispr',
        description='WISPr command line client',
        long_description='',
        classifiers=[],
        author='Wichert Akkerman',
        author_email='wichert@wiggy.net',
        url='https://github.com/wichert/wispr',
        license='BSD',
        entry_points='''
        [console_scripts]
        wispr = wispr:main
        ''')
