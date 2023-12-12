cmake_minimum_required(VERSION 3.0.2)
project(rosout)

if(NOT WIN32)
  set_directory_properties(PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra")
endif()

find_package(catkin REQUIRED COMPONENTS roscpp rosgraph_msgs)

# TODO(lucasw) make roscpp export these?
find_package(zenohc REQUIRED)
find_package(zenohcxx REQUIRED)

catkin_package()

include_directories(${catkin_INCLUDE_DIRS})

add_executable(rosout rosout.cpp)
target_link_libraries(rosout ${catkin_LIBRARIES} zenohcxx::zenohc::lib)

install(TARGETS rosout
  RUNTIME DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
