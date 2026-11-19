BLOCKSDS ?= /opt/wonderful/thirdparty/blocksds/core
BLOCKSDSEXT ?= /opt/wonderful/thirdparty/blocksds/external
WONDERFUL_TOOLCHAIN ?= /opt/wonderful
NAME ?= game-blocksds
GAME_TITLE ?= DungeonDS
GAME_SUBTITLE ?= Necromancer Crypt
GAME_AUTHOR ?= Antigravity
GAME_ICON ?= icon.png
SOURCEDIRS := arm9/source
INCLUDEDIRS := arm9/include
AUDIODIRS := audio
NITROFSDIR := nitrofiles
BINDIRS ?=
LIBDIRS := $(BLOCKSDS)/libs/maxmod
LIBS := -lmm9 -lnds9
DEFINES ?= -DDS_DEBUG_TRACE -DDS_AUTOTEST
# build-project.ps1 passes the variant defines through CFLAGS, so look there too (otherwise every sandbox/stress variant got ENCOUNTERS_PROTO=1).
VARIANT_DEFINES := $(DEFINES) $(CFLAGS)
ifeq ($(findstring SANDBOX=1,$(VARIANT_DEFINES))$(findstring BESTIARY_START=1,$(VARIANT_DEFINES))$(findstring STRESS_TEST=1,$(VARIANT_DEFINES))$(findstring GODRAYS_PROTO=1,$(VARIANT_DEFINES))$(findstring ENCOUNTERS_PROTO=,$(VARIANT_DEFINES)),)
DEFINES += -DENCOUNTERS_PROTO=1
endif
include $(BLOCKSDS)/sys/default_makefiles/rom_arm9/Makefile
