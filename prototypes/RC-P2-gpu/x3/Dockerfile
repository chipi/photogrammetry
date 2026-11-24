# RC-P2 X3 half: COLMAP patch_match_stereo through HIP on gfx1151 (Strix Halo, Radeon 8060S).
# Build: bash build.sh        Run: bash run_dense.sh
FROM rocm/dev-ubuntu-24.04:7.2.4

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        git cmake ninja-build build-essential ccache ca-certificates \
        libboost-program-options-dev libboost-graph-dev libboost-system-dev \
        libeigen3-dev libopenimageio-dev openimageio-tools libmetis-dev \
        libgoogle-glog-dev libgtest-dev libgmock-dev libsqlite3-dev \
        libceres-dev libsuitesparse-dev libcurl4-openssl-dev libssl-dev \
        libopenblas-dev libgflags-dev libglew-dev \
        hiprand-dev rocrand-dev \
    && mkdir -p /usr/include/opencv4 \
    && rm -rf /var/lib/apt/lists/*

# Upstream main carries the HIP backend (PR #4635 / #4795); pinned for repeatability.
ARG COLMAP_REF=57ded392a59a31890e3cffc9ab4019f5bf268fd3
ARG JOBS=16
RUN git clone https://github.com/colmap/colmap.git /src/colmap \
    && git -C /src/colmap checkout ${COLMAP_REF}

ENV ROCM_PATH=/opt/rocm
RUN cmake -S /src/colmap -B /build -GNinja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCUDA_ENABLED=OFF -DHIP_ENABLED=ON \
        -DCMAKE_HIP_ARCHITECTURES=gfx1151 \
        -DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++ \
        -DGUI_ENABLED=OFF -DOPENGL_ENABLED=OFF -DONNX_ENABLED=OFF \
        -DCGAL_ENABLED=OFF -DTESTS_ENABLED=OFF -DCCACHE_ENABLED=OFF \
        -DCMAKE_INSTALL_PREFIX=/opt/colmap
RUN cmake --build /build -j${JOBS} && cmake --install /build
ENV PATH=/opt/colmap/bin:/opt/rocm/bin:${PATH}
