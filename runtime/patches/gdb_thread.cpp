#ifdef GDB_STUB
#include <SDL.h>

void *createThread_gdb(void (*thread_function)(void *data), void *thread_data) {
    return SDL_CreateThread(reinterpret_cast<int (*)(void *)>(thread_function), "gdb-stub", thread_data);
}

void joinThread_gdb(void *thread_handle) {
    int ignored = 0;
    SDL_WaitThread(static_cast<SDL_Thread *>(thread_handle), &ignored);
}
#endif
