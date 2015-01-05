# coding: utf-8
"""
    holocron.app
    ~~~~~~~~~~~~

    This module implements the central Holocron application class.

    :copyright: (c) 2014 by the Holocron Team, see AUTHORS for details.
    :license: 3-clause BSD, see LICENSE for details.
"""

import os
import shutil
import logging

import jinja2

from dooku.conf import Conf
from dooku.decorator import cached_property
from dooku.ext import ExtensionManager

from .content import create_document
from .utils import iterfiles


logger = logging.getLogger(__name__)


class Holocron(object):
    """
    The Holocron object implements a blog instance.

    Once it's created it will act as a central registry for the extensions,
    converters, template configuration and much more.

    Here the interaction workflow for an end-user:

    * create instance with default/custom configuration
    * register extensions: converters and/or generators
    * call :meth:`run` method in order to build weblog

    :param conf: (dict) a user configuration, that overrides a default one
    """

    #: The factory function that is used to create a new document instance.
    document_factory = create_document

    #: Default configuration parameters.
    default_conf = {
        'sitename': 'Obi-Wan Kenobi',
        'siteurl': 'http://obi-wan.jedi',
        'author': 'Obi-Wan Kenobi',

        'encoding': 'utf-8',

        'paths': {
            'content': './',
            'output': '_build/',
            'theme': '_theme/',
        },

        'theme': {
            'navigation': [
                ('feed', '/feed.xml'),
            ],
        },

        'converters': {
            'enabled': ['markdown'],

            'markdown': {
                'extensions': ['codehilite', 'extra'],
            },
        },

        'generators': {
            'enabled': ['sitemap', 'blog'],

            'blog': {
                'feed': {
                    'save_as': 'feed.xml',
                    'posts_number': 5,
                },

                'index': {
                    'save_as': 'index.html',
                },

                'tags': {
                    'output': 'tags/',
                    'save_as': 'index.html',
                },
            },
        },

        'commands': {
            'serve': {
                'host': '0.0.0.0',
                'port': '5000',
            },
        },
    }

    def __init__(self, conf=None):
        #: The configuration dictionary.
        self.conf = Conf(self.default_conf, conf or {})

        #: A `file extension` -> `converter` map
        #:
        #: Holds a dicionary of all registered converters, that is used to
        #: getting converter for the :class:`holocron.content.Document`.
        self._converters = {}

        #: Holds a dictionary of all registered generators. The dict is used
        #: to prevent generator double registration.
        self._generators = {}

        # Register enabled converters in the application instance.
        for _, ext in ExtensionManager(
            namespace='holocron.ext.converters',
            names=self.conf['converters']['enabled'],
        ):
            self.register_converter(ext)

        # Register enabled generators in the application instance.
        for _, ext in ExtensionManager(
            namespace='holocron.ext.generators',
            names=self.conf['generators']['enabled'],
        ):
            self.register_generator(ext)

    def register_converter(self, converter_class, _force=False):
        """
        Registers a converter on the application.

        :param converter_class: a converter class to register
        :param _force: allows to override already registered converters
        """
        converter = converter_class(self.conf['converters'])

        for ext in converter.extensions:
            if ext in self._converters and not _force:
                logger.warning(
                    '%s converter: skipped for %s: already registered',
                    converter_class.__name__, ext)
                continue

            self._converters[ext] = converter

    def register_generator(self, generator_class, _force=False):
        """
        Registers a given generator on the application.

        :param generator_class: a generator class to register
        :param _force: re-register a generator, if it's already registered
        """
        if generator_class in self._generators and not _force:
            logger.warning(
                '%s generator: skipped: already registered',
                generator_class.__name__)
            return

        self._generators[generator_class] = generator_class(self)

    @cached_property
    def jinja_env(self):
        """
        Gets a Jinja2 environment based on Holocron's settings.
        Calculates only once, since it's a cached property.
        """
        # makes a default template loader
        templates_path = os.path.join('themes', 'default', 'templates')
        loader = jinja2.PackageLoader('holocron', templates_path)

        # PrefixLoader provides a direct access to the default templates
        loaders = [loader, jinja2.PrefixLoader({'!default': loader})]

        # makes a user template loader
        path = self.conf.get('paths.theme')
        if path is not None:
            path = os.path.join(path, 'templates')
            loaders.insert(0, jinja2.FileSystemLoader(path))

        env = jinja2.Environment(
            loader=jinja2.ChoiceLoader(loaders), extensions=['jinja2.ext.do'])
        env.globals.update(
            # pass some useful conf options to the template engine
            sitename=self.conf['sitename'],
            siteurl=self.conf['siteurl'],
            author=self.conf['author'],
            theme=self.conf['theme'],

            # TODO: I'm not a very fun of this hack, but it looks
            # like it is only solution we have to make possible
            # to change some attributes inside Template engine.
            setattr=setattr,
        )
        return env

    def run(self):
        """
        Starts build process.
        """
        # iterate over files in the content directory
        # except files/dirs starting with underscore or dot
        documents_paths = list(
            iterfiles(self.conf['paths.content'], '[!_.]*', True))

        # consequently builds all found documents
        documents = []
        for index, document_path in enumerate(documents_paths):
            try:
                percent = int((index + 1) * 100.0 / len(documents_paths))
                # TODO (@ikalnitsky):
                #   Rethink document factory through the class. Should be
                #   more flexible and nifty.
                document = Holocron.document_factory(document_path, self)
                print('[{percent:>3d}%] Building {doc}'.format(
                    percent=percent, doc=document.short_source))

                document.build()
                documents.append(document)

            except Exception:
                logger.warning(
                    'File %s is invalid. Building skipped.', document_path)

        # use generators to generate additional stuff
        for _, generator in self._generators.items():
            generator.generate(documents)

        self._copy_theme()

    def _copy_theme(self):
        """
        Copy theme's static files to the output folder. If the user's statics
        aren't exists then base statics will be copied.
        """
        root = os.path.dirname(__file__)

        base_static = os.path.join(root, 'themes', 'default', 'static')
        user_static = os.path.join(self.conf['paths.theme'], 'static')

        if not os.path.exists(user_static):
            user_static = base_static
        out_static = os.path.join(self.conf['paths.output'], 'static')

        shutil.rmtree(out_static, ignore_errors=True)
        shutil.copytree(user_static, out_static)
