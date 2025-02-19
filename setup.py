from distutils.command.build import build

from setuptools import setup
from setuptools_npm import npm_not_skipped


class custom_build(build):
    sub_commands = [
        ("compile_catalog", lambda x: True),
        ("npm_install", npm_not_skipped),
        ("npm_run", npm_not_skipped),
    ] + build.sub_commands


def main():
    setup(test_suite='tests.settings.run', cmdclass={"build": custom_build})


if __name__ == "__main__":
    main()
