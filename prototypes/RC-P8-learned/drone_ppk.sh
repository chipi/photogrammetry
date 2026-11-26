#!/usr/bin/env bash
# PPK of the drone's raw GNSS log against the EuroSDR local base station (RINEX 2.11, ETRS89
# precise coordinates in the header). RTKLIB (GPL) runs from Debian's package in a throwaway
# container, so nothing is installed on the host and the GPL tool stays outside our code.
#
#     drone_ppk.sh FLIGHT_DIR BASE_RINEX_GZ OUT_DIR "YYYY/MM/DD HH:MM:SS"
#
# The time is the flight's approximate UTC start; RTCM 3 carries no week number without it.
#
# Writes OUT_DIR/ppk.pos (fixed and float epochs, llh, ellipsoidal heights, GPS time of week).
set -euo pipefail
flight=$1 base=$2 out=$3 start=$4
mkdir -p "$out"
cp "$flight"/*_PPKRAW.bin "$out/rover.bin"
zcat "$base" > "$out/base.obs"
cat > "$out/ppk.conf" <<'EOF'
pos1-posmode       =kinematic
pos1-frequency     =l1+l2
pos1-soltype       =combined
pos1-elmask        =15
pos1-navsys        =5
pos2-armode        =fix-and-hold
pos2-gloarmode     =off
out-solformat      =llh
out-height         =ellipsoidal
out-timesys        =gpst
out-timeform       =tow
ant2-postype       =rinexhead
EOF
docker run --rm -v "$out":/w -w /w debian:trixie bash -c '
  apt-get -qq update >/dev/null && apt-get -qq install -y rtklib >/dev/null 2>&1
  convbin -r rtcm3 -tr "'"$start"'" -v 3.04 -o rover.obs -n rover.nav rover.bin >/dev/null 2>&1
  rnx2rtkp -k ppk.conf -o ppk.pos rover.obs base.obs rover.nav >/dev/null 2>&1
  chown -R '"$(id -u):$(id -g)"' /w'
grep -v '^%' "$out/ppk.pos" | awk '{q[$6]++} END {for (k in q) printf "Q=%s epochs %d\n", k, q[k]}'
