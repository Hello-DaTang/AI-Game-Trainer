/* Harmless local fixture for the AI Game Trainer CE read/write smoke test.
 * No injection, drivers, persistence, networking or external game interaction.
 * Built into Tools/AITrainerDemo.exe with MSVC /MT for a standalone runtime.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <wchar.h>

static volatile LONG g_demo_number = 123;

int wmain(int argc, wchar_t **argv)
{
    FILE *out = NULL;
    if (argc != 3 || wcscmp(argv[1], L"--ready-file") != 0) {
        return 2;
    }
    if (_wfopen_s(&out, argv[2], L"wb") != 0 || out == NULL) {
        return 3;
    }
    fprintf(out, "{\"pid\":%lu,\"address\":\"0x%llX\"}",
            (unsigned long)GetCurrentProcessId(),
            (unsigned long long)(uintptr_t)&g_demo_number);
    fclose(out);

    /* Refer to the volatile number so the compiler retains the symbol. */
    while (1) {
        if (g_demo_number == -1) {
            return 0;
        }
        Sleep(100);
    }
}
