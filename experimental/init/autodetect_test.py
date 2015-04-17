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
"""Tests for the autodetect module"""

import os
import shutil
import stat
import tempfile
import unittest

import experimental.init.autodetect as autodetect

helper = autodetect.AutodetectHelper()

# The content of pkg_config file
pc_file = """
prefix=/usr/local
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: libarchive
Cflags: -I${includedir}
Libs: -L${libdir} -larchive
Libs.private: -lexpat -llzma -lbz2 -lz 
"""

# A emulation of pkg_config that only serves the info of the file above
pkg_config = """#!/bin/bash

if [ "$#" != 2 ]; then
  exit 1
fi

if [ "$2" != "libarchive" ]; then
  exit 1
fi

case "$1" in
  --exists|--atleast-version|--max-version)
    ;;
  --libs-only-other|--cflags-only-other)
    ;;
  --libs-only-L)
    echo "-L/usr/local/lib"
    ;;
  --libs-only-l)
    echo "-larchive"
    ;;
  --cflags-only-I)
    echo "-I/usr/local/include"
    ;;
  --print-variables)
    echo prefix
    echo exec_prefix
    echo libdir
    echo includedir
    ;;
  --variable=prefix|--variable=exec_prefix)
    echo /usr/local
    ;;
  --variable=libdir)
    echo /usr/local/lib
    ;;
  --variable=includedir)
    echo /usr/local/include
    ;;
  *)
    exit 1
    ;;
esac
"""

# The expected output corresponding to the above fixture
pc_result = {
    "variables": {
        "prefix": "/usr/local",
        "exec_prefix": "/usr/local",
        "libdir": "/usr/local/lib",
        "includedir": "/usr/local/include"
    },
    "library_dirs": ["/usr/local/lib"],
    "libraries": ["archive"],
    "ldflags": [],
    "include_dirs": ["/usr/local/include"],
    "cflags": []
    }

class AutodetectHelperTestCase(unittest.TestCase):

  def fixture(self, binaries={"bin":""}, non_binaries={"txt":""}):
    self.temp = tempfile.mkdtemp()
    if "PATH" in os.environ:
      self.backup_path = os.environ["PATH"]
    os.environ["PATH"] = self.temp
    for key, value in binaries.iteritems():
      path = os.path.join(self.temp, key)
      f = open(path, "w")
      f.write(value)
      f.close()
      os.chmod(path, 0755)
    
    for key, value in non_binaries.iteritems():
      path = os.path.join(self.temp, key)
      f = open(path, "w")
      f.write(value)
      f.close()
      os.chmod(path, 0644)

  def setUp(self):
    self.maxDiff = None
    self.temp = None
    self.backup_path = None

  def tearDown(self):
    if self.temp:
      shutil.rmtree(self.temp)
      self.temp = None
    if self.backup_path:
      os.environ["PATH"] = self.backup_path
      self.backup_path = None

  def test_version_compare(self):
    self.assertEquals(helper.version_compare("1.7.0", "2"), -1)
    self.assertEquals(helper.version_compare("2.3.1", "2.1"), 1)
    self.assertEquals(helper.version_compare("1.2", "1.2"), 0)

  def test_which(self):
    self.fixture()
    self.assertEquals(helper.which("bin"), os.path.join(self.temp, "bin"))
    self.assertIsNone(helper.which("txt"))
    self.assertIsNone(helper.which("bin2"))
    path = os.path.join(self.temp, "toto") 
    os.mkdir(path)
    bin2_path = os.path.join(path, "bin2")
    f = open(bin2_path, "w")
    f.write("empty")
    f.close()
    os.chmod(bin2_path, 0755)
    self.assertIsNone(helper.which("bin2"))
    os.environ["PATH"] = "%s:%s" % (self.temp, path)
    self.assertEquals(helper.which("bin2"), bin2_path)

  def test_pkg_config(self):
    self.fixture(binaries={"pkg-config": pkg_config})
    self.assertIsNone(helper.pkg_config("toto"))
    self.assertEquals(helper.pkg_config("libarchive"), pc_result)

  def test_read_pc_as_pkg_config(self):
    self.fixture(non_binaries={"file.pc": pc_file})
    path = os.path.join(self.temp, "file.pc")

    variables =  {
      "prefix": "/usr/local",
      "exec_prefix": "${prefix}",
      "libdir": "${exec_prefix}/lib",
      "includedir": "${prefix}/include",
      }
    self.assertEquals(helper.pc_read(path), {
      "Name": "libarchive",
      "Cflags": "-I${includedir}",
      "Libs": "-L${libdir} -larchive",
      "Libs.private": "-lexpat -llzma -lbz2 -lz",
      "variables": variables
      })
    self.assertEquals(helper.sub_variables("${exec_prefix}/lib", variables),
                      "/usr/local/lib")
    self.assertEquals(helper.read_pc_as_pkg_config(path), pc_result)

    
if __name__ == '__main__':
    unittest.main()
