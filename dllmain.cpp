#include "pch.h"
#include "LicenseNotice.h"
#include "mod_loader.h"
#include "detours.h"
#include <windows.h>
#include <thread>
#include <cstdio>
#include <cstring>
#include <psapi.h>
#include <atomic>
#include <share.h>
#include <cstdarg>

char g_gameDir[MAX_PATH] = {};
FILE* gLogFile = nullptr;

void InitLogFile() {
    gLogFile = _fsopen("console.log", "w", _SH_DENYNO);
    if (gLogFile) {
        fprintf(gLogFile, "---- Log Started ----\n");
        fflush(gLogFile);
    }
}

void Log(const char* fmt, ...) {
    char buf[2048];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    buf[sizeof(buf) - 1] = '\0';
    va_end(args);

    printf("%s\n", buf);
    if (gLogFile) {
        fprintf(gLogFile, "%s\n", buf);
        fflush(gLogFile);
    }
}

bool FileExistsOnDisk(const char* path) {
    DWORD attr = GetFileAttributesA(path);
    return (attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY));
}

uintptr_t FindPattern(uintptr_t base, DWORD size, const char* pattern, const char* mask) {
    const size_t patternLength = strlen(mask);
    if (!patternLength || size < patternLength) return 0;
    for (size_t i = 0; i <= size - patternLength; ++i) {
        bool found = true;
        for (size_t j = 0; j < patternLength; ++j) {
            if (mask[j] != '?' && pattern[j] != *(char*)(base + i + j)) {
                found = false;
                break;
            }
        }
        if (found) return base + i;
    }
    return 0;
}

// g_gameDir is established once, with a trailing separator, before hooks are attached.
bool MakeResourcePath(const char* relative, char* output, size_t capacity) {
    const int length = snprintf(output, capacity, "%s%s", g_gameDir, relative);
    if (length < 0 || static_cast<size_t>(length) >= capacity) return false;
    for (char* p = output; *p; ++p) if (*p == '/') *p = '\\';
    return true;
}

typedef __int64(__fastcall* InitialFileCheck_t)(__int64 a1, const char* a2, unsigned int a3, unsigned int a4, unsigned __int16 a5);
typedef void(__fastcall* LocaleHandler_t)(__int64 mgr, char* dest, unsigned __int16* locale, char* src, int zero);

InitialFileCheck_t oInitialFileCheck = nullptr;
LocaleHandler_t oLocaleHandler = nullptr;
std::atomic<__int64> g_localeMgr{0};

__int64 __fastcall InitialFileCheck(__int64 a1, const char* a2, unsigned int a3, unsigned int a4, unsigned __int16 a5) {
    if (!a2) return oInitialFileCheck(a1, a2, a3, a4, a5);
    const size_t len = strlen(a2);
    if (len >= 4 && _stricmp(a2 + len - 4, ".pac") == 0)
        return oInitialFileCheck(a1, a2, a3, a4, a5);

    static thread_local char safeFullPath[MAX_PATH];
    // Game LocaleHandler writes a 0x200-byte path plus a DWORD length at +0x200.
    static thread_local char localizedPath[0x204];
    const char* finalPath = a2;
    const __int64 localeMgr = g_localeMgr.load(std::memory_order_relaxed);
    if (oLocaleHandler && localeMgr) {
        localizedPath[0] = '\0';
        oLocaleHandler(localeMgr, localizedPath, &a5, const_cast<char*>(a2), 0);
        if (localizedPath[0]) {
            char srcNorm[MAX_PATH];
            char destNorm[MAX_PATH];
            strncpy_s(srcNorm, sizeof(srcNorm), a2, _TRUNCATE);
            strncpy_s(destNorm, sizeof(destNorm), localizedPath, _TRUNCATE);
            for (char* p = srcNorm; *p; ++p) if (*p == '\\') *p = '/';
            for (char* p = destNorm; *p; ++p) if (*p == '\\') *p = '/';
            const char* slashSrc = strchr(srcNorm, '/');
            const char* slashDest = strchr(destNorm, '/');
            if (slashSrc && slashDest) {
                const size_t srcDirLen = static_cast<size_t>(slashSrc - srcNorm);
                const size_t destDirLen = static_cast<size_t>(slashDest - destNorm);
                if (destDirLen > srcDirLen && strncmp(destNorm, srcNorm, srcDirLen) == 0) {
                    char fullPath[MAX_PATH];
                    // Never probe a truncated absolute path. Retain the game's localized fallback.
                    if (MakeResourcePath(localizedPath, fullPath, sizeof(fullPath)) && FileExistsOnDisk(fullPath)) {
                        strcpy_s(safeFullPath, fullPath);
                        finalPath = safeFullPath;
                    } else {
                        finalPath = localizedPath;
                    }
                }
            }
        }
    }
    if (finalPath == a2) {
        char fullPath[MAX_PATH];
        if (MakeResourcePath(a2, fullPath, sizeof(fullPath)) && FileExistsOnDisk(fullPath)) {
            strcpy_s(safeFullPath, fullPath);
            finalPath = safeFullPath;
        }
    }
    return oInitialFileCheck(a1, finalPath, a3, a4, a5);
}

