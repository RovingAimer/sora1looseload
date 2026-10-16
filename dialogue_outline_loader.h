// Copyright (c) 2026 DialogueOutline contributors
// SPDX-License-Identifier: MIT
// Fixed DialogueOutline module entry for this sora1looseload fork.
#pragma once
#include <windows.h>
#include <cwchar>

// Call only from the existing worker, after its Detours transaction completes.
// The core's DllMain does no work; explicit initialization happens after LoadLibrary returns.
inline void LoadDialogueOutline(void (*log)(const char*, ...)) noexcept {
    wchar_t path[32768] = {};
    const DWORD length = GetModuleFileNameW(nullptr, path, 32768);
    if (!length || length >= 32768) {
        log("[DialogueOutline] Cannot resolve executable directory (error %lu).", GetLastError());
        return;
    }
    wchar_t* slash = std::wcsrchr(path, L'\\');
    if (!slash) {
        log("[DialogueOutline] Executable path has no directory.");
        return;
    }
    slash[1] = L'\0';
    if (wcscat_s(path, L"mods\\DialogueOutline\\DialogueOutline.dll") != 0) {
        log("[DialogueOutline] Fixed module path is too long.");
        return;
    }
    const DWORD attributes = GetFileAttributesW(path);
    if (attributes == INVALID_FILE_ATTRIBUTES) {
        const DWORD error = GetLastError();
        if (error != ERROR_FILE_NOT_FOUND && error != ERROR_PATH_NOT_FOUND)
            log("[DialogueOutline] Cannot inspect optional module (error %lu).", error);
        return; // Absent optional module: retain normal loose-resource behavior quietly.
    }
    if (attributes & FILE_ATTRIBUTE_DIRECTORY) {
        log("[DialogueOutline] Fixed module path is a directory.");
        return;
    }
    const HMODULE core = LoadLibraryExW(path, nullptr,
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if (!core) {
        log("[DialogueOutline] Optional module load failed (error %lu); loose loader remains active.",
            GetLastError());
        return;
    }
    using Initialize = DWORD (WINAPI*)();
    const auto initialize = reinterpret_cast<Initialize>(GetProcAddress(core, "SoraDialogueInitialize"));
    if (!initialize) {
        log("[DialogueOutline] SoraDialogueInitialize is missing (error %lu); loose loader remains active.",
            GetLastError());
        return;
    }
    const DWORD status = initialize();
    // ABI v1: HookActive is 0x8. A nonzero status alone never means initialization succeeded.
    const char* outcome = "hook inactive or initialization failed";
    if (status & 0x8)
        outcome = (status & 0x800) ? "hook active with memory-finalization warning" : "hook active";
    log("[DialogueOutline] Initialization status: 0x%08lX (%s); loose loader remains active.",
        status, outcome);
    // Keep every loaded module mapped for process lifetime. The core pins itself before
    // publishing a hook; even a failed initialization must never invalidate live code.
}
