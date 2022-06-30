
cmake_minimum_required(VERSION 2.8)

include(RezBuild)

file(GLOB_RECURSE py_files "src/wolfkrow/*.py")

rez_install_python(
    python
    RELATIVE src
    FILES ${py_files}
    DESTINATION python
)

rez_install_dirs(
    src/wolfkrow
    DESTINATION python
)

file(GLOB bin_files "src/bin/*")
rez_install_files(
    ${bin_files}
    RELATIVE src
    DESTINATION .
)
