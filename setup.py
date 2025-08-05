# /projects/myutils/setup.py

from setuptools import setup, find_packages

setup(
    name='myutils',
    version='0.1.0',
    packages=find_packages(),  # __init__.pyがあるディレクトリを探してくれる
    description='共通ユーティリティ関数',
    author='あなたの名前',
    install_requires=['pygame']
)
