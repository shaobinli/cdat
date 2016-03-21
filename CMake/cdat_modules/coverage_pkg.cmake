set(COVERAGE_MAJOR_SRC 4)
set(COVERAGE_MINOR_SRC 0)
set(COVERAGE_PATCH_SRC 3)

set(COVERAGE_VERSION ${COVERAGE_MAJOR_SRC}.${COVERAGE_MINOR_SRC}.${COVERAGE_PATCH_SRC})
set(COVERAGE_GZ coverage-${COVERAGE_VERSION}.tar.gz)
set(COVERAGE_SOURCE ${LLNL_URL}/${COVERAGE_GZ})
set(COVERAGE_MD5 c7d3db1882484022c81bf619be7b6365)

add_cdat_package_dependent(COVERAGE "" "" ON "CDAT_MEASURE_COVERAGE" OFF)