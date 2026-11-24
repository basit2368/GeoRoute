#include "georoute/engine.h"

#include <algorithm>
#include <cmath>
#include <chrono>
#include <limits>
#include <vector>

namespace {

struct Work {
  unsigned long long distance_evaluations = 0;
  unsigned long long comparisons = 0;
};

struct BestPair {
  int a = -1;
  int b = -1;
  double distance = std::numeric_limits<double>::infinity();
};

using Clock = std::chrono::high_resolution_clock;

inline double squared_distance(const GRPoint& a, const GRPoint& b) {
  const double dx = a.x - b.x;
  const double dy = a.y - b.y;
  return dx * dx + dy * dy;
}

inline bool y_order(const std::vector<GRPoint>& points, int a, int b) {
  if (points[a].y != points[b].y) return points[a].y < points[b].y;
  return points[a].x < points[b].x;
}

void evaluate_pair(const std::vector<GRPoint>& points,
                   int a,
                   int b,
                   BestPair& best,
                   Work& work) {
  ++work.distance_evaluations;
  const double distance = std::sqrt(squared_distance(points[a], points[b]));
  ++work.comparisons;
  if (distance < best.distance) {
    best.distance = distance;
    best.a = a;
    best.b = b;
  }
}

void brute_force_range(const std::vector<GRPoint>& points,
                       const std::vector<int>& order_x,
                       std::vector<int>& order_y,
                       int left,
                       int right,
                       BestPair& best,
                       Work& work) {
  std::sort(order_y.begin() + left,
            order_y.begin() + right,
            [&points](int a, int b) { return y_order(points, a, b); });

  for (int i = left; i < right; ++i) {
    for (int j = i + 1; j < right; ++j) {
      evaluate_pair(points, order_x[i], order_x[j], best, work);
    }
  }
}

void divide_conquer(const std::vector<GRPoint>& points,
                    std::vector<int>& order_x,
                    std::vector<int>& order_y,
                    int left,
                    int right,
                    BestPair& best,
                    Work& work) {
  const int size = right - left;
  if (size <= 8) {
    brute_force_range(points, order_x, order_y, left, right, best, work);
    return;
  }

  const int middle = left + size / 2;
  const double middle_x = points[order_x[middle]].x;

  divide_conquer(points, order_x, order_y, left, middle, best, work);
  divide_conquer(points, order_x, order_y, middle, right, best, work);

  // Merge the already y-sorted halves. This preserves the recurrence:
  // O(n log n) sorting at the top plus O(n) merging/checking per level.
  std::vector<int> merged(size);
  std::merge(order_y.begin() + left,
             order_y.begin() + middle,
             order_y.begin() + middle,
             order_y.begin() + right,
             merged.begin(),
             [&points](int a, int b) { return y_order(points, a, b); });
  std::copy(merged.begin(), merged.end(), order_y.begin() + left);

  std::vector<int> strip;
  strip.reserve(static_cast<std::size_t>(size));
  for (int i = left; i < right; ++i) {
    const int index = order_y[i];
    // <= keeps exact duplicate points in the strip when the current best is 0.
    ++work.comparisons;
    if (std::abs(points[index].x - middle_x) <= best.distance) {
      strip.push_back(index);
    }
  }

  for (std::size_t i = 0; i < strip.size(); ++i) {
    for (std::size_t j = i + 1; j < strip.size(); ++j) {
      const double dy = points[strip[j]].y - points[strip[i]].y;
      ++work.comparisons;
      if (dy > best.distance) break;
      evaluate_pair(points, strip[i], strip[j], best, work);
    }
  }
}

}  // namespace

extern "C" int gr_closest_pair(const GRPoint* points,
                               int count,
                               int algorithm,
                               GRClosestResult* result) {
  if (result == nullptr) return GR_INVALID_INPUT;
  *result = GRClosestResult{-1, -1, 0.0, 0, 0, 0.0, GR_INVALID_INPUT};

  if (points == nullptr || count < 2 ||
      (algorithm != GR_CLOSEST_BRUTE_FORCE &&
       algorithm != GR_CLOSEST_DIVIDE_CONQUER)) {
    return GR_INVALID_INPUT;
  }

  for (int i = 0; i < count; ++i) {
    if (!std::isfinite(points[i].x) || !std::isfinite(points[i].y)) {
      return GR_INVALID_INPUT;
    }
  }

  const auto start = Clock::now();
  Work work;
  BestPair best;

  try {
    std::vector<GRPoint> point_list(points, points + count);
    std::vector<int> order_x(static_cast<std::size_t>(count));
    for (int i = 0; i < count; ++i) order_x[static_cast<std::size_t>(i)] = i;

    std::sort(order_x.begin(), order_x.end(), [&point_list](int a, int b) {
      if (point_list[a].x != point_list[b].x) return point_list[a].x < point_list[b].x;
      return point_list[a].y < point_list[b].y;
    });

    if (algorithm == GR_CLOSEST_BRUTE_FORCE) {
      for (int i = 0; i + 1 < count; ++i) {
        for (int j = i + 1; j < count; ++j) {
          evaluate_pair(point_list, order_x[static_cast<std::size_t>(i)],
                        order_x[static_cast<std::size_t>(j)], best, work);
        }
      }
    } else {
      std::vector<int> order_y(order_x);
      divide_conquer(point_list, order_x, order_y, 0, count, best, work);
    }
  } catch (...) {
    return GR_INTERNAL_ERROR;
  }

  const auto end = Clock::now();
  result->index_a = best.a;
  result->index_b = best.b;
  result->distance = best.distance;
  result->distance_evaluations = work.distance_evaluations;
  result->comparisons = work.comparisons;
  result->elapsed_ms =
      std::chrono::duration<double, std::milli>(end - start).count();
  result->status = GR_OK;
  return GR_OK;
}
