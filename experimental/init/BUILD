package(default_visibility = ["//visibility:public"])

py_binary(
    name = "bazel-init",
    srcs = ["bazel-init.py"],
    deps = [
        ":autodetect",
        ":buildgen",
        ":packgen",
    ],
)

py_library(
    name = "autodetect",
    srcs = ["autodetect.py"],
    visibility = ["//visibility:private"],
)

py_test(
    name = "autodetect_test",
    srcs = ["autodetect_test.py"],
    deps = [":autodetect"],
)

py_library(
    name = "buildgen",
    srcs = ["buildgen.py"],
    visibility = ["//visibility:private"],
)

py_library(
    name = "packgen",
    srcs = ["packgen.py"],
    visibility = ["//visibility:private"],
)
