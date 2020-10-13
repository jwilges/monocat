import codecs
import distutils
import importlib
import re
import subprocess
import sys
from pathlib import Path
from typing import List, MutableMapping, Optional, Sequence, Type

import setuptools
import setuptools.command.build_py


def read(source_file_name: Path):
    if not source_file_name.is_file():
        raise FileNotFoundError(source_file_name)
    with codecs.open(str(source_file_name), 'r') as source_file:
        return source_file.read()


HERE = Path().parent.absolute()
PACKAGE_PATH = HERE / 'monocat'

LONG_DESCRIPTION = read(HERE / 'README.md')
METADATA = {
    'name': 'monocat',
    'version': '0.5.0',
    'author': 'Jeffrey Wilges',
    'author_email': 'jeffrey@wilges.com',
    'description': 'monocat is a command line utility for managing GitHub releases',
    'url': 'https://github.com/jwilges/monocat',
    'license': 'BSD'
}

OPTIONAL_COMMAND_CLASSES: MutableMapping[str, Type] = {}
OPTIONAL_COMMAND_OPTIONS: MutableMapping[str, MutableMapping[str, Sequence[str]]] = {}

try:
    from sphinx.setup_command import BuildDoc
    OPTIONAL_COMMAND_CLASSES['build_sphinx'] = BuildDoc
    OPTIONAL_COMMAND_OPTIONS['build_sphinx'] = {
        'source_dir': ('setup.py', 'docs'),
        'build_dir': ('setup.py', 'docs/_build')
    }
except ImportError:
    pass


class AddMetadataCommand(distutils.cmd.Command):
    description = 'Add `__metadata__` module'
    user_options = [
        ('local', None, 'enable local version label'),
    ]

    def initialize_options(self):
        self.local = None

    def finalize_options(self):
        pass

    def run(self):
        if self.local:
            try:
                git_process = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                                            check=False, capture_output=True, universal_newlines=True)
            except OSError:
                identifier = 'local'
            else:
                if git_process.returncode == 0:
                    identifier = git_process.stdout.strip()

            METADATA['version'] += f'+{identifier}'

        METADATA_PATH = Path(PACKAGE_PATH / '__metadata__.py')

        with open(METADATA_PATH, 'w') as metadata_module:
            metadata_module.writelines([f"{key.upper()} = '{value}'\n" for key, value in METADATA.items()])


class BuildMetadataCommand(setuptools.command.build_py.build_py):
    def run(self):
        AddMetadataCommand(self.distribution).run()
        super().run()


class ValidateTagCommand(distutils.cmd.Command):
    """A validator that ensures the package version both is in the canonical forma per
    PEP-440 and matches the current git tag"""
    description = 'validate that the package version matches the current git tag'
    user_options: List[Optional[str]] = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """Warn and exit if the package version either:
            a) is not in the canonical format per PEP-440 or,
            b) does not match any HEAD git tag version."""
        git_tag_process = subprocess.run(['git', 'tag', '--list', '--points-at', 'HEAD'],
                                         check=False, capture_output=True, universal_newlines=True)

        if git_tag_process.returncode != 0:
            self.warn(f'failed to execute `git tag` command')
            sys.exit(git_tag_process.returncode)

        git_tags = [tag.strip().lstrip('v') for tag in git_tag_process.stdout.splitlines()]
        version = METADATA['version']
        if version not in git_tags:
            self.warn(f'package version ({version}) does not match any HEAD git tag version (tag versions: {git_tags})')
            sys.exit(1)

        if not self.is_canonical(version):
            self.warn(f'package version ({version}) is not in the canonical format per PEP-440')
            sys.exit(1)

    @staticmethod
    def is_canonical(version: str) -> bool:
        """Return true if `version` is canonical per PEP-440."""
        return re.match(r'^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?$', version) is not None


setuptools.setup(
    **METADATA,
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(exclude=['tests*']),
    entry_points={
        'console_scripts': ['monocat=monocat.cli:main'],
    },
    python_requires='>=3.6',
    install_requires=[
        'pydantic>=1.4',
        'uritemplate>=3',
        'urllib3',
        'dataclasses; python_version < "3.7"'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Build Tools',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Networking',
        'Topic :: System :: Software Distribution',
        'Topic :: Utilities'
    ],
    cmdclass={
        'add_metadata': AddMetadataCommand,
        'build_py': BuildMetadataCommand,
        'validate_tag': ValidateTagCommand,
        **OPTIONAL_COMMAND_CLASSES
    },
    command_options={
        **OPTIONAL_COMMAND_OPTIONS
    },
)
