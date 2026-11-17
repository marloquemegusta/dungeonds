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
ifeq ($(findstring SANDBOX=1,$(DEFINES))$(findstring BESTIARY_START=1,$(DEFINES))$(findstring STRESS_TEST=1,$(DEFINES))$(findstring GODRAYS_PROTO=1,$(DEFINES))$(findstring ENCOUNTERS_PROTO=,$(DEFINES)),)
DEFINES += -DENCOUNTERS_PROTO=1
endif
include $(BLOCKSDS)/sys/default_makefiles/rom_arm9/Makefile
