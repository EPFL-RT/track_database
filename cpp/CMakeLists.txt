# Header-only C++ library to load the tracks of an external tracks folder.
# Usage from another CMake project:
#
#   include(FetchContent)
#   FetchContent_Declare(track_database
#       GIT_REPOSITORY https://github.com/EPFL-RT/track_database.git
#       GIT_TAG vX.X.X
#       SOURCE_SUBDIR cpp)
#   FetchContent_MakeAvailable(track_database)
#   target_link_libraries(my_target PRIVATE track_database::track_database)
cmake_minimum_required(VERSION 3.14)
project(track_database LANGUAGES CXX)

option(TRACK_DATABASE_BUILD_TESTS "Build the track_database C++ tests" OFF)

find_package(Eigen3 REQUIRED NO_MODULE)

add_library(track_database INTERFACE)
add_library(track_database::track_database ALIAS track_database)
target_include_directories(track_database INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_compile_features(track_database INTERFACE cxx_std_17)
target_link_libraries(track_database INTERFACE Eigen3::Eigen)

# Exposed so that consumers exporting their own targets (e.g. ament packages) can
# install the headers next to theirs instead of exporting this target.
set(TRACK_DATABASE_INCLUDE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/include CACHE INTERNAL "")

if(TRACK_DATABASE_BUILD_TESTS)
    enable_testing()
    add_executable(test_tracks test/test_tracks.cpp)
    target_link_libraries(test_tracks PRIVATE track_database::track_database)
    add_test(NAME test_tracks COMMAND test_tracks)
endif()
