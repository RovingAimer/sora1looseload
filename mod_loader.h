// Copyright (c) 2026 SoraMod contributors
// SPDX-License-Identifier: MIT
#pragma once
#include "pe_module_check.h"
#include <algorithm>
#include <cwchar>
#include <string>
#include <vector>

// Called once from the startup worker, after the resource-hook attempt.
inline void LoadMods(void (*log)(const char*, ...)) {
    wchar_t executable[32768] = {};
    const DWORD length = GetModuleFileNameW(nullptr, executable, 32768);
    if (!length || length >= 32768) {
        log("[Mods] Cannot resolve executable directory (error %lu).", GetLastError());
        return;
    }
    wchar_t* slash = std::wcsrchr(executable, L'\\');
    if (!slash) {
        log("[Mods] Executable path has no directory.");
        return;
    }
    slash[1] = L'\0';
    const std::wstring root = std::wstring(executable) + L"mods\\";
    const std::wstring search = root + L"*";
    if (search.size() >= 32768) {
        log("[Mods] Discovery path is too long.");
        return;
    }
    WIN32_FIND_DATAW item = {};
    const HANDLE find = FindFirstFileW(search.c_str(), &item);
    if (find == INVALID_HANDLE_VALUE) {
        const DWORD error = GetLastError();
        if (error != ERROR_FILE_NOT_FOUND && error != ERROR_PATH_NOT_FOUND)
            log("[Mods] Cannot enumerate module directories (error %lu).", error);
        else
            log("[Mods] No module directories found.");
        return;
    }
    std::vector<std::wstring> directories;
    do {
        if ((item.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) &&
            std::wcscmp(item.cFileName, L".") && std::wcscmp(item.cFileName, L".."))
            directories.emplace_back(item.cFileName);
    } while (FindNextFileW(find, &item));
    const DWORD enumerationError = GetLastError();
    FindClose(find);
    if (enumerationError != ERROR_NO_MORE_FILES)
        log("[Mods] Directory enumeration stopped (error %lu); processing discovered entries.", enumerationError);
    std::stable_sort(directories.begin(), directories.end(), [](const std::wstring& a, const std::wstring& b) {
        const int order = CompareStringOrdinal(a.c_str(), -1, b.c_str(), -1, TRUE);
        return order == CSTR_LESS_THAN || (order == CSTR_EQUAL && a < b);
    });
    std::vector<HMODULE> initialized;
    for (const auto& directory : directories) {
        const std::wstring moduleDirectory = root + directory + L"\\";
        const std::wstring manifest = moduleDirectory + L"sora_mod.ini";
        if (manifest.size() >= 32768) {
            log("[Mods] %ls: declaration path is too long; skipped.", directory.c_str());
            continue;
        }
        const DWORD attributes = GetFileAttributesW(manifest.c_str());
        if (attributes == INVALID_FILE_ATTRIBUTES) {
            const DWORD error = GetLastError();
            if (error != ERROR_FILE_NOT_FOUND && error != ERROR_PATH_NOT_FOUND)
                log("[Mods] %ls: cannot inspect declaration (error %lu); skipped.", directory.c_str(), error);
            continue;
        }
        if (attributes & FILE_ATTRIBUTE_DIRECTORY) {
            log("[Mods] %ls: sora_mod.ini is a directory; skipped.", directory.c_str());
            continue;
        }
        log("[Mods] %ls: declaration found.", directory.c_str());
        const auto field = [&](const wchar_t* key, const wchar_t* fallback, std::wstring& value) {
            wchar_t buffer[1024] = {};
            const DWORD count = GetPrivateProfileStringW(L"SoraMod", key, fallback, buffer, 1024, manifest.c_str());
            if (count >= 1023) return false;
            value.assign(buffer, count);
            return true;
        };
        std::wstring enabled, api, dll, entry;
        if (!field(L"Enabled", L"1", enabled)) {
            log("[Mods] %ls: Enabled is too long; skipped.", directory.c_str());
            continue;
        }
        if (enabled == L"0") {
            log("[Mods] %ls: disabled; skipped.", directory.c_str());
            continue;
        }
        if (enabled != L"1" || !field(L"Api", L"", api) || api != L"1" ||
            !field(L"DLL", L"", dll) || !field(L"Initialize", L"SoraModInitialize", entry)) {
            log("[Mods] %ls: invalid declaration (expected Enabled=0/1, Api=1 and DLL); skipped.", directory.c_str());
            continue;
        }
        if (dll.size() <= 4 || dll.find_first_of(L"\\/:*?\"<>|") != std::wstring::npos ||
            _wcsicmp(dll.c_str() + dll.size() - 4, L".dll") != 0) {
            log("[Mods] %ls: DLL must be a same-directory .dll leaf filename; skipped.", directory.c_str());
            continue;
        }
        std::string exportName;
        for (const wchar_t character : entry) {
            if (character < 0x21 || character > 0x7e) break;
            exportName.push_back(static_cast<char>(character));
        }
        if (exportName.empty() || exportName.size() != entry.size()) {
            log("[Mods] %ls: Initialize must be a nonempty ASCII export name; skipped.", directory.c_str());
            continue;
        }
        const std::wstring path = moduleDirectory + dll;
        if (path.size() >= 32768) {
            log("[Mods] %ls: DLL path is too long; skipped.", directory.c_str());
            continue;
        }
        std::string reason;
        if (!CheckModDll(path.c_str(), exportName.c_str(), reason)) {
            log("[Mods] %ls: precheck rejected %ls (%s); skipped.", directory.c_str(), dll.c_str(), reason.c_str());
            continue;
        }
        const HMODULE module = LoadLibraryExW(path.c_str(), nullptr,
            LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
        if (!module) {
            log("[Mods] %ls: load failed (error %lu); skipped.", directory.c_str(), GetLastError());
            continue;
        }
        // Every loaded module stays mapped: even DllMain may have published live code.
        if (std::find(initialized.begin(), initialized.end(), module) != initialized.end()) {
            log("[Mods] %ls: module handle already initialized; skipped.", directory.c_str());
            continue;
        }
        using Initialize = DWORD (WINAPI*)(void);
        const auto initialize = reinterpret_cast<Initialize>(GetProcAddress(module, exportName.c_str()));
        if (!initialize) {
            log("[Mods] %ls: cannot resolve %s after loading (error %lu); skipped.",
                directory.c_str(), exportName.c_str(), GetLastError());
            continue;
        }
        initialized.push_back(module);
        const DWORD status = initialize();
        log("[Mods] %ls: %s returned 0x%08lX.", directory.c_str(), exportName.c_str(), status);
    }
}
