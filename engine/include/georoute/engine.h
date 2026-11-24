#ifndef GEOROUTE_ENGINE_H
#define GEOROUTE_ENGINE_H

#include <cstddef>
#include <cstdint>

#if defined(_WIN32)
  #define GR_API __declspec(dllexport)
#elif defined(__GNUC__)
  #define GR_API __attribute__((visibility("default")))
#else
  #define GR_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

enum GRStatus {
  GR_OK = 0,
  GR_INVALID_INPUT = 1,
  GR_LIMIT_EXCEEDED = 2,
  GR_INTERNAL_ERROR = 3
};

enum GRClosestAlgorithm {
  GR_CLOSEST_BRUTE_FORCE = 0,
  GR_CLOSEST_DIVIDE_CONQUER = 1
};

enum GRTourAlgorithm {
  GR_TSP_EXACT = 0,
  GR_TSP_NEAREST_NEIGHBOR = 1,
  GR_TSP_TWO_OPT = 2
};

struct GRPoint {
  double x;
  double y;
};

struct GRClosestResult {
  int index_a;
  int index_b;
  double distance;
  unsigned long long distance_evaluations;
  unsigned long long comparisons;
  double elapsed_ms;
  int status;
};

struct GRTourResult {
  int* route;
  int route_length;
  double cost;
  unsigned long long distance_evaluations;
  unsigned long long comparisons;
  int improvement_passes;
  double elapsed_ms;
  int status;
};

/* Returns GR_OK on success and fills result. */
GR_API int gr_closest_pair(const GRPoint* points,
                          int count,
                          int algorithm,
                          GRClosestResult* result);

/* tour[0] is always the depot. The return to the depot is included in cost
   but is not repeated in the route array. */
GR_API int gr_tsp(const double* matrix,
                  int count,
                  int depot,
                  int algorithm,
                  GRTourResult* result);

/* Must be called for every successful gr_tsp result to release route[]. */
GR_API void gr_free_tour(GRTourResult* result);

GR_API const char* gr_version(void);

#ifdef __cplusplus
}
#endif

#endif
