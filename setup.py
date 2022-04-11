from setuptools import setup, find_packages

DEPENDENCIES = [
    'requests',
    'boto3',
    'idna-ssl',
    'slackclient',
]

STYLE_REQUIRES = [
    'flake8',
    'pylint',
]

TEST_REQUIRES = [
    'mock',
    'moto',
    'pytest',
]

EXTRAS_REQUIRE = {
    'test': TEST_REQUIRES,
    'style': STYLE_REQUIRES,
    'lint': STYLE_REQUIRES,
    'test-requirements': TEST_REQUIRES + STYLE_REQUIRES,
}

setup(
    name='cr-universal-translator',
    description='Slack Translator App',
    keywords='slack bot translate',
    version='0.1.0',
    install_requires=DEPENDENCIES,
    tests_require=TEST_REQUIRES + STYLE_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    include_package_data=True,
    packages=find_packages(exclude=['tests']),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    license='All rights reserved',
    author='Jim Rosser',
    maintainer_email='jarosser06@gmail.com',
    url='https://github.com/jarosser06/slack-inline-translator',
)
