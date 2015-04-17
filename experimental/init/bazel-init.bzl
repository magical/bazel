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

BAZEL_INIT = "//experimental/init:bazel-init"

# Trick but we actually want it to point to the embedded folder
EMBEDDED_DIR="$${PWD}/tools/jdk"

def package_conf(name, src, visibility=None):
    native.genrule(
        name = "bazel-init-%s-configure" % name,
        srcs = [src],
        tools = [BAZEL_INIT],
        visibility = ["//visibility:private"],
        outs = ["bazel-init-%s.conf" % name],
        # We add the PATH and HOMR, really we should integrate that more nicely
        cmd = "HOME=/tmp PATH=/usr/bin:/usr/local/bin:/bin" +
              (" $(location %s) configure $< $@" % BAZEL_INIT)
    )
    native.genrule(
        name = name,
        srcs = [src, ":bazel-init-%s-configure" % name],
        tools = [BAZEL_INIT],
        outs = ["%s.zip" % name],
        visibility = visibility,
        cmd = ("$(location %s) generate $(location %s)" +
               " $@ $(location :bazel-init-%s-configure) %s") % (
            BAZEL_INIT,
            src,
            name,
            EMBEDDED_DIR
            )
    )

def bazel_configure(name, deps):
    native.genrule(
        name = name,
        srcs = deps,
        tools = [BAZEL_INIT],
        outs = [name + ".zip"],
        cmd = "$(location %s) merge $@ $(SRCS)" % BAZEL_INIT
    )

