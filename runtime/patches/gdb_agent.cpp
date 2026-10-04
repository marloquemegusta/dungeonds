#ifdef GDB_STUB
#include "../../driver.h"
#include "../../armcpu.h"
#include "../../gdbstub.h"
#include "../../MMU.h"
#include "../../NDSSystem.h"
#include "../../SPU.h"
#include "interface.h"

class AgentDebugDriver final : public BaseDriver {
public:
    gdbstub_handle_t stubs[2] = {};
    void EMU_DebugIdleEnter() override { SPU_Pause(1); }
    void EMU_DebugIdleUpdate() override { gdbstub_wait(stubs, -1L); }
    void EMU_DebugIdleWakeUp() override { SPU_Pause(0); }
};

static AgentDebugDriver *agent_driver = nullptr;
static BaseDriver *previous_driver = nullptr;

extern "C" EXPORTED void desmume_gdb_stop();

extern "C" EXPORTED int desmume_gdb_start(unsigned short arm9_port, unsigned short arm7_port) {
    if (agent_driver != nullptr || (arm9_port == 0 && arm7_port == 0)) return 0;
    gdbstub_mutex_init();
    agent_driver = new AgentDebugDriver();
    previous_driver = driver;
    driver = agent_driver;
    if (arm9_port != 0) {
        agent_driver->stubs[0] = createStub_gdb(arm9_port, &NDS_ARM9, &arm9_direct_memory_iface);
    }
    if (arm7_port != 0) {
        agent_driver->stubs[1] = createStub_gdb(arm7_port, &NDS_ARM7, &arm7_base_memory_iface);
    }
    if ((arm9_port != 0 && agent_driver->stubs[0] == nullptr) ||
        (arm7_port != 0 && agent_driver->stubs[1] == nullptr)) {
        desmume_gdb_stop();
        return 0;
    }
    for (auto stub : agent_driver->stubs) {
        if (stub != nullptr) {
            activateStub_gdb(stub);
            gdbstub_wait_set_enabled(stub, 1);
        }
    }
    if (CommonSettings.use_jit) {
        arm_jit_sync();
        arm_jit_reset(CommonSettings.use_jit = 0);
    }
    return 1;
}

extern "C" EXPORTED void desmume_gdb_stop() {
    if (agent_driver == nullptr) return;
    for (auto &stub : agent_driver->stubs) {
        if (stub != nullptr) {
            destroyStub_gdb(stub);
            stub = nullptr;
        }
    }
    driver = previous_driver;
    previous_driver = nullptr;
    delete agent_driver;
    agent_driver = nullptr;
    gdbstub_mutex_destroy();
}
#else
extern "C" int desmume_gdb_start(unsigned short, unsigned short) { return 0; }
extern "C" void desmume_gdb_stop() {}
#endif
