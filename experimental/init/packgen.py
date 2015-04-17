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
# Experiment on generating a tools package from bazel.
#
"""bazel-init prototype tooling for package generation."""

import os
import shutil
import stat
import zipfile

def merge_package(output_file, packages):
  """Merge various package into one workspace."""
  output = zipfile.ZipFile(output_file, "w")
  workspace = ""
  for package in packages:
    zf = zipfile.ZipFile(package, "r")
    for info in zf.infolist():
      f = zf.open(info.filename)
      if info.filename == "WORKSPACE":
        workspace = "%s%s\n" % (workspace, f.read())
      else:
        output.writestr(info, f.read())
      f.close()
  info = zipfile.ZipInfo("WORKSPACE", (1980, 0, 0, 0, 0, 0))
  info.external_attr = 0444 << 16L
  output.writestr(info, workspace)
  output.close()


class PackageGenerationFailure(Exception):
  """Exception to be thrown on failure in package generation."""

  def __init__(self, value):
    Exception.__init__(self)
    self.value = value

  def __str__(self):
    return repr(self.value)

class ZipOutputGenerator(object):
  """Generate a Zip File with the workspace structure."""
  
  def __init__(self, output):
    self.zipfile = zipfile.ZipFile(output, "w")

  def scratch_file(self, path, content):
    info = zipfile.ZipInfo(path, (1980, 0, 0, 0, 0, 0))
    info.external_attr = 0444 << 16L  # Read-only files
    self.zipfile.writestr(info, content)

  def copy(self, path, origfile):
    info = zipfile.ZipInfo(path, (1980, 0, 0, 0, 0, 0))
    if not os.path.exists(origfile):
      raise PackageGenerationFailure("No such tool: " + origfile)
    # We don't use #write because we want to strip out timestamp
    if 0 != (stat.S_IXUSR & os.stat(origfile)[stat.ST_MODE]):
      info.external_attr = 0555 << 16L  # Read-only executable
    else:
      info.external_attr = 0444 << 16L  # Read-only
    f = open(origfile, "r")
    self.zipfile.writestr(info, f.read())
    f.close()

  def append(self, path, content):
    self.scratch_file(path, content)

  def close(self):
    self.zipfile.close()


class WorkspaceOutputGenerator(object):
  """Generate a workspace."""

  def __init__(self, output):
    self.folder = output
    if not os.path.exists(self.folder):
      os.makedirs(self.folder, 0700)

  @staticmethod
  def __mkdirs(p):
    p = os.path.dirname(p)
    if not os.path.exists(p):
      os.makedirs(p, 0700)

  def scratch_file(self, path, content):
    p = os.path.join(self.folder, path)
    WorkspaceOutputGenerator.__mkdirs(p)
    f = open(p, "w")
    f.write(content)
    f.close()
    os.chmod(p, 0600)

  def copy(self, path, origfile):
    p = os.path.join(self.folder, path)
    WorkspaceOutputGenerator.__mkdirs(p)
    shutil.copyfile(origfile, p)
    if 0 != (stat.S_IXUSR & os.stat(origfile)[stat.ST_MODE]):
      os.chmod(p, 0700)
    else:
      os.chmod(p, 0600)

  def append(self, path, content):
    p = os.path.join(self.folder, path)
    if os.path.exists(p):
      f = open(p, "a")
      f.write("\n")
      f.write(content)
      f.close()
    else:
      self.scratch_file(path, content)

  def close(self):
    pass


class PackageGenerationHelper(object):
  """A helper to generate the output."""

  def __init__(self, install_path, output, package):
    self.package = package
    self.install_path = install_path
    self.output = output

  def scratch_file(self, name, content):
    self.output.scratch_file(self.package + os.path.sep + name, content)

  def build_file(self, content):
    self.scratch_file("BUILD", content)

  def workspace_part(self, content):
    self.output.append("WORKSPACE", content)

  def copy_from_embedded(self, name):
    self.output.copy(self.package + os.path.sep + name,
                     self.install_path + os.path.sep + name)

  def close(self):
    self.output.close()


class ZipPackageGenerationHelper(PackageGenerationHelper):
  """A helper to generate the output in a ZIP file."""

  def __init__(self, install_path, output, package):
    PackageGenerationHelper.__init__(self, install_path,
                                     ZipOutputGenerator(output), package)


class WorkspacePackageGenerationHelper(PackageGenerationHelper):
  """A helper to generate the output in a folder."""

  def __init__(self, install_path, output, package):
    PackageGenerationHelper.__init__(self, install_path,
                                     WorkspaceOutputGenerator(output), package)


