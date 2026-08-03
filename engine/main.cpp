#define _CRT_SECURE_NO_WARNINGS
#include <iostream>
#include <string>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

// Workaround to prevent MSVC from searching for the Python debug library (pythonXX_d.lib)
#if defined(_MSC_VER) && defined(_DEBUG)
    #undef _DEBUG
    #include <Python.h>
    #define _DEBUG
#else
    #include <Python.h>
#endif

#include "webview.h"

#ifdef ESD_EMBED_HTML
#include "embedded_html.h"
static std::string GetPageHtml(const std::string& path) {
    const auto& map = GetEmbeddedHtml();
    auto it = map.find(path);
    return (it != map.end()) ? it->second : std::string();
}
#endif

#ifdef _WIN32
#include <direct.h>
#define GetCurrentDir _getcwd
#include <windows.h>
#include <dwmapi.h>
#include <shellapi.h>
#ifndef DWMWA_CAPTION_COLOR
#define DWMWA_CAPTION_COLOR 35
#endif
#else
#include <unistd.h>
#define GetCurrentDir getcwd
#endif

// ── Modal parsing helpers ──────────────────────────────────────────────────

// Extract a quoted attribute value from an HTML-like opening tag string.
static std::string ModalAttr(const std::string& tag, const std::string& attr,
                              const std::string& def = "") {
    for (char q : {'"', '\''}) {
        std::string key = attr + "=";
        key += q;
        auto pos = tag.find(key);
        if (pos == std::string::npos) continue;
        pos += key.size();
        auto end = tag.find(q, pos);
        if (end == std::string::npos) continue;
        return tag.substr(pos, end - pos);
    }
    return def;
}

// Extract the first opening tag (e.g. "<modal ...>") for a given tag name.
static std::string ModalOpenTag(const std::string& html, const std::string& tag) {
    auto start = html.find("<" + tag);
    if (start == std::string::npos) return "";
    auto end = html.find('>', start);
    if (end == std::string::npos) return "";
    return html.substr(start, end - start + 1);
}

// Extract the trimmed inner content between <tag ...> and </tag>.
static std::string ModalInner(const std::string& html, const std::string& tag) {
    auto open = html.find("<" + tag);
    if (open == std::string::npos) return "";
    auto bodyStart = html.find('>', open);
    if (bodyStart == std::string::npos) return "";
    bodyStart++;
    auto close = html.find("</" + tag + ">", bodyStart);
    if (close == std::string::npos) return "";
    std::string inner = html.substr(bodyStart, close - bodyStart);
    auto s = inner.find_first_not_of(" \t\r\n");
    if (s == std::string::npos) return "";
    auto e = inner.find_last_not_of(" \t\r\n");
    return inner.substr(s, e - s + 1);
}

// ── Modal OS-window thread ─────────────────────────────────────────────────

struct ModalThreadParams {
    std::string generatedHtml;
    std::string windowTitle;
    int   width;
    int   height;
    int   cornerRadius;  // rounded corners applied to frameless windows (0 = none)
    bool  useOsChrome;   // true = native OS titlebar; false = WS_POPUP (frameless)
    bool  closeable;
    bool  devTools;
    webview::webview* parentWv;
};

static DWORD WINAPI ModalWindowThread(LPVOID param) {
    auto* p = static_cast<ModalThreadParams*>(param);
    CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);

    std::string result = "null";

    {
        webview::webview modal(p->devTools, nullptr);
        HWND mhwnd = static_cast<HWND>(modal.window());

#ifdef _WIN32
        ShowWindow(mhwnd, SW_HIDE);
        if (!p->useOsChrome) {
            // Frameless popup — strip all OS window chrome
            LONG_PTR style = GetWindowLongPtr(mhwnd, GWL_STYLE);
            style = (style & ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX))
                  | WS_POPUP;
            SetWindowLongPtr(mhwnd, GWL_STYLE, style);
            SetWindowPos(mhwnd, nullptr, 0, 0, 0, 0,
                         SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED);
        } else {
            // Native titlebar — keep chrome but lock size and set title
            modal.set_title(p->windowTitle);
            if (!p->closeable) {
                HMENU hMenu = GetSystemMenu(mhwnd, FALSE);
                if (hMenu)
                    EnableMenuItem(hMenu, SC_CLOSE,
                                   MF_BYCOMMAND | MF_DISABLED | MF_GRAYED);
            }
        }

        // Inherit app icon
        HICON hIcon = LoadIcon(GetModuleHandle(nullptr), MAKEINTRESOURCE(101));
        if (hIcon) {
            SendMessage(mhwnd, WM_SETICON, ICON_BIG,   (LPARAM)hIcon);
            SendMessage(mhwnd, WM_SETICON, ICON_SMALL, (LPARAM)hIcon);
        }
#endif
        // Set size (handles DPI scaling internally)
        modal.set_size(p->width, p->height, WEBVIEW_HINT_FIXED);

