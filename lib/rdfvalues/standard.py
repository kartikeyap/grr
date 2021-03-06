#!/usr/bin/env python
"""Standard RDFValues."""


import re
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.proto import jobs_pb2


class RegularExpression(rdfvalue.RDFString):
  """A semantic regular expression."""

  def ParseFromString(self, value):
    super(RegularExpression, self).ParseFromString(value)

    # Check that this is a valid regex.
    try:
      self._regex = re.compile(self._value, flags=re.I | re.S | re.M)
    except re.error:
      raise type_info.TypeValueError("Not a valid regular expression.")

  def Search(self, text):
    """Search the text for our value."""
    return self._regex.search(text)

  def Match(self, text):
    return self._regex.match(text)

  def FindIter(self, text):
    return self._regex.finditer(text)

  def __str__(self):
    return "<RegularExpression: %r/>" % self._value


class EmailAddress(rdfvalue.RDFString):
  """An email address must be well formed."""

  _EMAIL_REGEX = re.compile(r"[^@]+@([^@]+)$")

  def ParseFromString(self, value):
    super(EmailAddress, self).ParseFromString(value)

    self._match = self._EMAIL_REGEX.match(self._value)
    if not self._match:
      raise ValueError("Email address %r not well formed." % self._value)


class DomainEmailAddress(EmailAddress):
  """A more restricted email address may only address the domain."""

  def ParseFromString(self, value):
    super(DomainEmailAddress, self).ParseFromString(value)

    domain = config_lib.CONFIG["Logging.domain"]
    if domain and self._match.group(1) != domain:
      raise ValueError(
          "Email address '%s' does not belong to the configured "
          "domain '%s'" % (self._match.group(1), domain))


class AuthenticodeSignedData(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.AuthenticodeSignedData


class PersistenceFile(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.PersistenceFile
