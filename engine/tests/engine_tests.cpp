#include "georoute/engine.h"

#include <cassert>
#include <cmath>
#include <iostream>
#include <vector>

namespace {

void test_closest_pair() {
  const std::vector<GRPoint> points = {
      {0.0, 0.0}, {1.0, 0.1}, {2.0, 0.0}, {3.0, 0.1}};

  GRClosestResult brute{};
  GRClosestResult divide{};
  assert(gr_closest_pair(points.data(), static_cast<int>(points.size()),
                         GR_CLOSEST_BRUTE_FORCE, &brute) == GR_OK);
  assert(gr_closest_pair(points.data(), static_cast<int>(points.size()),
                         GR_CLOSEST_DIVIDE_CONQUER, &divide) == GR_OK);

  assert(std::abs(brute.distance - divide.distance) < 1e-9);
  assert(brute.index_a == divide.index_a && brute.index_b == divide.index_b);

  std::vector<GRPoint> larger;
  for (int i = 0; i < 32; ++i) {
    const double angle = i * 0.7;
    larger.push_back({std::cos(angle) * 100.0, std::sin(angle) * 100.0});
  }
  GRClosestResult large_brute{};
  GRClosestResult large_divide{};
  assert(gr_closest_pair(larger.data(), static_cast<int>(larger.size()),
                         GR_CLOSEST_BRUTE_FORCE, &large_brute) == GR_OK);
  assert(gr_closest_pair(larger.data(), static_cast<int>(larger.size()),
                         GR_CLOSEST_DIVIDE_CONQUER, &large_divide) == GR_OK);
  assert(std::abs(large_brute.distance - large_divide.distance) < 1e-9);
  assert(large_divide.distance_evaluations < large_brute.distance_evaluations);
}

void test_closest_pair_duplicates() {
  const std::vector<GRPoint> points = {
      {0.0, 0.0}, {1.0, 1.0}, {2.0, 2.0}, {2.0, 2.0}, {5.0, 5.0}};

  GRClosestResult brute{};
  GRClosestResult divide{};
  assert(gr_closest_pair(points.data(), static_cast<int>(points.size()),
                         GR_CLOSEST_BRUTE_FORCE, &brute) == GR_OK);
  assert(gr_closest_pair(points.data(), static_cast<int>(points.size()),
                         GR_CLOSEST_DIVIDE_CONQUER, &divide) == GR_OK);
  assert(brute.distance == 0.0 && divide.distance == 0.0);
}

void test_tsp_exact() {
  const int n = 4;
  const std::vector<double> matrix = {
      0, 1, 2, 1,
      1, 0, 1, 2,
      2, 1, 0, 1,
      1, 2, 1, 0};

  GRTourResult result{};
  assert(gr_tsp(matrix.data(), n, 0, GR_TSP_EXACT, &result) == GR_OK);
  assert(std::abs(result.cost - 4.0) < 1e-9);
  assert(result.route_length == n);
  assert(result.route[0] == 0);
  gr_free_tour(&result);
}

void test_tsp_heuristics() {
  const int n = 5;
  const std::vector<double> matrix = {
      0,  2,  9,  4,  7,
      2,  0,  6,  3,  8,
      9,  6,  0,  5,  1,
      4,  3,  5,  0,  9,
      7,  8,  1,  9,  0};

  GRTourResult nearest{};
  GRTourResult two_opt{};
  assert(gr_tsp(matrix.data(), n, 0, GR_TSP_NEAREST_NEIGHBOR, &nearest) == GR_OK);
  assert(gr_tsp(matrix.data(), n, 0, GR_TSP_TWO_OPT, &two_opt) == GR_OK);

  assert(std::abs(nearest.cost - 18.0) < 1e-9);
  assert(two_opt.cost <= nearest.cost + 1e-9);
  assert(two_opt.route[0] == 0);
  assert(two_opt.improvement_passes > 0);

  gr_free_tour(&nearest);
  gr_free_tour(&two_opt);
}

void test_limits() {
  const std::vector<GRPoint> single{{0.0, 0.0}};
  GRClosestResult closest{};
  assert(gr_closest_pair(single.data(), 1, 0, &closest) == GR_INVALID_INPUT);

  const std::vector<double> big_matrix(12 * 12, 1.0);
  GRTourResult tour{};
  assert(gr_tsp(big_matrix.data(), 12, 0, GR_TSP_EXACT, &tour) ==
         GR_LIMIT_EXCEEDED);
}

}  // namespace

int main() {
  test_closest_pair();
  test_closest_pair_duplicates();
  test_tsp_exact();
  test_tsp_heuristics();
  test_limits();
  std::cout << "All C++ engine tests passed.\n";
  return 0;
}