#ifdef _WIN32
        // Center on nearest monitor
        {
            RECT wr;
            GetWindowRect(mhwnd, &wr);
            int aw = wr.right - wr.left;
            int ah = wr.bottom - wr.top;
            HWND parentHwnd = p->parentWv
                ? static_cast<HWND>(p->parentWv->window())
                : nullptr;
            HMONITOR hMon = MonitorFromWindow(
                parentHwnd ? parentHwnd : mhwnd,
                MONITOR_DEFAULTTONEAREST);
            MONITORINFO mi = { sizeof(mi) };
            if (GetMonitorInfo(hMon, &mi)) {
                int x = mi.rcWork.left + (mi.rcWork.right  - mi.rcWork.left - aw) / 2;
                int y = mi.rcWork.top  + (mi.rcWork.bottom - mi.rcWork.top  - ah) / 2;
                SetWindowPos(mhwnd, HWND_TOP, x, y, 0, 0,
                             SWP_NOSIZE | SWP_NOACTIVATE);
            }
        }

        // Apply rounded corners to frameless windows
        if (!p->useOsChrome && p->cornerRadius > 0) {
            RECT wr;
            GetWindowRect(mhwnd, &wr);
            int aw = wr.right - wr.left;
            int ah = wr.bottom - wr.top;
            int r  = p->cornerRadius;
            HRGN hRgn = CreateRoundRectRgn(0, 0, aw, ah, r, r);
            SetWindowRgn(mhwnd, hRgn, TRUE);
        }
#endif

        // _modalClose: called by closeModal() inside the modal HTML
        modal.bind("_modalClose", [&result, &modal](std::string req) -> std::string {
            // req arrives as a JSON array e.g. [true] or ["hello"] or [null]
            std::string val = req;
            if (val.size() >= 2 && val.front() == '[' && val.back() == ']')
                val = val.substr(1, val.size() - 2);
            if (val.empty()) val = "null";
            result = val;
            modal.terminate();
            return "";
        });

        // dragWindow: lets custom titlebars initiate native window drag
        modal.bind("dragWindow", [mhwnd](std::string) -> std::string {
#ifdef _WIN32
            if (mhwnd) { ReleaseCapture(); SendMessage(mhwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0); }
#endif
            return "";
        });

        // Reveal the modal only after its document is ready. The native HWND
        // remains hidden while its final style, size, position, and content
        // are prepared, preventing the default-position startup flash.
        bool modalWaitingToShow = true;
        modal.bind("__esdModalWindowReady", [mhwnd, &modalWaitingToShow](std::string) -> std::string {
#ifdef _WIN32
            if (mhwnd && modalWaitingToShow) {
                modalWaitingToShow = false;
                ShowWindow(mhwnd, SW_SHOWNORMAL);
                SetWindowPos(mhwnd, nullptr, 0, 0, 0, 0,
                             SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER |
                             SWP_NOACTIVATE | SWP_FRAMECHANGED);
                RECT client{};
                if (GetClientRect(mhwnd, &client)) {
                    SendMessage(mhwnd, WM_SIZE, SIZE_RESTORED,
                                MAKELPARAM(client.right - client.left,
                                          client.bottom - client.top));
                }
                RedrawWindow(mhwnd, nullptr, nullptr,
                             RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN |
                             RDW_UPDATENOW);
                UpdateWindow(mhwnd);
                SetForegroundWindow(mhwnd);
                SetFocus(mhwnd);
            }
#endif
            return "";
        });
        modal.init(
            "(function(){"
            "function ready(){setTimeout(function(){"
            "if(window.__esdModalWindowReady)window.__esdModalWindowReady('');"
            "},0);}"
            "if(document.readyState==='loading')"
            "window.addEventListener('DOMContentLoaded',ready,{once:true});"
            "else ready();"
            "})();");

        modal.set_html(p->generatedHtml);
        modal.run();
    }

    // Resolve the parent window's Promise with the modal's return value
    std::string resolvedValue   = result;
    webview::webview* parentWv  = p->parentWv;
    parentWv->dispatch([parentWv, resolvedValue]() {
        parentWv->eval("window.__esd_resolveModal(" + resolvedValue + ")");
    });

    delete p;
    CoUninitialize();
    return 0;
}

// Helper to get current directory and resolve project root
std::string GetCurrentWorkingDir() {
    char buff[FILENAME_MAX];
    GetCurrentDir(buff, FILENAME_MAX);
    std::string cwd(buff);
    
    // If run from within the build directory, strip it to reach the project root.
    size_t buildPos = cwd.find("\\build");
    if (buildPos == std::string::npos) buildPos = cwd.find("/build");
    if (buildPos != std::string::npos) {
        cwd = cwd.substr(0, buildPos);
    }
    return cwd;
}

// Helper to load properties.config
std::unordered_map<std::string, std::string> LoadConfig(const std::string& filename) {
    std::unordered_map<std::string, std::string> config;
    std::ifstream file(filename);
    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;
        // Trim carriage return if present (Windows CRLF issue)
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        auto delimiterPos = line.find('=');
        if (delimiterPos != std::string::npos) {
            std::string key = line.substr(0, delimiterPos);
            std::string value = line.substr(delimiterPos + 1);
            config[key] = value;
        }
    }
    return config;
}

#ifdef _WIN32
// Tell MSVC linker to build a Windows GUI app (no console by default) but keep main() as the entrypoint.
#pragma comment(linker, "/SUBSYSTEM:windows /ENTRY:mainCRTStartup")
#endif

