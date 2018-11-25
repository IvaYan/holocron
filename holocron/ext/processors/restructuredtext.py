"""Convert reStructuredText into HTML."""

import os

import schema
from docutils.core import publish_parts
from docutils.writers import html5_polyglot
from docutils import nodes

from ._misc import iterdocuments, parameters


@parameters(
    schema={
        'when': schema.Or([{str: object}], None, error='unsupported value'),
        'docutils': schema.Schema({str: object}),
    }
)
def process(app, documents, when=None, docutils={}):
    settings = dict(
        {
            # We need to start heading level with <h2> in case there are
            # few top-level sections, because it simply means there's no
            # title.
            'initial_header_level': 2,

            # Docutils is designed to convert reStructuredText files to
            # other formats such as, for instance, HTML. That's why it
            # produces full-featured HTML with embed CSS. Since we are
            # going to use our own templates we are not interested in
            # getting the whole HTML output. So let's turn off producing
            # a stylesheet and save both memory and CPU cycles.
            'embed_stylesheet': False,

            # Docutils uses Pygments to highlight code blocks, and the
            # later can produce HTML marked with either short or long
            # CSS classes. There are a lot of colorschemes designed for
            # the former notation, so it'd be better to use it in order
            # simplify customization flow.
            'syntax_highlight': 'short',
        },
        **docutils)

    for document in iterdocuments(documents, when):
        # Writer is mutable so we can't share the same instance between
        # conversions.
        writer = html5_polyglot.Writer()

        # Unfortunately we are not happy with out-of-box conversion to
        # HTML. For instance, we want to see inline code to be wrapped
        # into <code> tag rather than <span>. So we need to use custom
        # translator to fit our needs.
        writer.translator_class = _HTMLTranslator

        parts = publish_parts(
            document['content'], writer=writer, settings_overrides=settings)

        document['content'] = parts['fragment'].strip()
        document['destination'] = \
            '%s.html' % os.path.splitext(document['destination'])[0]

        # Usually converters go after frontmatter processor and that
        # means any explicitly specified attribute is already set on
        # the document. Since frontmatter processor is considered to
        # have a higher priority, let's set 'title' iff it does't
        # exist.
        if 'title' not in document and parts.get('title'):
            document['title'] = parts['title']

    return documents


class _HTMLTranslator(html5_polyglot.HTMLTranslator):
    """Translate reStructuredText nodes to HTML."""

    # skip <div class="section"> wrapper around sections

    def visit_section(self, node):
        self.section_level += 1

    def depart_section(self, node):
        self.section_level -= 1

    # wrap inline code into <code> tag rather than <span>

    def visit_literal(self, node):
        self.body.extend(['<code>', node.astext(), '</code>'])

        # HTML tag has been produced and any further processing is not
        # required anymore.
        raise nodes.SkipNode
