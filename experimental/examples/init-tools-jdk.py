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
# Experiment on generating a tools/jdk package from bazel
#
"""bazel-init prototype for tools/jdk."""

import os
import platform
import re
import subprocess

def package():
  return "tools/jdk"

JDK_REQUIRED_VERSION = "1.8"

BOOTCLASS_JARS = [
    "rt.jar",
    "resources.jar",
    "jsse.jar",
    "jce.jar",
    "charsets.jar",
    ]


def test_java_home(helper, java_home, min_java_version):
  """Test if the provided java home contains a JDK with the correct version.

  Args:
    helper: the auto-detection helper
    java_home: the supposed path to the JDK
    min_java_version: the minimum required Java version

  Returns:
    True if java_home is a path to an existing JDK whose version is at
    least min_java_version.
  """
  try:
    path = os.path.join(java_home, "bin", "javac")
    if not os.path.exists(path):
      return False
    output = subprocess.check_output([path, "-version"],
                                     stderr=subprocess.STDOUT)
    match = re.search("javac ([0-9\\.]*)", output)
    if match is None:
      return False
    version = match.group(1)
    return helper.version_compare(version, min_java_version) >= 0
  except subprocess.CalledProcessError:
    return False

def find_jdk(helper, min_java_version):
  """Find a JDK installation on the system.

  Args:
    helper: the auto-detection helper
    min_java_version: the minimum java version required.

  Returns:
    A string giving the path to the install JDK or fails if none was found.
  """
  if platform.system() == "Darwin":
    # Under darwin try /usr/libexec/java_home
    try:
      java_home = subprocess.check_output([
          "/usr/libexec/java_home",
          "-v",
          min_java_version + "+"
          ]).strip()
      if test_java_home(helper, java_home, min_java_version):
        return java_home
    except subprocess.CalledProcessError:
      # Ignore, we just go to default unix usage
      pass

  if "JAVA_HOME" in os.environ:
    if test_java_home(helper, os.environ["JAVA_HOME"], min_java_version):
      return os.environ["JAVA_HOME"]

  java_path = helper.which("java")
  if java_path is not None:
    java_home = os.path.dirname(os.path.dirname(os.path.realpath(java_path)))
    if test_java_home(helper, java_home, min_java_version):
      return java_home

  helper.fail("Cannot find JDK version at least " + min_java_version)

def autodetect(variables, helper):
  """Do autodetection of JDK stuff."""
  if "jdk" in variables and test_java_home(helper, variables["jdk"],
                                           JDK_REQUIRED_VERSION):
    jdk = variables["jdk"]
  else:
    jdk = find_jdk(helper, JDK_REQUIRED_VERSION)

  jni_md_header = os.path.join("include", platform.system().lower(), "jni_md.h")

  return {"jdk": jdk, "jni_md_header": jni_md_header}

def generate(variables, helper):
  """Generate the tools/jdk package."""
  jdk_helper = helper.new_repository("new_local_repository",
                                     name="jdk",
                                     path=variables["jdk"])

  jni_header = jdk_helper.rule("filegroup",
                               name="jni_header",
                               srcs=["include/jni.h"])
  jni_md_header = jdk_helper.rule("filegroup",
                                  name="jni_md_header",
                                  srcs=[variables["jni_md_header"]])
  java = jdk_helper.rule("filegroup", name="java", srcs=["bin/java"])
  bootclasspath = jdk_helper.rule("filegroup",
                                  name="bootclasspath",
                                  srcs=[
                                      "jre/lib/%s" % jar
                                      for jar in BOOTCLASS_JARS
                                      ])
  langtools = jdk_helper.rule("filegroup",
                              name="langtools",
                              srcs=["lib/tools.jar"])
  jdk_default = jdk_helper.rule("filegroup",
                                name="jdk-default",
                                srcs=helper.glob(["bin/*"]))

  helper.rule("filegroup", name="jni_header", srcs=[jni_header])
  helper.rule("filegroup", name="jni_md_header", srcs=[jni_md_header])
  helper.rule("filegroup", name="java", srcs=[java])
  helper.rule("filegroup", name="langtools", srcs=[langtools])
  helper.rule("filegroup", name="bootclasspath", srcs=[bootclasspath])
  helper.rule("java_import", name="langtools-neverlink",
              jars=[langtools], neverlink=1)

  # This one is just needed because how filegroup redirection works
  jdk_null = helper.rule("filegroup", name="jdk-null")
  helper.rule("filegroup", name="jdk", srcs=[jdk_null, jdk_default])
  helper.rule("java_toolchain",
              name="toolchain",
              encoding="UTF-8",
              source_version="8",
              target_version="8")
  helper.exports_embedded("JavaBuilder_deploy.jar")
  helper.exports_embedded("SingleJar_deploy.jar")
  helper.exports_embedded("ijar")