// Function to route a string payload to Python's /server/api.py
std::string CallPythonBackend(const std::string& message) {
    std::string resultStr = "{\"error\": \"Failed to call Python\"}";
    
    // Import the API module
    PyObject* pName = PyUnicode_DecodeFSDefault("server.api");
    PyObject* pModule = PyImport_Import(pName);
    Py_DECREF(pName);

    if (pModule != nullptr) {
        PyObject* pFunc = PyObject_GetAttrString(pModule, "handle_message");
        if (pFunc && PyCallable_Check(pFunc)) {
            // Pass the string argument
            PyObject* pArgs = PyTuple_New(1);
            PyTuple_SetItem(pArgs, 0, PyUnicode_FromString(message.c_str()));
            
            PyObject* pValue = PyObject_CallObject(pFunc, pArgs);
            Py_DECREF(pArgs);
            if (pValue != nullptr) {
                resultStr = PyUnicode_AsUTF8(pValue);
                Py_DECREF(pValue);
            }
        } else {
            if (PyErr_Occurred()) PyErr_Print();
        }
        Py_XDECREF(pFunc);
        Py_DECREF(pModule);
    } else {
        if (PyErr_Occurred()) PyErr_Print();
    }
    return resultStr;
}

#ifdef _WIN32
struct NativeWindowState {
    WNDPROC originalProc = nullptr;
    int cornerRadius = 0;
    bool frameless = false;
};

static NativeWindowState g_nativeWindowState;

static void UpdateRoundedWindowRegion(HWND hwnd, bool maximized) {
    if (!hwnd) return;
    if (!g_nativeWindowState.frameless ||
        g_nativeWindowState.cornerRadius <= 0 ||
        maximized) {
        SetWindowRgn(hwnd, nullptr, TRUE);
        return;
    }

    RECT rect{};
    if (!GetWindowRect(hwnd, &rect)) return;
    const int width = rect.right - rect.left;
    const int height = rect.bottom - rect.top;
    const int radius = g_nativeWindowState.cornerRadius;
    HRGN region = CreateRoundRectRgn(0, 0, width + 1, height + 1, radius, radius);
    if (region && !SetWindowRgn(hwnd, region, TRUE)) {
        DeleteObject(region);
    }
}

static LRESULT CALLBACK EsdkWindowProc(HWND hwnd, UINT message, WPARAM wParam, LPARAM lParam) {
    WNDPROC original = g_nativeWindowState.originalProc;
    LRESULT result = CallWindowProc(original, hwnd, message, wParam, lParam);

    if (message == WM_SIZE && g_nativeWindowState.frameless) {
        if (wParam == SIZE_MAXIMIZED) {
            UpdateRoundedWindowRegion(hwnd, true);
        } else if (wParam == SIZE_RESTORED) {
            UpdateRoundedWindowRegion(hwnd, false);
        }
    } else if (message == WM_DPICHANGED && g_nativeWindowState.frameless) {
        UpdateRoundedWindowRegion(hwnd, IsZoomed(hwnd) != FALSE);
    }
    return result;
}

static void InstallEsdkWindowProcedure(HWND hwnd) {
    if (!hwnd || g_nativeWindowState.originalProc) return;
    g_nativeWindowState.originalProc = reinterpret_cast<WNDPROC>(
        SetWindowLongPtr(hwnd, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(EsdkWindowProc)));
}

static void ShowPreparedWindow(HWND hwnd) {
    if (!hwnd) return;
    ShowWindow(hwnd, SW_SHOW);
    SetWindowPos(hwnd, nullptr, 0, 0, 0, 0,
                 SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER |
                 SWP_NOACTIVATE | SWP_FRAMECHANGED);
    RECT client{};
    if (GetClientRect(hwnd, &client)) {
        SendMessage(hwnd, WM_SIZE, IsZoomed(hwnd) ? SIZE_MAXIMIZED : SIZE_RESTORED,
                    MAKELPARAM(client.right - client.left,
                              client.bottom - client.top));
    }
    RedrawWindow(hwnd, nullptr, nullptr,
                 RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW);
    UpdateWindow(hwnd);
    DwmFlush();
    SetForegroundWindow(hwnd);
    SetFocus(hwnd);
}
#endif

