package(default_visibility = ["//visibility:public"])
load("/experimental/init/bazel-init", "package_conf", "bazel_configure")

package_conf(
    name = "jdk",
    src = "init-tools-jdk.py",
)

package_conf(
    name = "fromhost",
    src = "init-fromhost.py",
)

bazel_configure(
    name = "config",
    deps = [
        ":jdk",
        ":fromhost"
    ]
)
