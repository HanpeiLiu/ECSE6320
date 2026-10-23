#!/usr/bin/env python3
"""Rebuild the downloaded tool sources within this project, without sudo."""
from pathlib import Path
import os
import subprocess

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
BIN = ROOT / "bin"
LOGS = ROOT / "logs"
BIN.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)


def build(name, cwd, commands, extra_env=None):
    env = os.environ.copy()
    env.update(extra_env or {})
    logfile = LOGS / (name + "-rebuild.log")
    print("Building", name, flush=True)
    with logfile.open("w") as log:
        for command in commands:
            log.write(repr(command) + "\n")
            log.flush()
            subprocess.run(command, cwd=cwd, env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True)


build("fio", SRC / "fio-3.43", [
    ["./configure", "--prefix=../.."], ["make", "-j4"],
])
build("smartmontools", SRC / "smartmontools-7.5", [
    ["./configure", "--prefix=" + str(ROOT), "--without-initscriptdir",
     "--without-update-smart-drivedb"],
    ["make", "-j4", "smartctl"],
])
build("lmbench", SRC / "lmbench" / "src", [[
    "../scripts/build", "../bin/macos-arm64/lat_mem_rd",
    "../bin/macos-arm64/bw_mem", "../bin/macos-arm64/tlb",
    "../bin/macos-arm64/par_mem",
]], {
    "CC": "clang", "CFLAGS": "-O2 -include rpc/rpc.h -include rpc/pmap_clnt.h",
    "OS": "macos-arm64", "MAKE": "make",
})
build("stream", SRC / "stream", [[
    "clang", "-O3", "-mcpu=native", "-DSTREAM_ARRAY_SIZE=10000000",
    "-DNTIMES=10", "stream.c", "-o", str(BIN / "stream"),
]])

links = {"fio": "../src/fio-3.43/fio",
         "smartctl": "../src/smartmontools-7.5/smartctl"}
for name in ["lat_mem_rd", "bw_mem", "tlb", "par_mem"]:
    links[name] = "../src/lmbench/bin/macos-arm64/" + name
for name, target in links.items():
    path = BIN / name
    if path.is_symlink():
        if os.readlink(path) != target:
            raise RuntimeError("Unexpected existing symlink: " + str(path))
    elif path.exists():
        raise RuntimeError("Refusing to overwrite: " + str(path))
    else:
        path.symlink_to(target)
print("Tools ready in", BIN)