// Applies window properties dynamically to the window handle
void ApplyWindowProperties(webview::webview& w, HWND hwnd, const std::unordered_map<std::string, std::string>& config, bool& dragBackgroundOut) {
    std::string title = config.count("TITLE") ? config.at("TITLE") : "ESD Suite Framework";
    w.set_title(title);

    int windowWidth = 800;
    if (config.count("WINDOW_WIDTH")) {
        try { windowWidth = std::stoi(config.at("WINDOW_WIDTH")); } catch(...) {}
    }
    
    int windowHeight = 600;
    if (config.count("WINDOW_HEIGHT")) {
        try { windowHeight = std::stoi(config.at("WINDOW_HEIGHT")); } catch(...) {}
    }
    
    w.set_size(windowWidth, windowHeight, WEBVIEW_HINT_NONE);
    dragBackgroundOut = (config.count("DRAG_BACKGROUND") && config.at("DRAG_BACKGROUND") == "true");

#ifdef _WIN32
    if (!hwnd) return;

    bool canClose = (config.count("CAN_CLOSE") == 0 || config.at("CAN_CLOSE") != "false");
    bool canMinimize = (config.count("CAN_MINIMIZE") == 0 || config.at("CAN_MINIMIZE") != "false");
    bool canMaximize = (config.count("CAN_MAXIMIZE") == 0 || config.at("CAN_MAXIMIZE") != "false");
    bool showTitlebar = (config.count("TITLEBAR") == 0 || config.at("TITLEBAR") != "false");
    
    int cornerRadius = 0;
    if (config.count("CORNER_RADIUS")) {
        try { cornerRadius = std::stoi(config.at("CORNER_RADIUS")); } catch(...) {}
    }

    std::string iconPath = config.count("ICON") ? config.at("ICON") : "";
    if (!iconPath.empty()) {
        HICON hIcon = (HICON)LoadImageA(NULL, iconPath.c_str(), IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE);
        if (hIcon) {
            SendMessage(hwnd, WM_SETICON, ICON_BIG, (LPARAM)hIcon);
            SendMessage(hwnd, WM_SETICON, ICON_SMALL, (LPARAM)hIcon);
        }
    }

    // Apply window styles based on properties
    LONG_PTR style = GetWindowLongPtr(hwnd, GWL_STYLE);
    if (!canMinimize) style &= ~WS_MINIMIZEBOX; else style |= WS_MINIMIZEBOX;
    if (!canMaximize) style &= ~WS_MAXIMIZEBOX; else style |= WS_MAXIMIZEBOX;
    if (!showTitlebar) {
        style &= ~WS_CAPTION;
        // Keep the native sizing frame when maximizing is allowed. It is
        // visually frameless without WS_CAPTION, but Windows retains correct
        // maximize, restore, snap, work-area, and minimum-size behavior.
        if (canMaximize) style |= WS_THICKFRAME;
        else style &= ~WS_THICKFRAME;
    } else {
        style |= (WS_CAPTION | WS_THICKFRAME);
    }
    SetWindowLongPtr(hwnd, GWL_STYLE, style);

    g_nativeWindowState.frameless = !showTitlebar;
    g_nativeWindowState.cornerRadius = cornerRadius;
    
    // Center the window on the screen and force it to redraw its frame
    HMONITOR hMonitor = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST);
    MONITORINFO mi = { sizeof(mi) };
    if (GetMonitorInfo(hMonitor, &mi)) {
        RECT windowRect{};
        GetWindowRect(hwnd, &windowRect);
        int actualWidth = windowRect.right - windowRect.left;
        int actualHeight = windowRect.bottom - windowRect.top;
        int screenWidth = mi.rcWork.right - mi.rcWork.left;
        int screenHeight = mi.rcWork.bottom - mi.rcWork.top;
        int x = mi.rcWork.left + (screenWidth - actualWidth) / 2;
        int y = mi.rcWork.top + (screenHeight - actualHeight) / 2;
        SetWindowPos(hwnd, NULL, x, y, actualWidth, actualHeight,
                     SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED);
    } else {
        SetWindowPos(hwnd, NULL, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED);
    }

    UpdateRoundedWindowRegion(hwnd, IsZoomed(hwnd) != FALSE);

    HMENU hMenu = GetSystemMenu(hwnd, FALSE);
    if (!canClose) {
        EnableMenuItem(hMenu, SC_CLOSE, MF_BYCOMMAND | MF_DISABLED | MF_GRAYED);
    } else {
        EnableMenuItem(hMenu, SC_CLOSE, MF_BYCOMMAND | MF_ENABLED);
    }
#endif
}

#ifdef _WIN32
// Switches the window to borderless fullscreen covering the entire primary monitor.
void ApplyFullscreen(webview::webview& w, HWND hwnd) {
    if (!hwnd) return;
    int screenWidth  = GetSystemMetrics(SM_CXSCREEN);
    int screenHeight = GetSystemMetrics(SM_CYSCREEN);
    // WS_VISIBLE must be kept — dropping it hides the native window while leaving
    // the WebView2 child surfaces visible, producing the staircase-white artifact.
    SetWindowLongPtr(hwnd, GWL_STYLE, WS_POPUP | WS_VISIBLE);
    // Clear any rounded-corner clipping region before covering the full screen.
    SetWindowRgn(hwnd, NULL, FALSE);
    SetWindowPos(hwnd, HWND_TOP, 0, 0, screenWidth, screenHeight,
                 SWP_FRAMECHANGED | SWP_NOOWNERZORDER);
    w.set_size(screenWidth, screenHeight, WEBVIEW_HINT_FIXED);
}
#endif

