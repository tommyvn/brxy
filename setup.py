from setuptools import setup, find_packages

setup(
    name='pullproxy',
    version='0.0.1',
    description='Super double reverse proxy micro loadbalancer from the future',
    url='http://github.com/drie/pullproxy',
    author='Tom van Neerijnen',
    author_email='tom@tomvn.com',
    keywords='proxy serverless',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
    ],
    packages=find_packages(exclude=['tests*']))