void __fastcall hkLocaleHandler(__int64 mgr, char* dest, unsigned __int16* locale, char* src, int zero) {
    g_localeMgr.store(mgr, std::memory_order_relaxed);
    oLocaleHandler(mgr, dest, locale, src, zero);
}

bool InitializeResources() {
    const DWORD pathLength = GetModuleFileNameA(nullptr, g_gameDir, MAX_PATH);
    if (!pathLength || pathLength >= MAX_PATH) {
        Log("[Resources] Cannot resolve full executable path (error %lu).", GetLastError());
        return false;
    }
    char* slash = strrchr(g_gameDir, '\\');
    if (!slash) {
        Log("[Resources] Executable path has no directory.");
        return false;
    }
    slash[1] = '\0';
    const HMODULE executable = GetModuleHandleW(nullptr);
    MODULEINFO moduleInfo = {};
    if (!executable || !GetModuleInformation(GetCurrentProcess(), executable, &moduleInfo, sizeof(moduleInfo))) {
        Log("[Resources] Cannot get executable image information (error %lu).", GetLastError());
        return false;
    }
    const uintptr_t base = reinterpret_cast<uintptr_t>(moduleInfo.lpBaseOfDll);
    const DWORD size = moduleInfo.SizeOfImage;
    const char* initialFileCheckSig_GLB = "\x48\x89\x5C\x24\x20\x55\x56\x57\x41\x56\x41\x57\x48\x8D\xAC\x24\x90\xFC\xFF\xFF";
    const char* initialFileCheckMask_GLB = "xxxxxxxxxxxxxxxxxxxx";
    const char* initialFileCheckSig_CLE = "\x48\x89\x5C\x24\x20\x55\x56\x57\x41\x56\x41\x57\x48\x81\xEC\x60\x02\x00\x00";
    const char* initialFileCheckMask_CLE = "xxxxxxxxxxxxxxxxxxx";
    const char* localeHandlerSig = "\x40\x55\x53\x56\x57\x41\x54\x41\x55\x41\x56\x41\x57\x48\x8D\xAC\x24\xA8\xFE\xFF\xFF";
    const char* localeHandlerMask = "xxxxxxxxxxxxxxxxxxxxx";
    uintptr_t initialFileCheckAddr = FindPattern(base, size, initialFileCheckSig_GLB, initialFileCheckMask_GLB);
    if (!initialFileCheckAddr)
        initialFileCheckAddr = FindPattern(base, size, initialFileCheckSig_CLE, initialFileCheckMask_CLE);
    const uintptr_t localeHandlerAddr = FindPattern(base, size, localeHandlerSig, localeHandlerMask);
    if (!initialFileCheckAddr || !localeHandlerAddr) {
        Log("[Resources] Missing signatures: InitialFileCheck=%p, LocaleHandler=%p.",
            reinterpret_cast<void*>(initialFileCheckAddr), reinterpret_cast<void*>(localeHandlerAddr));
        return false;
    }
    oInitialFileCheck = reinterpret_cast<InitialFileCheck_t>(initialFileCheckAddr);
    oLocaleHandler = reinterpret_cast<LocaleHandler_t>(localeHandlerAddr);
    LONG result = DetourTransactionBegin();
    if (result == NO_ERROR) {
        result = DetourUpdateThread(GetCurrentThread());
        if (result == NO_ERROR) result = DetourAttach(&oInitialFileCheck, InitialFileCheck);
        if (result == NO_ERROR) result = DetourAttach(&oLocaleHandler, hkLocaleHandler);
        if (result == NO_ERROR) result = DetourTransactionCommit();
        else DetourTransactionAbort();
    }
    if (result != NO_ERROR) {
        Log("[Resources] Detours transaction failed (%ld).", result);
        return false;
    }
    return true;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hModule);
        std::thread([] {
            InitLogFile();
            Log("[Loader] Starting resource hooks and module discovery.");
            const bool resourcesReady = InitializeResources();
            Log("[Resources] Loose-resource hooks %s.", resourcesReady ? "active" : "unavailable");
            LoadMods(Log);
        }).detach();
    }
    return TRUE;
}
