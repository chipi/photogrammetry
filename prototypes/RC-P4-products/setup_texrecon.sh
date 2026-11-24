#!/bin/bash
# Records how MVS-Texturing (texrecon) was built on the DGX (aarch64), user-level, 2 build jobs.
# Edits needed for aarch64 (made in the clone only): -mfpmath=sse removed from CMakeLists.txt, and
# -msse2 -msse3 -msse4 -mpopcnt removed from elibs/mve/Makefile.inc (all x86-only).
# The configure step downloads, at pinned or default revisions: mapmap_cpu fa526e0, rayint (branch
# cuda), Eigen 3.3.2 (MPL2), nmoehrle/mve 91c0f3f. First build attempt ran make once to fetch them.
set -e
R=$HOME/.cache/recce; E=$R/texenv
export MAMBA_ROOT_PREFIX=$R/mamba
~/.local/bin/micromamba create -y -p "$E" -c conda-forge libpng libjpeg-turbo libtiff tbb-devel cmake make git
git clone https://github.com/nmoehrle/mvs-texturing.git "$R/texrecon-src"   # f3374298ac959cb5afe47a14e4d35d2ac7fbdbb1
cd "$R/texrecon-src"
sed -i 's/ -mfpmath=sse//' CMakeLists.txt
mkdir -p build && cd build
export PATH=$E/bin:$PATH CPPFLAGS=-I$E/include LDFLAGS="-L$E/lib -Wl,-rpath,$E/lib"
cmake .. -DCMAKE_PREFIX_PATH="$E" -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_EXE_LINKER_FLAGS="-Wl,-rpath,$E/lib"
make -j2 || true   # fails once in ext_mve on the x86 flags, after the sources are downloaded
sed -i -E 's/ -msse[0-9]*//g; s/ -mpopcnt//g' ../elibs/mve/Makefile.inc
make -j2
