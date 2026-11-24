#include "georoute/engine.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <numeric>
#include <vector>

namespace {

constexpr int kMaxExactLocations = 11;
constexpr int kMaxTwoOptPasses = 100;
constexpr double kImprovementEpsilon = 1e-9;

using Clock = std::chrono::high_resolution_clock;

struct Work {
  unsigned long long distance_evaluations = 0;
  unsigned long long comparisons = 0;
};

inline double lookup(const double* matrix,
                     int count,
                     int from,
                     int to,
                     Work& work) {
  ++work.distance_evaluations;
  return matrix[static_cast<std::size_t>(from) * count + to];
}

double evaluate_cost(const double* matrix,
                     int count,
                     const std::vector<int>& route,
                     Work& work) {
  double cost = 0.0;
  for (int i = 0; i < count; ++i) {
    const int from = route[static_cast<std::size_t>(i)];
    const int to = route[static_cast<std::size_t>((i + 1) % count)];
    cost += lookup(matrix, count, from, to, work);
  }
  return cost;
}

bool valid_matrix(const double* matrix, int count) {
  if (matrix == nullptr || count < 2) return false;
  for (std::size_t i = 0; i < static_cast<std::size_t>(count) * count; ++i) {
    if (!std::isfinite(matrix[i]) || matrix[i] < 0.0) return false;
  }
  return true;
}

bool is_symmetric(const double* matrix, int count) {
  for (int i = 0; i < count; ++i) {
    for (int j = i + 1; j < count; ++j) {
      const double forward = matrix[static_cast<std::size_t>(i) * count + j];
      const double backward = matrix[static_cast<std::size_t>(j) * count + i];
      const double tolerance =
          1e-9 * std::max(1.0, std::max(std::abs(forward), std::abs(backward)));
      if (std::abs(forward - backward) > tolerance) return false;
    }
  }
  return true;
}

std::vector<int> nearest_neighbour(const double* matrix,
                                   int count,
                                   int depot,
                                   Work& work) {
  std::vector<bool> visited(static_cast<std::size_t>(count), false);
  std::vector<int> route;
  route.reserve(static_cast<std::size_t>(count));
  route.push_back(depot);
  visited[static_cast<std::size_t>(depot)] = true;

  int current = depot;
  for (int step = 1; step < count; ++step) {
    int best = -1;
    double best_cost = std::numeric_limits<double>::infinity();
    for (int candidate = 0; candidate < count; ++candidate) {
      if (visited[static_cast<std::size_t>(candidate)]) continue;
      const double cost = lookup(matrix, count, current, candidate, work);
      ++work.comparisons;
      if (cost < best_cost) {
        best_cost = cost;
        best = candidate;
      }
    }
    visited[static_cast<std::size_t>(best)] = true;
    route.push_back(best);
    current = best;
  }
  return route;
}

std::vector<int> solve_exact(const double* matrix,
                             int count,
                             int depot,
                             Work& work) {
  std::vector<int> permutation;
  permutation.reserve(static_cast<std::size_t>(count - 1));
  for (int i = 0; i < count; ++i) {
    if (i != depot) permutation.push_back(i);
  }

  std::sort(permutation.begin(), permutation.end());
  std::vector<int> best(permutation);
  double best_cost = std::numeric_limits<double>::infinity();

  do {
    std::vector<int> candidate;
    candidate.reserve(static_cast<std::size_t>(count));
    candidate.push_back(depot);
    candidate.insert(candidate.end(), permutation.begin(), permutation.end());

    const double cost = evaluate_cost(matrix, count, candidate, work);
    ++work.comparisons;
    if (cost < best_cost) {
      best_cost = cost;
      best = candidate;
    }
  } while (std::next_permutation(permutation.begin(), permutation.end()));

  return best;
}

std::vector<int> improve_two_opt(const double* matrix,
                                 int count,
                                 std::vector<int> route,
                                 bool symmetric,
                                 Work& work,
                                 int& passes) {
  passes = 0;

  for (int pass = 0; pass < kMaxTwoOptPasses; ++pass) {
    bool improved = false;
    ++passes;
    for (int i = 0; i < count - 1; ++i) {
      for (int k = i + 1; k < count; ++k) {
        const int a = route[static_cast<std::size_t>(i)];
        const int b = route[static_cast<std::size_t>(i + 1)];
        const int c = route[static_cast<std::size_t>(k)];
        const int d = route[static_cast<std::size_t>((k + 1) % count)];

        double old_edges = lookup(matrix, count, a, b, work) +
                           lookup(matrix, count, c, d, work);
        double new_edges = lookup(matrix, count, a, c, work) +
                           lookup(matrix, count, b, d, work);
        if (!symmetric) {
          // Reversing a segment also reverses its internal directed edges.
          for (int p = i + 1; p < k; ++p) {
            old_edges += lookup(matrix, count, route[static_cast<std::size_t>(p)],
                                route[static_cast<std::size_t>(p + 1)], work);
            new_edges += lookup(matrix, count, route[static_cast<std::size_t>(p + 1)],
                                route[static_cast<std::size_t>(p)], work);
          }
        }
        const double delta = new_edges - old_edges;

        ++work.comparisons;
        if (delta < -kImprovementEpsilon) {
          std::reverse(route.begin() + i + 1, route.begin() + k + 1);
          improved = true;
        }
      }
    }
    if (!improved) break;
  }
  return route;
}

void fill_result(GRTourResult* result,
                 const std::vector<int>& route,
                 double cost,
                 const Work& work,
                 int passes,
                 double elapsed_ms) {
  result->route = new int[route.size()];
  std::copy(route.begin(), route.end(), result->route);
  result->route_length = static_cast<int>(route.size());
  result->cost = cost;
  result->distance_evaluations = work.distance_evaluations;
  result->comparisons = work.comparisons;
  result->improvement_passes = passes;
  result->elapsed_ms = elapsed_ms;
  result->status = GR_OK;
}

}  // namespace

