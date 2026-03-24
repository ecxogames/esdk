cmake_minimum_required(VERSION 3.14)
project(ESDEngine)

# Fix CMake CMP0135 Warning for FetchContent URL downloads
if(POLICY CMP0135)
    cmake_policy(SET CMP0135 NEW)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Search for Python3 (required for backend)
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# The single webview.h needs to be in engine/ folder
set(CMAKE_INCLUDE_CURRENT_DIR ON)

# Export compile commands for VS Code IntelliSense
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Provide WebView2 implicitly for Windows
if(WIN32)
    include(FetchContent)
    FetchContent_Declare(
        webview2
        URL "https://www.nuget.org/api/v2/package/Microsoft.Web.WebView2"
    )
    FetchContent_MakeAvailable(webview2)
endif()

add_executable(ESDEngine engine/main.cpp)

# Link C++ and Python (and dwmapi for Windows modern titlebars)
if(WIN32)
    target_link_libraries(ESDEngine PRIVATE Python3::Python dwmapi)
else()
    target_link_libraries(ESDEngine PRIVATE Python3::Python)
endif()
target_include_directories(ESDEngine PRIVATE ${Python3_INCLUDE_DIRS})

# Link C++ Webview requirements dynamically based on OS
if(WIN32)
    # Give target visibility to the extracted webview2 package directory
    target_include_directories(ESDEngine PRIVATE ${webview2_SOURCE_DIR}/build/native/include)
    
    # We dynamically load Webview2 on Windows via COM, but core Windows libs are still needed
    target_link_libraries(ESDEngine PRIVATE setupapi pathcch)
elseif(APPLE)
    target_link_libraries(ESDEngine PRIVATE "-framework WebKit" "-framework Cocoa")
elseif(UNIX)
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(WEBKIT2GTK REQUIRED webkit2gtk-4.0)
    target_link_libraries(ESDEngine PRIVATE ${WEBKIT2GTK_LIBRARIES})
    target_include_directories(ESDEngine PRIVATE ${WEBKIT2GTK_INCLUDE_DIRS})
endif()
