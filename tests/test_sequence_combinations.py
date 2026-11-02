"""Lazy combination order equals the frozen full-product order, without building the product."""
import itertools
import random
import tracemalloc

import pytest

from sign_robot.sequence_assembly import combinations


def reference(pools, pair_ids, limit):
    """The original materializing definition, kept as the test oracle."""
    sizes = [len(pools[pair_id]) for pair_id in pair_ids]
    return sorted(itertools.product(*(range(size) for size in sizes)), key=lambda r: (sum(r), r))[:limit]


def pools_of(sizes):
    return {f"P{i}": [None] * size for i, size in enumerate(sizes)}


@pytest.mark.parametrize("sizes", [(1,), (5,), (3, 3), (1, 7), (7, 1), (4, 2, 3), (2, 2, 2, 2), (13, 7, 18, 8), (3, 1, 4, 1, 5)])
@pytest.mark.parametrize("limit", [0, 1, 2, 7, 64, 10_000])
def test_first_items_equal_the_sorted_product(sizes, limit):
    pools = pools_of(sizes)
    ids = list(pools)
    assert combinations(pools, ids, limit) == reference(pools, ids, limit)


def test_repeated_edges_and_random_shapes_match_reference():
    generator = random.Random(5412)
    for _ in range(300):
        names = [f"P{i}" for i in range(generator.randint(1, 4))]
        pools = {name: [None] * generator.randint(1, 9) for name in names}
        # Positional sizes: a repeated pair id contributes one independent rank per edge.
        ids = [generator.choice(names) for _ in range(generator.randint(1, 5))]
        limit = generator.choice([1, 3, 64, 500])
        assert combinations(pools, ids, limit) == reference(pools, ids, limit)


def test_empty_pool_and_limit_boundaries():
    assert combinations(pools_of((3, 0, 2)), ["P0", "P1", "P2"], 64) == []
    assert combinations(pools_of((3, 2)), ["P0", "P1"], 0) == []
    assert len(combinations(pools_of((3, 2)), ["P0", "P1"], 6)) == 6
    assert len(combinations(pools_of((3, 2)), ["P0", "P1"], 7)) == 6
    assert combinations(pools_of((2, 2)), ["P0", "P1"], 3) == [(0, 0), (0, 1), (1, 0)]


def test_large_pools_build_only_the_requested_prefix():
    sizes = (10**6,) * 5  # The full product would have 1e30 tuples.
    pools = {f"P{i}": range(size) for i, size in enumerate(sizes)}
    tracemalloc.start()
    result = combinations(pools, list(pools), 64)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(result) == 64 and peak < 2_000_000
    assert result[:6] == [(0, 0, 0, 0, 0), (0, 0, 0, 0, 1), (0, 0, 0, 1, 0), (0, 0, 1, 0, 0), (0, 1, 0, 0, 0), (1, 0, 0, 0, 0)]
    assert [sum(r) for r in result] == sorted(sum(r) for r in result)
    assert len(set(result)) == 64
