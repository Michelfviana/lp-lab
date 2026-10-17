import random
import sys
import unittest
from fractions import Fraction
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from solver import solve


def problem(c, rows, sense="max"):
    return {
        "objective": c,
        "sense": sense,
        "constraints": [
            {"coefficients": a, "operator": op, "rhs": b} for a, op, b in rows
        ],
    }


class SolverTests(unittest.TestCase):
    def test_document_example(self):
        r = solve(
            problem([3, 5], [([1, 0], "<=", 4), ([0, 2], "<=", 12), ([3, 2], "<=", 18)])
        )
        self.assertEqual(
            (r["status"], r["variables"], r["objective_value"]),
            ("optimal", ["2", "6"], "36"),
        )
        self.assertEqual([x["slack"] for x in r["constraints"]], ["2", "0", "0"])

    def test_minimization_two_phases(self):
        r = solve(problem([2, 3], [([1, 1], ">=", 4), ([1, 3], ">=", 6)], "min"))
        self.assertEqual(r["variables"], ["3", "1"])
        self.assertEqual(r["objective_value"], "9")
        self.assertEqual({s["phase"] for s in r["steps"]}, {1, 2})

    def test_infeasible(self):
        r = solve(problem([1, 1], [([1, 1], "<=", 2), ([1, 1], ">=", 5)]))
        self.assertEqual(r["status"], "infeasible")
        self.assertIsNone(r["variables"])

    def test_unbounded_certificate(self):
        p = problem([1, 1], [([1, -1], "<=", 2)])
        r = solve(p)
        self.assertEqual(r["status"], "unbounded")
        x = list(map(Fraction, r["variables"]))
        d = list(map(Fraction, r["ray"]))
        self.assertGreater(sum(d), 0)
        self.assertLessEqual(x[0] + 100 * d[0] - x[1] - 100 * d[1], 2)
        self.assertTrue(all(v >= 0 for v in d))

    def test_negative_rhs(self):
        r = solve(problem([1, 0], [([-1, 0], "<=", -2), ([1, 0], "<=", 5)]))
        self.assertEqual(r["objective_value"], "5")
        self.assertTrue(r["notes"])

    def test_redundant_equalities(self):
        r = solve(
            problem([1, 2], [([1, 1], "=", 3), ([2, 2], "=", 6), ([0, 0], "=", 0)])
        )
        self.assertEqual(r["objective_value"], "6")
        self.assertEqual(r["variables"], ["0", "3"])
        self.assertFalse(any(c.startswith("a") for c in r["steps"][-1]["columns"]))

    def test_impossible_zero_row(self):
        self.assertEqual(
            solve(problem([1, 1], [([0, 0], "=", 1)]))["status"], "infeasible"
        )

    def test_fraction_exactness(self):
        r = solve(problem(["1/3", "0"], [([1, 0], "<=", "2/7")]))
        self.assertEqual(r["objective_value"], "2/21")

    def test_alternative_optima(self):
        self.assertTrue(solve(problem([1, 1], [([1, 1], "<=", 4)]))["alternative"])

    def test_unbounded_region_finite_optimum(self):
        r = solve(problem([1, 0], [([1, 0], "<=", 4)]))
        self.assertEqual(r["status"], "optimal")
        self.assertEqual(r["objective_value"], "4")
        self.assertTrue(r["alternative"])

    def test_three_variables(self):
        r = solve(
            problem(
                [3, 2, 4],
                [([1, 1, 1], "<=", 10), ([2, 1, 0], "<=", 12), ([0, 1, 2], "<=", 14)],
            )
        )
        self.assertEqual(r["objective_value"], "37")
        self.assertIsNone(r["graph"])

    def test_bland_cycling_example(self):
        r = solve(
            problem(
                [10, -57, -9, -24],
                [
                    (["1/2", "-11/2", "-5/2", 9], "<=", 0),
                    (["1/2", "-3/2", "-1/2", 1], "<=", 0),
                    ([1, 0, 0, 0], "<=", 1),
                ],
            )
        )
        self.assertEqual(r["status"], "optimal")
        self.assertEqual(r["objective_value"], "1")
        self.assertLess(r["iterations"], 30)

    def test_validation(self):
        for p in [
            problem([1, 2], []),
            problem([1, 2], [([1], "<=", 2)]),
            problem(["nan", 1], [([1, 1], "<=", 2)]),
            problem([1, 1], [([1, 1], "!=", 2)]),
            problem(["1e999999999", 1], [([1, 1], "<=", 2)]),
        ]:
            with self.assertRaises(ValueError):
                solve(p)

    def test_minimization_unbounded(self):
        r = solve(problem([-1, 0], [([0, 1], "=", 0)], "min"))
        self.assertEqual(r["status"], "unbounded")
        self.assertLess(Fraction(r["ray"][0]) * -1, 0)

    def test_random_models_against_vertex_enumeration(self):
        # Oráculo independente: interseções de retas com operações inteiras.
        rng = random.Random(2026)
        for _ in range(150):
            c = [rng.randint(-5, 5), rng.randint(-5, 5)]
            rows = [([1, 0], "<=", 10), ([0, 1], "<=", 10)]
            rows += [
                (
                    [rng.randint(-3, 4), rng.randint(-3, 4)],
                    rng.choice(["<=", ">="]),
                    rng.randint(-6, 20),
                )
                for _ in range(4)
            ]
            boundaries = [(a, b) for a, op, b in rows] + [([1, 0], 0), ([0, 1], 0)]
            vertices = []
            for (a, b), (d, e) in combinations(boundaries, 2):
                det = a[0] * d[1] - a[1] * d[0]
                if not det:
                    continue
                x, y = (
                    Fraction(b * d[1] - a[1] * e, det),
                    Fraction(a[0] * e - b * d[0], det),
                )
                if x < 0 or y < 0:
                    continue
                if all(
                    (
                        v[0] * x + v[1] * y <= rhs
                        if op == "<="
                        else v[0] * x + v[1] * y >= rhs
                    )
                    for v, op, rhs in rows
                ):
                    vertices.append(c[0] * x + c[1] * y)
            sense = rng.choice(["min", "max"])
            r = solve(problem(c, rows, sense))
            if not vertices:
                self.assertEqual(r["status"], "infeasible")
            else:
                self.assertEqual(r["status"], "optimal")
                self.assertEqual(
                    Fraction(r["objective_value"]),
                    (max if sense == "max" else min)(vertices),
                )


if __name__ == "__main__":
    unittest.main()