int main() {
    std::string cwd = GetCurrentWorkingDir();
    auto rootConfig = LoadConfig(cwd + "/properties.config");
    bool isFullscreen = (rootConfig.count("FULLSCREEN") && rootConfig.at("FULLSCREEN") == "true");
    int appPort = 2024;
    if (rootConfig.count("APP_PORT")) {
        try {
            int configuredPort = std::stoi(rootConfig.at("APP_PORT"));
            if (configuredPort < 1 || configuredPort > 65535) throw std::out_of_range("port");
            appPort = configuredPort;
        } catch (...) {
            std::cerr << "Invalid APP_PORT in properties.config; using 2024." << std::endl;
        }
    }
    std::string appPortString = std::to_string(appPort);
    
    // Check if terminal should be hidden
    bool hideTerminal = (rootConfig.count("SHOW_TERMINAL") && rootConfig["SHOW_TERMINAL"] == "false");
#ifdef _WIN32
    if (!hideTerminal) {
        // Allocate a new console window manually since we are running as a GUI application
        AllocConsole();
        FILE* fp;
        freopen_s(&fp, "CONOUT$", "w", stdout);
        freopen_s(&fp, "CONOUT$", "w", stderr);
        freopen_s(&fp, "CONIN$", "r", stdin);
    }
#endif

    // Determine the main page
    std::string mainPageFile = rootConfig.count("MAIN_PAGE") ? rootConfig["MAIN_PAGE"] : "ui/pages/index.html";
    std::string titlebarColor = rootConfig.count("TITLEBAR_COLOR") ? rootConfig["TITLEBAR_COLOR"] : "";

    // Replace backslashes with forward slashes for URI formatting
    std::string cwdUri = cwd;
    for(size_t i = 0; i < cwdUri.length(); ++i) {
        if(cwdUri[i] == '\\') cwdUri[i] = '/';
    }

    // 1. Initialize Python Interpreter
    Py_Initialize();
    // Build a forward-slash version of cwd safe to embed in a Python string literal
    std::string pyCwd = cwd;
    for (char& c : pyCwd) { if (c == '\\') c = '/'; }

    PyRun_SimpleString(("import sys\nsys.path.insert(0, '" + pyCwd + "')\nprint('Python backend initialized.')").c_str());

    // Start the configurable local file server to serve project files to the webview.
    // Uses the C++ computed project root so it works correctly from any working directory.
    // Bind synchronously so this process knows it owns the server it navigates
    // to. If another app already occupies APP_PORT, use an OS-assigned fallback
    // instead of navigating to an unrelated or stale process.
    {
        std::string serverScript =
            "import threading, http.server, socket, time\n"
            "class _ESDHandler(http.server.SimpleHTTPRequestHandler):\n"
            "    def __init__(self, *a, **kw):\n"
            "        super().__init__(*a, directory='" + pyCwd + "', **kw)\n"
            "    def end_headers(self):\n"
            "        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')\n"
            "        self.send_header('Pragma', 'no-cache')\n"
            "        self.send_header('Expires', '0')\n"
            "        super().end_headers()\n"
            "    def log_message(self, fmt, *a): pass\n"
            "_esd_requested_port = " + appPortString + "\n"
            "try:\n"
            "    _esd_server = http.server.ThreadingHTTPServer(('127.0.0.1', _esd_requested_port), _ESDHandler)\n"
            "except OSError:\n"
            "    _esd_server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _ESDHandler)\n"
            "_esd_server.daemon_threads = True\n"
            "_esd_actual_port = int(_esd_server.server_address[1])\n"
            "threading.Thread(target=_esd_server.serve_forever, daemon=True).start()\n"
            "# Block until this process's server is accepting connections (max ~5 s)\n"
            "for _ in range(50):\n"
            "    try:\n"
            "        _c = socket.create_connection(('127.0.0.1', _esd_actual_port), timeout=0.1)\n"
            "        _c.close(); break\n"
            "    except OSError:\n"
            "        time.sleep(0.1)\n";
        if (PyRun_SimpleString(serverScript.c_str()) != 0) {
            std::cerr << "Failed to start the ESDK application server." << std::endl;
        } else {
            PyObject* mainModule = PyImport_AddModule("__main__");
            PyObject* actualPort = mainModule
                ? PyObject_GetAttrString(mainModule, "_esd_actual_port")
                : nullptr;
            if (actualPort && PyLong_Check(actualPort)) {
                appPort = static_cast<int>(PyLong_AsLong(actualPort));
                appPortString = std::to_string(appPort);
            }
            Py_XDECREF(actualPort);
        }
    }

#ifdef _WIN32
    // Disable WebView2's persistent disk cache so every launch always loads fresh files.
    _putenv("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-allow-origins=* --disable-cache --disable-application-cache");
#endif

    // 2. Initialize the Webview
    bool devTools = true;
    if (rootConfig.count("DEVTOOLS") && rootConfig.at("DEVTOOLS") == "false") {
        devTools = false;
    }

    webview::webview w(devTools, nullptr);
    
    bool contextMenu = true;
    if (rootConfig.count("DEFAULT_CONTEXTUAL_MENU") && rootConfig.at("DEFAULT_CONTEXTUAL_MENU") == "false") {
        contextMenu = false;
    }
    
    if (!contextMenu) {
        w.init("window.addEventListener('contextmenu', e => e.preventDefault());");
    }

    HWND hwnd = nullptr;
#ifdef _WIN32
    hwnd = (HWND)w.window();
    ShowWindow(hwnd, SW_HIDE);
    InstallEsdkWindowProcedure(hwnd);
    
    // Load embedded icon and set it for the window taskbar/titlebar
    HICON hIcon = LoadIcon(GetModuleHandle(NULL), MAKEINTRESOURCE(101));
    if (hIcon) {
        SendMessage(hwnd, WM_SETICON, ICON_BIG, (LPARAM)hIcon);
        SendMessage(hwnd, WM_SETICON, ICON_SMALL, (LPARAM)hIcon);
    }
#endif

    bool dragBackground = false;
    bool windowWaitingToShow = true;

    // Every top-level document reports when its DOM is ready. The HWND stays
    // hidden until its final config and centered bounds have already been
    // applied, so users never see the library's default startup position.
    w.bind("__esdWindowReady", [&](std::string) -> std::string {
#ifdef _WIN32
        if (hwnd && windowWaitingToShow) {
            windowWaitingToShow = false;
            ShowPreparedWindow(hwnd);
        }
#endif
        return "";
    });
    w.init(
        "(function(){"
        "function ready(){setTimeout(function(){"
        "if(window.__esdWindowReady)window.__esdWindowReady('');"
        "},0);}"
        "if(document.readyState==='loading')"
        "window.addEventListener('DOMContentLoaded',ready,{once:true});"
        "else ready();"
        "})();");

    // Optional: Load Splash Screen Config
    std::string splashConfigPath = cwd + "/ui/splash/properties.config";
    std::ifstream splashFile(splashConfigPath);

    bool userWantsSplash = true;
    if (rootConfig.count("SPLASH_SCREEN") && rootConfig.at("SPLASH_SCREEN") == "false") {
        userWantsSplash = false;
    }

    bool useSplash = splashFile.good() && userWantsSplash;

    // Register the splash bridge before the first navigation. Registering it
    // after loading splash.html creates a race where the page can finish its
    // timer before WebView2 has exposed transitionToMain, leaving the splash
    // visible indefinitely.
    w.bind("transitionToMain", [&](std::string req) -> std::string {
#ifdef _WIN32
        if (hwnd) ShowWindow(hwnd, SW_HIDE);
#endif
        windowWaitingToShow = true;
        ApplyWindowProperties(w, hwnd, rootConfig, dragBackground);
#ifdef ESD_EMBED_HTML
        std::string mainHtml = GetPageHtml(mainPageFile);
        if (!mainHtml.empty()) { w.set_html(mainHtml); }
        else { w.navigate("http://127.0.0.1:" + appPortString + "/" + mainPageFile); }
#else
        w.navigate("http://127.0.0.1:" + appPortString + "/" + mainPageFile);
#endif
#ifdef _WIN32
        if (isFullscreen) ApplyFullscreen(w, hwnd);
#endif
        return "";
    });

    if (useSplash) {
        auto splashConfig = LoadConfig(splashConfigPath);
        ApplyWindowProperties(w, hwnd, splashConfig, dragBackground);
#ifdef ESD_EMBED_HTML
        std::string splashHtml = GetPageHtml("ui/splash/splash.html");
        if (!splashHtml.empty()) { w.set_html(splashHtml); }
        else { w.navigate("http://127.0.0.1:" + appPortString + "/ui/splash/splash.html?v=" + std::to_string(std::time(nullptr))); }
#else
        w.navigate("http://127.0.0.1:" + appPortString + "/ui/splash/splash.html?v=" + std::to_string(std::time(nullptr)));
#endif
    } else {
        ApplyWindowProperties(w, hwnd, rootConfig, dragBackground);
#ifdef ESD_EMBED_HTML
        std::string mainHtml = GetPageHtml(mainPageFile);
        if (!mainHtml.empty()) { w.set_html(mainHtml); }
        else { w.navigate("http://127.0.0.1:" + appPortString + "/" + mainPageFile + "?v=" + std::to_string(std::time(nullptr))); }
#else
        w.navigate("http://127.0.0.1:" + appPortString + "/" + mainPageFile + "?v=" + std::to_string(std::time(nullptr)));
#endif
#ifdef _WIN32
        if (isFullscreen) ApplyFullscreen(w, hwnd);
#endif
    }

    // 3. Create the JS -> C++ -> Python Bridge
    w.bind("setNativeTitlebarColor", [&](std::string req) -> std::string {
#ifdef _WIN32
        if (hwnd) {
            int r = 255, g = 255, b = 255;
            if (sscanf(req.c_str(), "[\"rgb(%d, %d, %d)\"]", &r, &g, &b) == 3 ||
                sscanf(req.c_str(), "[\"rgba(%d, %d, %d", &r, &g, &b) == 3) {
                COLORREF color = RGB(r, g, b);
                DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, &color, sizeof(color));
            }
        }
#endif
        return "";
    });

    if (titlebarColor == "transparent" && rootConfig.count("TITLEBAR") && rootConfig["TITLEBAR"] != "false") {
        w.init("window.addEventListener('DOMContentLoaded', () => {"
               "  setTimeout(() => {"
               "    let bg = window.getComputedStyle(document.body).backgroundColor;"
               "    if (window.setNativeTitlebarColor) window.setNativeTitlebarColor(bg);"
               "  }, 50);"
               "});");
    }

    w.bind("invokeBridge", [&](std::string req) -> std::string {
        // webview.h sends arguments as a JSON array e.g. ["{...}"]
        // We strip the outer array brackets to parse our raw JSON object string
        std::string payload = "";
        if (req.length() > 2 && req.front() == '[' && req.back() == ']') {
            // Remove the bounding [ ] array markers
            payload = req.substr(1, req.length() - 2);
            // Additional minor unescaping may be necessary depending on JSON payload
        } else {
            payload = req;
        }

        // Reacquire GIL for this callback — the main thread released it before w.run()
        PyGILState_STATE gstate = PyGILState_Ensure();
        std::string pyRes = CallPythonBackend(payload);
        PyGILState_Release(gstate);
        return pyRes;
    });

    // Window control bindings — usable from any custom titlebar or button
    w.bind("windowClose", [&](std::string req) -> std::string {
#ifdef _WIN32
        if (hwnd) PostMessage(hwnd, WM_CLOSE, 0, 0);
#endif
        return "";
    });

    w.bind("windowMinimize", [&](std::string req) -> std::string {
#ifdef _WIN32
        if (hwnd) ShowWindow(hwnd, SW_MINIMIZE);
#endif
        return "";
    });

    w.bind("windowMaximize", [&](std::string req) -> std::string {
#ifdef _WIN32
        if (hwnd) {
            ShowWindow(hwnd, IsZoomed(hwnd) ? SW_RESTORE : SW_MAXIMIZE);
        }
#endif
        return "";
    });

    // Native Drag window binding for UI
    w.bind("dragWindow", [&](std::string req) -> std::string {
        if (dragBackground) {
#ifdef _WIN32
            if (hwnd) {
                ReleaseCapture();
                SendMessage(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0);
            }
#endif
        }
        return "";
    });

    // Native External Link opener
    w.bind("openExternalLink", [&](std::string req) -> std::string {
        std::string url = req;
        // The payload arrives as a JSON array string: ["https://example.com"]
        if (url.length() >= 4 && url.front() == '[' && url.back() == ']') {
            url = url.substr(2, url.length() - 4);
        }
#ifdef _WIN32
        ShellExecuteA(0, "open", url.c_str(), 0, 0, SW_SHOW);
#endif
        return "";
    });

    // Inject Javascript to intercept external links
    w.init(R"(
        window.addEventListener('click', function(e) {
            let target = e.target.closest('a');
            if (target && target.href) {
                // Check if it's an external URL (http or https)
                if (target.href.startsWith('http://') || target.href.startsWith('https://')) {
                    e.preventDefault();
                    if (window.openExternalLink) {
                        window.openExternalLink(target.href);
                    }
                }
            }
        });
    )");

    // C++ binding: opens a modal HTML file as a native OS window on its own thread.
    // The parent's Promise is resolved when the modal calls closeModal(value).
    w.bind("_openModalNative", [&](std::string req) -> std::string {
        // Payload: JSON array ["modalName"] — strip wrapper
        std::string modalName = req;
        if (modalName.size() >= 4 && modalName.front() == '[' && modalName.back() == ']')
            modalName = modalName.substr(2, modalName.size() - 4);

        std::string modalPath = cwd + "/ui/modals/" + modalName + ".html";
        std::ifstream mf(modalPath);
        if (!mf.is_open()) {
            w.eval("window.__esd_resolveModal(null)");
            return "";
        }
        std::stringstream mss;
        mss << mf.rdbuf();
        std::string src = mss.str();

        // ── Parse <modal> attributes ────────────────────────────────────────
        std::string modalTag = ModalOpenTag(src, "modal");
        int mWidth  = 400, mHeight = 300;
        bool mBlur     = false;
        bool mCloseable = true;

        if (!modalTag.empty()) {
            try { mWidth  = std::stoi(ModalAttr(modalTag, "width",  "400")); } catch (...) {}
            try { mHeight = std::stoi(ModalAttr(modalTag, "height", "300")); } catch (...) {}
            mBlur      = (ModalAttr(modalTag, "blur",      "false") == "true");
            mCloseable = (ModalAttr(modalTag, "closeable", "true")  != "false");
        }

        // ── Parse <titlebar> section ────────────────────────────────────────
        // <titlebar value="false"> → custom HTML titlebar, no OS chrome
        // <titlebar value="true">  → use OS native titlebar
        // No <titlebar> element    → use OS native titlebar
        std::string titlebarOpenTag = ModalOpenTag(src, "titlebar");
        bool useOsChrome  = true;
        bool customTitlebar = false;
        int  titlebarH    = 38;
        std::string titlebarHtml;

        if (!titlebarOpenTag.empty()) {
            std::string tbVal = ModalAttr(titlebarOpenTag, "value", "true");
            if (tbVal == "false") {
                useOsChrome   = false;
                customTitlebar = true;
                try { titlebarH = std::stoi(ModalAttr(titlebarOpenTag, "height", "38")); } catch (...) {}
                titlebarHtml = ModalInner(src, "titlebar");
            }
        }

        // ── Parse <title><value>...</value></title> ──────────────────────────
        std::string titleInner  = ModalInner(src, "title");
        std::string windowTitle = ModalInner(titleInner, "value");
        if (windowTitle.empty()) windowTitle = modalName;

        // ── Parse <content> and <script> ────────────────────────────────────
        std::string contentHtml   = ModalInner(src, "content");
        std::string scriptContent = ModalInner(src, "script");

        // ── Generate a full standalone HTML page for the modal window ────────
        std::string tbH = std::to_string(titlebarH);
        std::string generatedHtml;

        if (customTitlebar) {
            generatedHtml =
                "<!DOCTYPE html><html><head><meta charset=\"UTF-8\"><style>"
                "* { margin:0; padding:0; box-sizing:border-box; }"
                "html,body { width:100%; height:100%; overflow:hidden; }"
                ".esd-tb-wrap { position:relative; height:" + tbH + "px; flex-shrink:0; overflow:hidden; }"
                ".esd-tb-drag { position:absolute; inset:0; z-index:0; cursor:move; }"
                ".esd-tb-content { position:relative; z-index:1; height:100%; pointer-events:none; }"
                ".esd-tb-content button,.esd-tb-content input,.esd-tb-content a,"
                ".esd-tb-content select,.esd-tb-content label { pointer-events:auto; }"
                ".esd-body { position:absolute; top:" + tbH + "px; left:0; right:0; bottom:0;"
                " overflow:auto; display:flex; align-items:center; justify-content:center; }"
                "</style></head>"
                "<body style=\"display:flex;flex-direction:column;\">"
                "<div class=\"esd-tb-wrap\">"
                "<div class=\"esd-tb-drag\" onmousedown=\"if(window.dragWindow)dragWindow()\"></div>"
                "<div class=\"esd-tb-content\">" + titlebarHtml + "</div>"
                "</div>"
                "<div class=\"esd-body\">" + contentHtml + "</div>"
                "<script>"
                "function closeModal(v){if(window._modalClose)window._modalClose(v!==undefined?v:null);}"
                + scriptContent +
                "</script>"
                "</body></html>";
        } else {
            generatedHtml =
                "<!DOCTYPE html><html><head><meta charset=\"UTF-8\"><style>"
                "* { margin:0; padding:0; box-sizing:border-box; }"
                "html,body { width:100%; height:100%; overflow:hidden; }"
                ".esd-body { width:100%; height:100%; display:flex;"
                " align-items:center; justify-content:center; }"
                "</style></head>"
                "<body>"
                "<div class=\"esd-body\">" + contentHtml + "</div>"
                "<script>"
                "function closeModal(v){if(window._modalClose)window._modalClose(v!==undefined?v:null);}"
                + scriptContent +
                "</script>"
                "</body></html>";
        }

        // ── Optional: blur/dim the parent window while modal is open ─────────
        if (mBlur) {
            w.eval(
                "(function(){"
                "var o=document.createElement('div');"
                "o.id='__esd_blur_overlay__';"
                "o.style.cssText='position:fixed;inset:0;z-index:9998;"
                "backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);"
                "background:rgba(0,0,0,0.35);pointer-events:none;';"
                "document.body.appendChild(o);"
                "})()");
        }

        // ── Read ui/modals/properties.config for corner radius ───────────────
        int mCornerRadius = 0;
        {
            auto modalCfg = LoadConfig(cwd + "/ui/modals/properties.config");
            if (modalCfg.count("CORNER_RADIUS")) {
                try { mCornerRadius = std::stoi(modalCfg.at("CORNER_RADIUS")); } catch (...) {}
            }
        }

        // ── Spawn the modal on its own thread with its own message loop ───────
        auto* params = new ModalThreadParams{
            generatedHtml, windowTitle,
            mWidth, mHeight, mCornerRadius,
            useOsChrome, mCloseable, devTools,
            &w
        };
        HANDLE hThread = CreateThread(nullptr, 0, ModalWindowThread, params, 0, nullptr);
        if (hThread) CloseHandle(hThread);

        return "";
    });

    // JS modal API — openModal(name) returns a Promise resolved by the modal's closeModal(value).
    w.init(R"ESDMODAL(
(function () {
    window.openModal = function (name) {
        return new Promise(function (resolve) {
            window.__esd_modalResolve = resolve;
            window._openModalNative(name);
        });
    };

    window.__esd_resolveModal = function (value) {
        var el = document.getElementById('__esd_blur_overlay__');
        if (el) el.remove();
        if (window.__esd_modalResolve) {
            window.__esd_modalResolve(value !== undefined ? value : null);
            window.__esd_modalResolve = null;
        }
    };
})();
)ESDMODAL");

    if (!hideTerminal) {
        std::cout << "Loading Interface..." << std::endl;
    }

    // 4. Run loop
    // Release the GIL so the Python HTTP server daemon thread can process requests.
    // Without this, the main thread holds the GIL through the entire event loop,
    // starving the server thread and producing a black screen.
    PyThreadState* _pyThreadState = PyEval_SaveThread();
    w.run();
    PyEval_RestoreThread(_pyThreadState);

    // 5. Cleanup
    Py_Finalize();
    return 0;
}
