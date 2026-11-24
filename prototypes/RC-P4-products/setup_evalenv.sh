#!/bin/bash
# Records how ETH3D's multi-view-evaluation tool was built on the DGX (aarch64), user-level only.
# Three upstream files needed edits for a current toolchain (patched in the clone, not committed):
#   -msse2 -msse3 -std=c++11 compiler flags (x86-only, and C++11 conflicts with PCL 1.15): removed
#   cmake_minimum_required 2.8 -> 3.5 (CMake 4 refuses < 3.5)
#   Boost COMPONENTS: system removed (Boost 1.90 has no compiled system library)
#   CMAKE_MODULE_PATH line removed (the repo's FindEigen3.cmake rejects Eigen 5.0)
set -e
R=$HOME/.cache/recce; E=$R/evalenv
export MAMBA_ROOT_PREFIX=$R/mamba
~/.local/bin/micromamba create -y -p "$E" -c conda-forge pcl libboost-devel eigen p7zip cmake make
git clone https://github.com/ETH3D/multi-view-evaluation.git "$R/mve-src"
cd "$R/mve-src"   # built at 0daa4f4de036d47d37a6ba054c51fd66642ef896
sed -i 's/-O2 -msse2 -msse3 -std=c++11/-O2/; s/cmake_minimum_required(VERSION 2.8)/cmake_minimum_required(VERSION 3.5)/; s/COMPONENTS filesystem system REQUIRED/COMPONENTS filesystem REQUIRED/; /CMAKE_MODULE_PATH/d' CMakeLists.txt
mkdir -p build && cd build
PATH=$E/bin:$PATH cmake .. -DCMAKE_PREFIX_PATH="$E" -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXE_LINKER_FLAGS="-Wl,-rpath,$E/lib"
PATH=$E/bin:$PATH make -j4
./ETH3DMultiViewEvaluation --help | head -3
