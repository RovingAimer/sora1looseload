#include "pch.h"
#pragma comment(linker, "/EXPORT:XInputEnable=XInputEnable,@5")
#pragma comment(linker, "/EXPORT:XInputGetAudioDeviceIds=XInputGetAudioDeviceIds,@10")
#pragma comment(linker, "/EXPORT:XInputGetBatteryInformation=XInputGetBatteryInformation,@7")
#pragma comment(linker, "/EXPORT:XInputGetCapabilities=XInputGetCapabilities,@4")
#pragma comment(linker, "/EXPORT:XInputGetKeystroke=XInputGetKeystroke,@8")
#pragma comment(linker, "/EXPORT:XInputGetState=XInputGetState,@2")
#pragma comment(linker, "/EXPORT:XInputSetState=XInputSetState,@3")

#include <Windows.h>
#include <cstdlib>

#ifdef __cplusplus
extern "C" {
#endif

    HINSTANCE s_instance = NULL;
    struct XINPUT_STATE {};
    struct XINPUT_CAPABILITIES {};
    struct XINPUT_BATTERY_INFORMATION {};
    struct XINPUT_KEYSTROKE {};

    typedef void (WINAPI* f_XInputEnable)(BOOL);
    typedef DWORD(WINAPI* f_XInputGetAudioDeviceIds)(DWORD, LPWSTR, UINT*, LPWSTR, UINT*);
    typedef DWORD(WINAPI* f_XInputGetBatteryInformation)(DWORD, BYTE, XINPUT_BATTERY_INFORMATION*);
    typedef DWORD(WINAPI* f_XInputGetCapabilities)(DWORD, DWORD, XINPUT_CAPABILITIES*);
    typedef DWORD(WINAPI* f_XInputGetKeystroke)(DWORD, DWORD, XINPUT_KEYSTROKE*);
    typedef DWORD(WINAPI* f_XInputGetState)(DWORD, XINPUT_STATE*);
    typedef DWORD(WINAPI* f_XInputSetState)(DWORD, void*);

    f_XInputEnable s_XInputEnable = NULL;
    f_XInputGetAudioDeviceIds s_XInputGetAudioDeviceIds = NULL;
    f_XInputGetBatteryInformation s_XInputGetBatteryInformation = NULL;
    f_XInputGetCapabilities s_XInputGetCapabilities = NULL;
    f_XInputGetKeystroke s_XInputGetKeystroke = NULL;
    f_XInputGetState s_XInputGetState = NULL;
    f_XInputSetState s_XInputSetState = NULL;

    INIT_ONCE s_initializeOnce = INIT_ONCE_STATIC_INIT;

    BOOL CALLBACK InitializeSystemXInput(PINIT_ONCE, PVOID, PVOID*)
    {
        WCHAR path[MAX_PATH] = {};
        const UINT length = GetSystemDirectoryW(path, MAX_PATH);
        if (!length || length > MAX_PATH - _countof(L"\\XInput1_4.dll"))
            return TRUE; // Cache failure too; wrappers keep their existing fallbacks.
        wcscat_s(path, L"\\XInput1_4.dll");
        s_instance = LoadLibraryW(path);

        if (!s_instance)
            return TRUE;

        s_XInputEnable = (f_XInputEnable)GetProcAddress(s_instance, "XInputEnable");
        s_XInputGetAudioDeviceIds = (f_XInputGetAudioDeviceIds)GetProcAddress(s_instance, "XInputGetAudioDeviceIds");
        s_XInputGetBatteryInformation = (f_XInputGetBatteryInformation)GetProcAddress(s_instance, "XInputGetBatteryInformation");
        s_XInputGetCapabilities = (f_XInputGetCapabilities)GetProcAddress(s_instance, "XInputGetCapabilities");
        s_XInputGetKeystroke = (f_XInputGetKeystroke)GetProcAddress(s_instance, "XInputGetKeystroke");
        s_XInputGetState = (f_XInputGetState)GetProcAddress(s_instance, "XInputGetState");
        s_XInputSetState = (f_XInputSetState)GetProcAddress(s_instance, "XInputSetState");
        return TRUE;
    }

    void WINAPI XInputEnable(BOOL enable)
    {
        InitOnceExecuteOnce(&s_initializeOnce, InitializeSystemXInput, nullptr, nullptr);
        if (s_XInputEnable)
            s_XInputEnable(enable);
    }

    DWORD WINAPI XInputGetAudioDeviceIds(DWORD dwUserIndex, LPWSTR pRenderDeviceId, UINT* pRenderCount, LPWSTR pCaptureDeviceId, UINT* pCaptureCount)
    {
        InitOnceExecuteOnce(&s_initializeOnce, InitializeSystemXInput, nullptr, nullptr);
        if (!s_XInputGetAudioDeviceIds)
            return ERROR_DEVICE_NOT_CONNECTED;
        return s_XInputGetAudioDeviceIds(dwUserIndex, pRenderDeviceId, pRenderCount, pCaptureDeviceId, pCaptureCount);
    }

    DWORD WINAPI XInputGetBatteryInformation(DWORD dwUserIndex, BYTE devType, XINPUT_BATTERY_INFORMATION* pBatteryInformation)
    {
        InitOnceExecuteOnce(&s_initializeOnce, InitializeSystemXInput, nullptr, nullptr);
        if (!s_XInputGetBatteryInformation)
            return ERROR_DEVICE_NOT_CONNECTED;
        return s_XInputGetBatteryInformation(dwUserIndex, devType, pBatteryInformation);
    }

    DWORD WINAPI XInputGetCapabilities(DWORD dwUserIndex, DWORD dwFlags, XINPUT_CAPABILITIES* pCapabilities)
    {
        InitOnceExecuteOnce(&s_initializeOnce, InitializeSystemXInput, nullptr, nullptr);
        if (!s_XInputGetCapabilities)
            return ERROR_DEVICE_NOT_CONNECTED;
        return s_XInputGetCapabilities(dwUserIndex, dwFlags, pCapabilities);
    }

    DWORD WINAPI XInputGetKeystroke(DWORD dwUserIndex, DWORD dwReserved, XINPUT_KEYSTROKE* pKeystroke)
    {
        InitOnceExecuteOnce(&s_initializeOnce, InitializeSystemXInput, nullptr, nullptr);
        if (!s_XInputGetKeystroke)
            return ERROR_DEVICE_NOT_CONNECTED;
        return s_XInputGetKeystroke(dwUserIndex, dwReserved, pKeystroke);
    }

    DWORD WINAPI XInputGetState(DWORD dwUserIndex, XINPUT_STATE* pState)
    {
        InitOnceExecuteOnce(&s_initializeOnce, InitializeSystemXInput, nullptr, nullptr);
        if (!s_XInputGetState)
            return ERROR_DEVICE_NOT_CONNECTED;
        return s_XInputGetState(dwUserIndex, pState);
    }

    DWORD WINAPI XInputSetState(DWORD dwUserIndex, void* pVibration)
    {
        InitOnceExecuteOnce(&s_initializeOnce, InitializeSystemXInput, nullptr, nullptr);
        if (!s_XInputSetState)
            return ERROR_DEVICE_NOT_CONNECTED;
        return s_XInputSetState(dwUserIndex, pVibration);
    }

#ifdef __cplusplus
}
#endif
