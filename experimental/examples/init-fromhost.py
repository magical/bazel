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
# Experiment on generating a fromhost package from bazel
#
"""bazel-init prototype for fromhost."""

import os
import platform
import re
import subprocess

def package():
  return "fromhost"

def autodetect(variables, helper):
  """Do pkg-config detection of libarchive."""
  result = helper.find_library("libarchive")
  if result is None:
    helper.fail("Unable to find libarchive")
  return result

def generate(variables, helper):
  """Generate the fromhost package."""
  helper.scratch_file("empty.c")
  helper.rule("cc_library",
              name = "libarchive",
              srcs = ["empty.c"],
              copts = variables["cflags"],
              includes = variables["include_dirs"],
              linkopts = variables["ldflags"] + [
                ("-L%s" % d) for d in variables["library_dirs"]
                ] + [
                  ("-l%s" % l) for l in variables["libraries"]
                ]
  )