extern "C" int gr_tsp(const double* matrix,
                      int count,
                      int depot,
                      int algorithm,
                      GRTourResult* result) {
  if (result == nullptr) return GR_INVALID_INPUT;
  *result = GRTourResult{nullptr, 0, 0.0, 0, 0, 0, 0.0, GR_INVALID_INPUT};

  if (!valid_matrix(matrix, count) || depot < 0 || depot >= count ||
      (algorithm != GR_TSP_EXACT &&
       algorithm != GR_TSP_NEAREST_NEIGHBOR &&
       algorithm != GR_TSP_TWO_OPT)) {
    return GR_INVALID_INPUT;
  }
  if (algorithm == GR_TSP_EXACT && count > kMaxExactLocations) {
    return GR_LIMIT_EXCEEDED;
  }

  const auto start = Clock::now();
  Work work;
  int passes = 0;
  double cost = 0.0;
  std::vector<int> route;

  try {
    if (algorithm == GR_TSP_EXACT) {
      route = solve_exact(matrix, count, depot, work);
      cost = evaluate_cost(matrix, count, route, work);
    } else {
      route = nearest_neighbour(matrix, count, depot, work);
      if (algorithm == GR_TSP_TWO_OPT) {
        route = improve_two_opt(
            matrix, count, route, is_symmetric(matrix, count), work, passes);
      }
      cost = evaluate_cost(matrix, count, route, work);
    }
  } catch (...) {
    return GR_INTERNAL_ERROR;
  }

  const auto end = Clock::now();
  const double elapsed_ms =
      std::chrono::duration<double, std::milli>(end - start).count();
  fill_result(result, route, cost, work, passes, elapsed_ms);
  return GR_OK;
}

extern "C" void gr_free_tour(GRTourResult* result) {
  if (result == nullptr) return;
  delete[] result->route;
  result->route = nullptr;
  result->route_length = 0;
}

extern "C" const char* gr_version(void) {
  return "1.0.0";
}
