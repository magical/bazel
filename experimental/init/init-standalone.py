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
"""bazel-init prototype for standalone run (outside of bazel)."""

import atexit
import imp
import os
import pickle
import shutil
import subprocess
import sys
import tempfile

# Local imports
import autodetect
import buildgen
import packgen

#
# Entry point
#

def bazel_info(info_key):
  return subprocess.check_output(["bazel", "info", info_key]).strip()

def usage(progname):
  sys.exit(("Usage: %s module1...moduleN") % progname)


def configure(helper, modules):
  result = []
  for module in modules:
    print("  %s..." % module.package())
    result.append(module.autodetect({}, helper))
  return result


def generate(modules, configs, install_dir, output):
  for i in range(0, len(modules)):
    package = modules[i].package()
    print("  %s..." % package)
    package_helper = packgen.PackageGenerationHelper(install_dir, output, package)
    build_helper = buildgen.BuildGeneratorHelper(package)
    modules[i].generate(configs[i], build_helper)
    build_helper.generate(package_helper)
    package_helper.close()


def main(argv):
  if len(argv) < 2:
    usage(argv[0])

  # Touch the workspace file
  if not os.path.exists("WORKSPACE"):
    with open("WORKSPACE", "a"):
      pass

  # Get info from bazel
  install_base = bazel_info("install_base")
  output_base = bazel_info("output_base")
  output_dir = os.path.join(output_base, "package_path")
  embed_dir = os.path.join(install_base, "_embedded_binaries")

  # Load all modules
  temp_directory = tempfile.mkdtemp()
  atexit.register(lambda: shutil.rmtree(temp_directory))

  modules = []
  for i in range(1, len(argv)):
    new_module = os.path.join(temp_directory, "package_builder%d" % i)
    shutil.copy(argv[i], new_module)
    modules.append(imp.load_source("package_builder%d" % i, new_module))

  # Configure and generate
  output = packgen.WorkspaceOutputGenerator(output_dir)
  print("CONFIGURE")
  configs = configure(autodetect.AutodetectHelper(), modules)
  print("GENERATE")
  generate(modules, configs, embed_dir, output)
  print("SUCCESS")
  print("Please set in your ~/.bazelrc:")
  print("  startup --package_path=%%workspace%%:%s" % output_dir)


try:
  main(sys.argv)
except autodetect.AutodetectFailure as e:
  exit("\033[1m\033[91mERROR:\033[0m Auto-detection - " + e.value)
except packgen.PackageGenerationFailure as e:
  exit("\033[1m\033[91mERROR:\033[0m Generation - " + e.value)
