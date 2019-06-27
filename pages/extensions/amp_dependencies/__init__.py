# -*- coding: utf-8 -*-
from sets import Set
import requests

from grow import extensions
from grow.documents import document, static_document
from grow.extensions import hooks

COMPONENT_VERSIONS_URL = 'https://playground.amp.dev/api/amp-component-versions'
# The latest component versions if no explicit version is set
COMPONENT_VERSIONS = requests.get(COMPONENT_VERSIONS_URL).json()
# Default version to use if it is not in the set of known components
DEFAULT_VERSION = '0.1'

# Used to determine where to print the script tags
PLACEHOLDER = '__AMP__DEPENDENCIES__'


class AmpDependencies(object):
  def __init__(self, doc):
    self._doc = doc
    self._pod = doc.pod
    # Stores registered dependencies
    self._dependencies = Set()
    # Can be used to determine if the deps have already been injected
    self.injected = False


  def __repr__(self):
    return '<AmpDependencies>'

  def add(self, name, version=None, type='element'):
    if version is None:
      version = COMPONENT_VERSIONS.get(name, DEFAULT_VERSION)

    src = 'https://cdn.ampproject.org/v0/{name}-{version}.js'.format(name=name, version=version)
    tag = '<script custom-{type}="{name}" src="{src}" async></script>'.format(type=type, name=name, src=src)

    self._dependencies.add(tag)
    return ''

  def emit(self):
    return PLACEHOLDER

  def inject(self, content):
    # Check wether the content has the placeholder
    if PLACEHOLDER not in content or self.injected:
      return content

    self.injected = True
    dependencies = ''.join(self._dependencies)
    return content.replace(PLACEHOLDER, dependencies)


class AmpDependenciesPreRenderHook(hooks.PreRenderHook):
  """Handle the post-render hook."""

  def should_trigger(self, previous_result, doc, original_body, *_args,
                       **_kwargs):
    """Only run for documents with contents"""

    # Check that it's not a StaticDocument
    if isinstance(doc, static_document.StaticDocument):
      return False

    return True

  def trigger(self, previous_result, doc, raw_content, *_args, **_kwargs):
    amp_dependencies = AmpDependencies(doc)
    setattr(doc, 'amp_dependencies', amp_dependencies)

    return previous_result if previous_result else raw_content


class AmpDependenciesPostRenderHook(hooks.PostRenderHook):
  """Handle the post-render hook."""

  def should_trigger(self, previous_result, doc, original_body, *_args,
                       **_kwargs):
    """Only needs to trigger if pre-render hook added a dependency set
    and there is content to render"""
    # Do not run for empty documents
    content = previous_result if previous_result else original_body
    if content is None:
      return False

    # Check that it's not a StaticDocument
    if isinstance(doc, static_document.StaticDocument):
      return False

    return True

  def trigger(self, previous_result, doc, raw_content, *_args, **_kwargs):
    content = previous_result if previous_result else raw_content

    amp_dependencies = getattr(doc, 'amp_dependencies')
    content = amp_dependencies.inject(content)

    return content


class AmpDependenciesExtension(extensions.BaseExtension):
  """AMP Dependencies Extension."""

  def __init__(self, pod, config):
    super(AmpDependenciesExtension, self).__init__(pod, config)

  @property
  def available_hooks(self):
    """Returns the available hook classes."""
    return [
      AmpDependenciesPreRenderHook,
      AmpDependenciesPostRenderHook,
    ]