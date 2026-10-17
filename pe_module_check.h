// Copyright (c) 2026 SoraMod contributors
// SPDX-License-Identifier: MIT
#pragma once
#include <windows.h>
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

// Parse file bytes only: no module code runs during this check.
inline bool CheckModDll(const wchar_t* path, const char* exportName, std::string& reason) {
    struct FileView {
        HANDLE file = INVALID_HANDLE_VALUE;
        HANDLE mapping = nullptr;
        const BYTE* data = nullptr;
        ~FileView() {
            if (data) UnmapViewOfFile(data);
            if (mapping) CloseHandle(mapping);
            if (file != INVALID_HANDLE_VALUE) CloseHandle(file);
        }
    } view;
    const auto reject = [&](const char* message) { reason = message; return false; };
    reason.clear();
    view.file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL, nullptr);
    if (view.file == INVALID_HANDLE_VALUE)
        return reject("cannot open DLL file");
    LARGE_INTEGER fileSize = {};
    if (!GetFileSizeEx(view.file, &fileSize) || fileSize.QuadPart <= 0 ||
        static_cast<uint64_t>(fileSize.QuadPart) > SIZE_MAX)
        return reject("invalid DLL file size");
    const size_t size = static_cast<size_t>(fileSize.QuadPart);
    view.mapping = CreateFileMappingW(view.file, nullptr, PAGE_READONLY, 0, 0, nullptr);
    if (!view.mapping) return reject("cannot map DLL file");
    view.data = static_cast<const BYTE*>(MapViewOfFile(view.mapping, FILE_MAP_READ, 0, 0, 0));
    if (!view.data) return reject("cannot read DLL file mapping");
    const auto contains = [&](uint64_t offset, uint64_t length) {
        return offset <= size && length <= size - offset;
    };
    const auto read = [&](uint64_t offset, void* output, size_t length) {
        if (!contains(offset, length)) return false;
        std::memcpy(output, view.data + static_cast<size_t>(offset), length);
        return true;
    };
    IMAGE_DOS_HEADER dos = {};
    if (!read(0, &dos, sizeof(dos)) || dos.e_magic != IMAGE_DOS_SIGNATURE || dos.e_lfanew < 0)
        return reject("invalid DOS header");
    const uint64_t nt = static_cast<uint64_t>(dos.e_lfanew);
    DWORD signature = 0;
    IMAGE_FILE_HEADER fileHeader = {};
    if (!read(nt, &signature, sizeof(signature)) || signature != IMAGE_NT_SIGNATURE ||
        !read(nt + sizeof(signature), &fileHeader, sizeof(fileHeader)))
        return reject("invalid NT header");
    if (fileHeader.Machine != IMAGE_FILE_MACHINE_AMD64 ||
        !(fileHeader.Characteristics & IMAGE_FILE_DLL))
        return reject("expected an AMD64 DLL");
    const uint64_t optionalOffset = nt + sizeof(signature) + sizeof(fileHeader);
    IMAGE_OPTIONAL_HEADER64 optional = {};
    const size_t requiredOptionalBytes = offsetof(IMAGE_OPTIONAL_HEADER64, DataDirectory) + sizeof(IMAGE_DATA_DIRECTORY);
    if (fileHeader.SizeOfOptionalHeader < requiredOptionalBytes ||
        !contains(optionalOffset, fileHeader.SizeOfOptionalHeader) ||
        !read(optionalOffset, &optional, requiredOptionalBytes) ||
        optional.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC ||
        optional.NumberOfRvaAndSizes <= IMAGE_DIRECTORY_ENTRY_EXPORT)
        return reject("invalid PE32+ optional header");
    const uint64_t sectionOffset = optionalOffset + fileHeader.SizeOfOptionalHeader;
    const uint64_t sectionBytes = uint64_t(fileHeader.NumberOfSections) * sizeof(IMAGE_SECTION_HEADER);
    if (!fileHeader.NumberOfSections || !contains(sectionOffset, sectionBytes) ||
        optional.SizeOfHeaders < sectionOffset + sectionBytes ||
        !contains(0, optional.SizeOfHeaders) || optional.SizeOfHeaders > optional.SizeOfImage)
        return reject("invalid section table or header range");
    std::vector<IMAGE_SECTION_HEADER> sections(fileHeader.NumberOfSections);
    std::memcpy(sections.data(), view.data + static_cast<size_t>(sectionOffset),
        static_cast<size_t>(sectionBytes));
    for (const auto& section : sections) {
        const uint64_t extent = (std::max)(section.Misc.VirtualSize, section.SizeOfRawData);
        if (!contains(section.PointerToRawData, section.SizeOfRawData) ||
            uint64_t(section.VirtualAddress) + extent > optional.SizeOfImage)
            return reject("section exceeds file or image range");
    }

    // All RVA reads must have real raw bytes; virtual zero-filled tails are not file data.
    const auto mapRva = [&](DWORD rva, uint64_t length, size_t& offset, size_t& available) {
        if (rva < optional.SizeOfHeaders) {
            available = optional.SizeOfHeaders - rva;
            offset = rva;
            return length <= available && contains(offset, length);
        }
        for (const auto& section : sections) {
            if (rva < section.VirtualAddress) continue;
            const uint64_t delta = uint64_t(rva) - section.VirtualAddress;
            if (delta >= section.SizeOfRawData) continue;
            available = section.SizeOfRawData - static_cast<size_t>(delta);
            const uint64_t raw = uint64_t(section.PointerToRawData) + delta;
            if (length > available || !contains(raw, length)) return false;
            offset = static_cast<size_t>(raw);
            return true;
        }
        return false;
    };
    const auto& directory = optional.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT];
    size_t exportOffset = 0, available = 0;
    if (!directory.VirtualAddress || directory.Size < sizeof(IMAGE_EXPORT_DIRECTORY) ||
        uint64_t(directory.VirtualAddress) + directory.Size > optional.SizeOfImage ||
        !mapRva(directory.VirtualAddress, directory.Size, exportOffset, available))
        return reject("invalid export directory");
    IMAGE_EXPORT_DIRECTORY exports = {};
    std::memcpy(&exports, view.data + exportOffset, sizeof(exports));
    size_t names = 0, ordinals = 0, functions = 0;
    if (!exports.NumberOfNames || !exports.NumberOfFunctions || !exports.AddressOfNames ||
        !exports.AddressOfNameOrdinals || !exports.AddressOfFunctions ||
        !mapRva(exports.AddressOfNames, uint64_t(exports.NumberOfNames) * sizeof(DWORD), names, available) ||
        !mapRva(exports.AddressOfNameOrdinals, uint64_t(exports.NumberOfNames) * sizeof(WORD), ordinals, available) ||
        !mapRva(exports.AddressOfFunctions, uint64_t(exports.NumberOfFunctions) * sizeof(DWORD), functions, available))
        return reject("invalid export arrays");
    DWORD entryRva = 0;
    bool found = false;
    const char* previousName = nullptr;
    for (DWORD i = 0; i < exports.NumberOfNames; ++i) {
        DWORD nameRva = 0;
        WORD ordinal = 0;
        std::memcpy(&nameRva, view.data + names + size_t(i) * sizeof(DWORD), sizeof(nameRva));
        std::memcpy(&ordinal, view.data + ordinals + size_t(i) * sizeof(WORD), sizeof(ordinal));
        if (ordinal >= exports.NumberOfFunctions)
            return reject("export ordinal exceeds function table");
        size_t nameOffset = 0;
        if (!nameRva || !mapRva(nameRva, 1, nameOffset, available))
            return reject("invalid export name RVA");
        const char* name = reinterpret_cast<const char*>(view.data + nameOffset);
        if (!std::memchr(name, '\0', available)) return reject("unterminated export name");
        // GetProcAddress searches the sorted name table; reject ambiguous/malformed ordering.
        if (previousName && std::strcmp(previousName, name) >= 0)
            return reject("export names are not strictly sorted");
        previousName = name;
        if (std::strcmp(name, exportName) == 0) {
            std::memcpy(&entryRva, view.data + functions + size_t(ordinal) * sizeof(DWORD), sizeof(entryRva));
            found = true;
        }
    }
    if (!found) return reject("declared initialization export is missing");
    if (!entryRva) return reject("initialization export has a null RVA");
    if (entryRva >= directory.VirtualAddress &&
        uint64_t(entryRva) - directory.VirtualAddress < directory.Size)
        return reject("forwarded initialization exports are unsupported");
    size_t entryOffset = 0;
    if (!mapRva(entryRva, 1, entryOffset, available))
        return reject("initialization export has no file-backed bytes");
    for (const auto& section : sections) {
        if (entryRva >= section.VirtualAddress &&
            uint64_t(entryRva) - section.VirtualAddress < section.SizeOfRawData &&
            (section.Characteristics & IMAGE_SCN_MEM_EXECUTE))
            return true;
    }
    return reject("initialization export is not in an executable section");
}
