cmake_minimum_required(VERSION 3.10)
project(http_server)

# 设置 C++ 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 查找 OpenSSL 和 CURL
find_package(OpenSSL REQUIRED)
find_package(CURL REQUIRED)

# 添加头文件路径
include_directories(
    ${PROJECT_SOURCE_DIR}
    ${PROJECT_SOURCE_DIR}/include
    ${PROJECT_SOURCE_DIR}/HttpServer/include
    ${PROJECT_SOURCE_DIR}/AIApps/ChatServer/include
    /usr/include/mysql-cppconn-8
    /usr/include/mysql
    ${OPENSSL_INCLUDE_DIR}
    ${CURL_INCLUDE_DIRS}
    /usr/include/opencv4          # OpenCV 头文件路径
    /usr/local/include            # SimpleAmqpClient & ONNX Runtime
)

# 查找必要的库
find_library(MYSQLCPPCONN_LIBRARY
    NAMES mysqlcppconn mysqlcppconn8
    PATHS /usr/lib /usr/lib64 /usr/local/lib
)

find_library(ONNXRUNTIME_LIBRARY
    NAMES onnxruntime
    PATHS /usr/lib /usr/lib64 /usr/local/lib
)

# 添加源文件
file(GLOB_RECURSE HTTP_SERVER_SRC
    "${PROJECT_SOURCE_DIR}/HttpServer/src/*.cpp"
)

file(GLOB_RECURSE GOMOKU_SERVER_SRC
    "${PROJECT_SOURCE_DIR}/AIApps/ChatServer/src/*.cpp"
)

# 主程序文件
set(MAIN_SRC "${PROJECT_SOURCE_DIR}/AIApps/ChatServer/src/main.cpp")

# 添加可执行文件
add_executable(http_server
    ${MAIN_SRC}
    ${HTTP_SERVER_SRC}
    ${GOMOKU_SERVER_SRC}
)

# 链接库
target_link_libraries(http_server
    pthread
    muduo_net
    muduo_base
    mysqlcppconn
    mysqlclient
    ssl
    crypto
    ${CURL_LIBRARIES}
    ${OPENCV4_LIBRARIES}
    /usr/lib/x86_64-linux-gnu/libopencv_core.so
    /usr/lib/x86_64-linux-gnu/libopencv_imgproc.so
    /usr/lib/x86_64-linux-gnu/libopencv_highgui.so
    /usr/lib/x86_64-linux-gnu/libopencv_imgcodecs.so
    /usr/lib/x86_64-linux-gnu/libopencv_videoio.so
    /usr/lib/x86_64-linux-gnu/libopencv_dnn.so

    ${ONNXRUNTIME_LIBRARY}        # 自动查找的 ONNX Runtime 库

    SimpleAmqpClient
    rabbitmq
)

# 如果库不在默认路径，添加链接目录
link_directories(/usr/local/lib)

# 打印调试信息
message(STATUS "Include directories:")
get_property(dirs DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR} PROPERTY INCLUDE_DIRECTORIES)
foreach(dir ${dirs})
    message(STATUS "  ${dir}")
endforeach()

message(STATUS "ONNX Runtime library: ${ONNXRUNTIME_LIBRARY}")
message(STATUS "Main source file: ${MAIN_SRC}")
message(STATUS "HTTP Server sources: ${HTTP_SERVER_SRC}")
message(STATUS "Gomoku Server sources: ${GOMOKU_SERVER_SRC}")

# 引入 GTest 依赖
find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIRS})

# 把我们要测试的那个文件加进来创建一个新的可执行目标
add_executable(test_runner tests_gtest/test_aihelper.cpp)

# 需要把我们要测的类对应的源码全都绑给这个 test_runner
# 注意下面这一坨是把所有依赖打包给它
target_sources(test_runner PRIVATE
    AIApps/ChatServer/src/AIUtil/AIHelper.cpp
    AIApps/ChatServer/src/AIUtil/AIConfig.cpp
    AIApps/ChatServer/src/AIUtil/AIFactory.cpp
    AIApps/ChatServer/src/AIUtil/AIToolRegistry.cpp
    AIApps/ChatServer/src/AIUtil/MQManager.cpp
    # 这里如果编译还报错说缺哪个cpp，就在这里继续补那个cpp的路径
)

# 链接 GTest 的库和项目中用到的关键库
target_link_libraries(test_runner
    ${GTEST_LIBRARIES}
    pthread
    curl
    muduo_net
    muduo_base
    mysqlcppconn
    mysqlclient
    ssl
    crypto
    SimpleAmqpClient
    rabbitmq
)
