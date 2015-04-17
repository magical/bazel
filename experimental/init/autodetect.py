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
# Autodetection helpers
#
"""bazel-init prototype autodetection helpers."""

import os
import re
import stat
import subprocess

try:
    from subprocess import FNULL
except ImportError:
    FNULL = open(os.devnull, 'wb')

class AutodetectFailure(Exception):
  """Exception to be thrown on an autodetect failure."""

  def __init__(self, value):
    Exception.__init__(self)
    self.value = value

  def __str__(self):
    return repr(self.value)


class AutodetectHelper(object):
  """Helper for the autodetection part.

     It provides various generic methods for auto detection.
  """

  @staticmethod
  def fail(msg):
    raise AutodetectFailure(msg)

  @staticmethod
  def version_compare(version1, version2):
    """Compare two versions expressed as a dot separated version number.

    Args:
      version1: A first string version, e.g. '1.2.3'.
      version2: A second string version, e.g. '1.3'.

    Returns:
      A integer that can take the following values:
        -1 if version1 < version2, e.g.,
           version_compare('1.7.0', '2') == -1
        0 if version1 == version2, e.g.,
          version_compare('2.3.1', '2.1') == 1,
        1 if version1 > version2. e.g.,
          version_compare('1.2', '1.2') == 0.
    """
    ver1 = version1.split(".")
    ver2 = version2.split(".")
    for i in range(0, min(len(ver1), len(ver2))):
      if ver1[i] > ver2[i]:
        return 1
      elif ver1[i] < ver2[i]:
        return -1
    if len(ver1) < len(ver2):
      return -1
    elif len(ver1) > len(ver2):
      return 1
    else:
      return 0

  @staticmethod
  def which(prog):
    """Try to find the path of a program using the PATH environment variable.

    Args:
      prog: the base name of the program e.g. 'java'

    Returns:
      The path to prog according to the PATH environment variable (e.g.
      '/usr/lib/jvm/jdk1.7.0/bin/java`) or None if no such program exists
      in the PATH.
    """
    if "PATH" in os.environ:
      for s in os.environ["PATH"].split(os.pathsep):
        path = os.path.join(s, prog)
        if os.path.exists(path) and (stat.S_IXUSR
                                     & os.stat(path)[stat.ST_MODE]):
          return path
    return None

  @staticmethod
  def __process_flags(astr, strip_option=None):
    """Split a flag list, eventually removing option"""
    result = []
    for opt in astr.split(" "):
      opt = opt.strip()
      if strip_option is not None and opt.startswith(strip_option):
        if opt != strip_option:
          result.append(opt[len(strip_option):])
      else:
        result.append(opt)
    return [s.strip() for s in result if s.strip()]

  @staticmethod
  def pkg_config(name, atleast_version=None, exact_version=None,
                max_version=None):
    """Run pkg-config asking for library `name`.

    Args:
      name: the library name to pass to pkg-config.
      atleast_version: value to pass to pkg-config --atleast-version flag.
      exact_version: value to pass to pkg-config --exact-version flag.
      max_version: value to pass to pkg-config --max-version flag.

    Returns:
      A dictionary that contains the following keys:
      - library_dirs are the list of directory as passed with the -L flag
      - libraries are the list of libraries as passed with the -l flag
      - ldflags are non library flags given to the linker
      - include_dirs are include directories as passed with the -I flag
      - cflags are non include flags given to the compiler
      - variables is a dictionary of all variables for this library
      The return value is None when the library was not found by pkg-config
      or pkg-config failed to execute.
    """
    pkg_config = AutodetectHelper.which("pkg-config")
    if pkg_config is None:
      return None
    test = "--exists"
    if exact_version is not None:
      test = "--exact-version=%s" % exact_version
    elif atleast_version is not None:
      test = "--atleast-version=%s" % atleast_version
    elif max_version is not None:
      test = "--max-version=%s" % max_version

    if subprocess.call([pkg_config, test, name]) != 0:
      return None
    if atleast_version is not None and max_version is not None:
      # Check --max-version because both atleast and max where provided.
      if subprocess.call([pkg_config, "--max-version=%s" % max_version,
                          name]) != 0:
        return None

    # Constructs the result
    result = {}
    result["library_dirs"] = AutodetectHelper.__process_flags(
        subprocess.check_output([pkg_config, "--libs-only-L", name]), "-L")
    result["libraries"] = AutodetectHelper.__process_flags(
        subprocess.check_output([pkg_config, "--libs-only-l", name]), "-l")
    result["ldflags"] = AutodetectHelper.__process_flags(
        subprocess.check_output([pkg_config, "--libs-only-other", name]))
    result["include_dirs"] = AutodetectHelper.__process_flags(
        subprocess.check_output([pkg_config, "--cflags-only-I", name]), "-I")
    result["cflags"] = AutodetectHelper.__process_flags(
        subprocess.check_output([pkg_config, "--cflags-only-other", name]))
    variables = subprocess.check_output([pkg_config, "--print-variables", name])
    result["variables"] = {}
    for var in variables.splitlines():
      result["variables"][var] = subprocess.check_output(
        [pkg_config, "--variable=%s" % var, name]).strip()
    return result

  @staticmethod
  def brew_prefix(package):
    """Returns the prefix of the given package."""
    brew = AutodetectHelper.which("brew")
    try:
      if brew is not None:
        return subprocess.check_output([brew, "--prefix", package], stderr=FNULL
                                       ).strip()
    except subprocess.CalledProcessError:
      pass

  @staticmethod
  def port_content(package):
    """Returns the list of files of a port package."""
    port = AutodetectHelper.which("port")
    try:
      if port is not None:
        return [s.strip() for s in
                subprocess.check_output([port, "-q", "contents", package],
                                        stderr=FNULL).splitlines()
                                        if s]
    except subprocess.CalledProcessError:
      pass

  @staticmethod
  def pc_read(filename):
    """Read a pkg-config file."""
    if not os.path.exists(filename):
      return None
    regex = re.compile("^([a-zA-Z._-]*)\s*([=:])\s*(.*)$")
    result = {"variables": {}}
    f = open(filename, "r")
    for line in f:
      line = line.strip()
      if line and not line.startswith("#"):
        match = regex.match(line)
        if match:
          if match.group(2) == ":":
            result[match.group(1)] = match.group(3)
          else:
            result["variables"][match.group(1)] = match.group(3)
    f.close()
    return result

  @staticmethod
  def sub_variables(value, variables):
    """Variables substitution on one value"""
    regex = re.compile("\$\{([a-zA-Z._-]*)\}")
    match = regex.search(value)
    while match:
      var = match.group(1)
      val = ""
      if var in variables:
        val = variables[var]
      value = re.sub("\$\{%s\}" % var, val, value) 
      match = regex.search(value)
    return value

  @staticmethod
  def __pc_variables(variables):
    """Performs variables substitution on the variables list."""
    regex = re.compile("\$\{([^\}]*)\}")
    for key, value in variables.iteritems():
      variables[key] = AutodetectHelper.sub_variables(value, variables)
    return variables

  @staticmethod
  def __pc_extract_flag(astr, variables, include=None, excludes=None):
    """Extract the list of flags."""
    if include:
      return [
        AutodetectHelper.sub_variables(i[len(include):], variables)
        for i in astr.split() if i.startswith(include)
        ]
    else:
      f = lambda i: reduce(lambda x, v: x and not i.startswith(v), excludes,
                           True)
      return [
        AutodetectHelper.sub_variables(i, variables)
        for i in astr.split() if f(i)
        ]

  @staticmethod
  def read_pc_as_pkg_config(filename):
    """Read a pkg-config file and return the same result as with pkg_config."""
    f = AutodetectHelper.pc_read(filename)
    if not f:
      return None
    result = {"variables": AutodetectHelper.__pc_variables(f["variables"])}
    result["library_dirs"] = AutodetectHelper.__pc_extract_flag(
      f["Libs"], result["variables"], "-L")
    result["libraries"] = AutodetectHelper.__pc_extract_flag(
      f["Libs"], result["variables"], "-l")
    result["ldflags"] = AutodetectHelper.__pc_extract_flag(
      f["Libs"], result["variables"], excludes=["-l", "-L"])
    result["include_dirs"] = AutodetectHelper.__pc_extract_flag(
      f["Cflags"], result["variables"], "-I")
    result["cflags"] = AutodetectHelper.__pc_extract_flag(
      f["Cflags"], result["variables"], excludes=["-I"])
    return result

  @staticmethod
  def find_library(name):
    """Search for a library on the system.

    It is a wrapper around the other helper method to have a unified interface.
    See AutodetectHelper.pkg_config for the format of the output.
    """
    # Use pkg-config first
    result = AutodetectHelper.pkg_config(name)
    if result:
      return result
    # Fallback to brew
    brew_prefix = AutodetectHelper.brew_prefix(name)
    if brew_prefix:
      # pc files are in ${brew_prefix}/lib/pkgconfig/${name}.pc
      result = AutodetectHelper.read_pc_as_pkg_config(
        "%s/lib/pkgconfig/%s.pc" % (brew_prefix, name))
      if result is None:
        # Fallback, returns default values.
        return {
          "variables": {
            "prefix": brew_prefix,
            "exec_prefix": brew_prefix,
            "libdir": "%s/lib" % brew_prefix,
            "includedir": "%s/include" % brew_prefix,
          }
        }
      else:
        return result
    # Fallback to port
    port_files = AutodetectHelper.port_content(name)
    if port_files:
      pc_files = filter(port_files, lambda f: f.endswith(".pc"))
      result = None
      if len(pc_files) > 0:
        result = AutodetectHelper.read_pc_as_pkg_config(pc_files[0])
      if result is None:
        # Fallback, returns default values.
        return {
          "variables": {
            "content": port_files,
            "prefix": "/opt/local",
            "exec_prefix": "/opt/local",
            "libdir": "/opt/local/lib",
            "includedir": "/opt/local/include",
          }
        }
      else:
        result["variables"]["content"] = port_files
        return result
    # Not found
    return None
