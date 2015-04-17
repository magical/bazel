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
"""bazel-init prototype."""

import atexit
import imp
import os
import pickle
import shutil
import sys
import tempfile

# Local imports
import experimental.init.autodetect as autodetect
import experimental.init.buildgen as buildgen
import experimental.init.packgen as packgen

#
# Entry point
#


def usage(progname):
  sys.exit(("Usage: %s (merge output_file file1...fileN"
            "|configure module output_file [input_file]"
            "|generate module output_file input_file install_base)") % progname)


def main(argv):
  if len(argv) < 2 or argv[1] not in ["configure", "generate", "merge"]:
    usage(argv[0])

  command = argv[1]
  if command == "merge":
    # Special casing the merge
    output_file = argv[2]
    packgen.merge_package(output_file, argv[3:])
    return

  module = argv[2]
  output_file = argv[3]
  
  variables = {}
  if len(argv) > 4:
    fi = open(argv[4], "rb")
    variables = pickle.load(fi)
    fi.close()

  temp_directory = tempfile.mkdtemp()
  atexit.register(lambda: shutil.rmtree(temp_directory))

  new_module = os.path.join(temp_directory, "package_builder")
  shutil.copy(module, new_module)
  package_builder = imp.load_source("package_builder", new_module)

  if command == "generate":
    if len(argv) != 6:
      usage(argv[0])
    package = package_builder.package()
    package_helper = packgen.ZipPackageGenerationHelper(argv[5], output_file, package)
    build_helper = buildgen.BuildGeneratorHelper(package)
    package_builder.generate(variables, build_helper)
    build_helper.generate(package_helper)
    package_helper.close()
  else:  # configure
    helper = autodetect.AutodetectHelper()
    variables = package_builder.autodetect(variables, helper)
    fi = open(output_file, "wb")
    pickle.dump(variables, fi)
    fi.close()

try:
  main(sys.argv)
except autodetect.AutodetectFailure as e:
  exit("\033[1m\033[91mERROR:\033[0m Auto-detection - " + e.value)
except packgen.PackageGenerationFailure as e:
  exit("\033[1m\033[91mERROR:\033[0m Generation - " + e.value)
