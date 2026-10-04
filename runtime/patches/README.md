# DeSmuME Headless Agent Patch & Build Instructions

This directory contains the patches and source files needed to build `libdesmume.so` and `desmume-agent` with headless ABI and ARM9 GDB stub enabled.

- Base commit: `b3915949700be824253a35affa7f7b8248e84e46` (upstream DeSmuME Git).
- Patch: `desmume-agent.patch`
- New files: `gdb_agent.cpp` and `gdb_thread.cpp` (placed in `desmume/src/frontend/interface/`).

## Automated Setup
To avoid building manually, use `scripts/setup.ps1` which automatically fetches the precompiled runtime binary from GitHub Releases.
