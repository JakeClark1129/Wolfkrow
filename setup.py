from setuptools import setup, find_packages

packages = find_packages(where="src", include=["wolfkrow", "wolfkrow.*"])

setup(
    name='wolfkrow',
    version='1.0.0',
    description='Wolfkrow is a Task execution engine, which allows users to easily string a series of tasks together in order to create a workflow.',
    url='https://github.com/JakeClark1129/Wolfkrow',
    author='Jacob Clark',
    author_email='jakeclark1129@gmail.com',
    license='GNU GPLv3',
    packages=packages,
    entry_points={
        'console_scripts': [
            'wolfkrow_run_task=wolfkrow.core.engine.wolfkrow_run_task:main',
        ],
    },
    package_dir={
        "": "src"
    },
    install_requires=[
        'deadline', # TODO: This isn't really a real requirement.
        'networkx',
        'yaml', # I think this should probably be PyYaml.
    ],
)
