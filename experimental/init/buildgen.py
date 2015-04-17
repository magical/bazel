# Copyright 2015 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Experiment on generating a tools package from bazel
#
"""bazel-init prototype build file generation helpers."""

import os

class BuildSerializable(object):
  """An object that can serialize into a valid-build file structure."""
  
  def __init__(self, _name, _first=None, **kwargs):
    self.name = _name
    self.kwargs = kwargs
    self.first = _first

  @staticmethod
  def __escape(astring):
    return astring.replace("\\", "\\\\").replace("\n", "\\n").replace(
        "\"", "\\\"").replace("\'", "\\\'")

  @staticmethod
  def __serialize(obj, prefix):
    subprefix = prefix + "    "
    if isinstance(obj, list):
      result = "%s[\n" % prefix
      for item in obj:
        result = "%s%s,\n" % (result,
                              BuildSerializable.__serialize(item, subprefix))
      result = "%s%s]" % (result, prefix)
      return result
    elif isinstance(obj, dict):
      result = "%s{\n" % prefix
      for key, value in obj:
        result = "%s%s: %s,\n" % (
            result,
            BuildSerializable.__serialize(key, subprefix),
            BuildSerializable.__serialize(value, subprefix). strip()
            )
      result = "%s%s}" % (result, prefix)
    elif isinstance(obj, BuildSerializable):
      return obj.serialize(prefix)
    else:
      return "%s\"%s\"" % (prefix, BuildSerializable.__escape(obj.__str__()))

  def serialize(self, prefix=""):
    result = "%s(\n" % self.name
    newprefix = prefix + "    "
    if self.first is not None:
      result = "%s%s%s,\n" % (result, newprefix, self.first)
    for name, value in self.kwargs.iteritems():
      result = "%s%s%s = %s,\n" % (result, newprefix, name,
                                   self.__serialize(value, "    ").strip())
    return "%s%s)\n" % (result, prefix)


class BuildGeneratorLabel(BuildSerializable):
  """A serializable object that output the string representation of a label."""

  def __init__(self, package, name, parent=None):
    BuildSerializable.__init__(self, name)
    self.package = package
    self.name = name
    self.parent = parent

  def serialize(self, prefix=""):
    if self.parent is not None:
      return "%s\"%s\"" % (prefix, self.parent.bind(self.package, self.name))
    else:
      return "%s\"//%s:%s\"" % (prefix, self.package, self.name)


class BuildGeneratorHelper(object):
  """A helper class to ease the generation of a package."""

  def __init__(self, package, parent=None):
    self.repositories = {}
    self.rules = []
    self.bindings = {}
    self.workspace = []
    self.embedded = []
    self.files = {}
    self.package = package
    self.parent = parent

  def rule(self, _name, **kwargs):
    """Create a rule and returns its label."""
    self.rules.append(BuildSerializable(_name, **kwargs))
    return BuildGeneratorLabel(self.package, kwargs["name"], self.parent)

  @staticmethod
  def glob(pattern, **kwargs):
    """Returns a serializable object that serialize to a glob()."""
    return BuildSerializable("glob", pattern, **kwargs)

  @staticmethod
  def select(dictionary):
    """Returns a serializable object that serialize to a select()."""
    return BuildSerializable("select", dictionary)

  def exports_embedded(self, name):
    """Export a file that was embedded in Bazel binary."""
    self.embedded.append(name)
    self.rules.append(BuildSerializable("exports_files", [name]))

  def scratch_file(self, name, content = ""):
    self.files[name] = content

  def new_repository(self, _rule, **kwargs):
    """Create a repository rule that support build_file.

    Examples of such rules are new_local_repository or new_http_archive.

    Args:
        _rule: the type of the rule, e.g., new_local_repository.
        **kwargs: the various attributes of the rule.

    Returns:
        A helper to construct the build file associated with that rule.
    """
    name = kwargs["name"]
    build_file = self.package + os.path.sep + "BUILD." + name
    newname = "%s-%s" % (self.package.replace("/", "-"), name)
    kwargs["name"] = newname
    kwargs["build_file"] = build_file
    self.workspace.append(BuildSerializable(_rule, **kwargs))
    self.repositories[name] = BuildGeneratorHelper("@" + newname, self)
    return self.repositories[name]

  def bind(self, package, name):
    if name not in self.bindings:
      self.bindings[name] = BuildSerializable(
          "bind",
          name=self.package + "/" + name,
          actual=package + ":" + name)
    return "//external:%s/%s" % (self.package, name)

  def __build_file(self):
    """Generate the corresponding build file."""
    result = """# This file was auto-generated. Do not edit.
# If you wish to overwrite this package, copy the package
# into your workspace
package(default_visibility = ["//visibility:public"])
"""
    for rule in self.rules:
      result = "%s\n%s" % (result, rule.serialize())
    return result

  def __workspace_file(self):
    """Generate the WORKSPACE file part."""
    result = """#
# Generated part from package %s
#
""" % self.package
    for rule in self.workspace:
      result = "%s\n%s" % (result, rule.serialize())
    for _, rule in self.bindings.iteritems():
      result = "%s\n%s" % (result, rule.serialize())
    return result

  def generate(self, helper):
    """Do the actual generation."""
    helper.build_file(self.__build_file())
    for key, repository in self.repositories.iteritems():
      helper.scratch_file("BUILD." + key, repository.__build_file())
    for name in self.embedded:
      helper.copy_from_embedded(name)
    for name, content in self.files.iteritems():
      helper.scratch_file(name, content)
    helper.workspace_part(self.__workspace_file())
