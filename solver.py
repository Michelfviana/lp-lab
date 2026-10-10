"""Simplex de duas fases com aritmética racional e registro didático."""

from fractions import Fraction
from itertools import combinations
import re


def number(value):
    if isinstance(value, bool):
        raise ValueError("Use números nos coeficientes.")
    raw = str(value).strip().replace(",", ".")
    if len(raw) > 40:
        raise ValueError("Cada coeficiente deve ter até 40 caracteres.")
    exponent = re.search(r"[eE]([+-]?\d+)$", raw)
    if exponent and abs(int(exponent.group(1))) > 18:
        raise ValueError("Expoente fora do intervalo permitido (−18 a 18).")
    try:
        result = Fraction(raw)
    except (ValueError, ZeroDivisionError, TypeError):
        raise ValueError(
            f"Coeficiente inválido: {value!r}. Use decimal ou fração."
        ) from None
    if abs(result) > 10**9 or result.denominator > 10**9:
        raise ValueError(
            "Use coeficientes de até 1 bilhão e no máximo 9 casas decimais."
        )
    return result


def validate(data):
    if not isinstance(data, dict):
        raise ValueError("O problema precisa ser um objeto JSON.")
    sense = data.get("sense", "max")
    if sense not in ("max", "min"):
        raise ValueError("Selecione maximização ou minimização.")
    raw = data.get("objective", [])
    if not isinstance(raw, list) or not 2 <= len(raw) <= 8:
        raise ValueError("Informe de 2 a 8 variáveis.")
    c = [number(v) for v in raw]
    rows = data.get("constraints", [])
    if not isinstance(rows, list) or not 1 <= len(rows) <= 20:
        raise ValueError("Informe de 1 a 20 restrições.")
    constraints = []
    for i, row in enumerate(rows):
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("coefficients"), list)
            or len(row["coefficients"]) != len(c)
        ):
            raise ValueError(f"A restrição {i + 1} precisa de {len(c)} coeficientes.")
        op = row.get("operator", "<=")
        if op not in ("<=", ">=", "="):
            raise ValueError(f"Operador inválido na restrição {i + 1}.")
        constraints.append(
            ([number(v) for v in row["coefficients"]], op, number(row.get("rhs", "")))
        )
    return c, sense, constraints


def solve(data):
    c, sense, constraints = validate(data)
    n = len(c)
    names = [f"x{i + 1}" for i in range(n)]
    normalized, notes = [], []
    for i, (a, op, b) in enumerate(constraints):
        if b < 0:
            a, b = [-v for v in a], -b
            op = {"<=": ">=", ">=": "<=", "=": "="}[op]
            notes.append(
                f"R{i + 1}: multiplicamos por −1 e invertemos a desigualdade para tornar o lado direito não negativo."
            )
        normalized.append((a, op, b))
    rows = [a[:] for a, _, _ in normalized]
    basis, artificial = [], []

    def column(name, row, value):
        idx = len(names)
        names.append(name)
        for j, r in enumerate(rows):
            r.append(Fraction(value if j == row else 0))
        return idx

    for i, (_, op, _) in enumerate(normalized):
        if op == "<=":
            basis.append(column(f"f{i + 1}", i, 1))
        else:
            if op == ">=":
                column(f"e{i + 1}", i, -1)
            idx = column(f"a{i + 1}", i, 1)
            artificial.append(idx)
            basis.append(idx)
    table = [r + [normalized[i][2]] for i, r in enumerate(rows)]
    steps = []

    def objective(cost):
        obj = [-v for v in cost] + [Fraction(0)]
        for i, b in enumerate(basis):
            weight = cost[b]
            obj = [x + weight * y for x, y in zip(obj, table[i])]
        return obj

    def snapshot(phase, message, entering=None, leaving=None, ratios=None):
        steps.append(
            {
                "phase": phase,
                "message": message,
                "columns": names[:],
                "basis": [names[b] for b in basis],
                "tableau": [[str(x) for x in r] for r in table],
                "entering": entering,
                "leaving": leaving,
                "ratios": ratios,
            }
        )

    def pivot(row, col):
        p = table[row][col]
        table[row] = [x / p for x in table[row]]
        for i in range(len(table)):
            if i != row:
                weight = table[i][col]
                table[i] = [x - weight * y for x, y in zip(table[i], table[row])]
        basis[row] = col

    def optimize(phase):
        for _ in range(500):
            entering = next((j for j, x in enumerate(table[-1][:-1]) if x < 0), None)
            if entering is None:
                snapshot(
                    phase,
                    "Todos os custos reduzidos são não negativos: esta fase atingiu o ótimo.",
                )
                return "optimal", None
            candidates = [
                (r[-1] / r[entering], basis[i], i)
                for i, r in enumerate(table[:-1])
                if r[entering] > 0
            ]
            if not candidates:
                snapshot(
                    phase,
                    f"{names[entering]} pode crescer sem limite: não há coeficiente positivo na coluna pivô.",
                    entering,
                )
                return "unbounded", entering
            ratio, _, leaving = min(candidates)
            ratios = [
                str(r[-1] / r[entering]) if r[entering] > 0 else None
                for r in table[:-1]
            ]
            snapshot(
                phase,
                f"Entra {names[entering]}, sai {names[basis[leaving]]}. Menor razão: {ratio}. Divida a linha pelo pivô {table[leaving][entering]} e zere a coluna nas demais linhas.",
                entering,
                leaving,
                ratios,
            )
            pivot(leaving, entering)
        snapshot(phase, "Limite de 500 pivôs atingido nesta fase.")
        return "iteration_limit", None

    status, entering = "optimal", None
    if artificial:
        cost = [Fraction(-1 if j in artificial else 0) for j in range(len(names))]
        table.append(objective(cost))
        snapshot(
            1,
            "Fase I: maximizar −(soma das artificiais). O valor precisa chegar a zero para existir solução viável.",
        )
        status, _ = optimize(1)
        if status == "optimal" and table[-1][-1] != 0:
            status = "infeasible"
        if status == "optimal":
            # Artificiais básicas de valor zero: pivotar ou remover equação redundante.
            i = 0
            while i < len(basis):
                if basis[i] in artificial:
                    col = next(
                        (
                            j
                            for j in range(len(names))
                            if j not in artificial and table[i][j] != 0
                        ),
                        None,
                    )
                    if col is not None:
                        snapshot(
                            1,
                            f"Retiramos {names[basis[i]]} da base usando {names[col]} antes da Fase II.",
                            col,
                            i,
                        )
                        pivot(i, col)
                    else:
                        snapshot(
                            1,
                            "Removemos uma equação redundante cuja artificial básica vale zero.",
                        )
                        table.pop(i)
                        basis.pop(i)
                        continue
                i += 1
            keep = [j for j in range(len(names)) if j not in artificial]
            basis = [keep.index(b) for b in basis]
            names = [names[j] for j in keep]
            table = [[r[j] for j in keep] + [r[-1]] for r in table[:-1]]
        else:
            return result(
                status, c, sense, constraints, names, basis, table, steps, notes
            )
    multiplier = 1 if sense == "max" else -1
    cost = [multiplier * v for v in c] + [Fraction(0)] * (len(names) - n)
    table.append(objective(cost))
    snapshot(
        2,
        "Fase II: função objetivo original em forma canônica."
        + (
            " A minimização é convertida em maximização de −Z."
            if sense == "min"
            else ""
        ),
    )
    status, entering = optimize(2)
    return result(
        status, c, sense, constraints, names, basis, table, steps, notes, entering
    )


def result(
    status, c, sense, constraints, names, basis, table, steps, notes, entering=None
):
    values = [Fraction(0)] * len(names)
    for i, b in enumerate(basis):
        values[b] = table[i][-1]
    x = values[: len(c)]
    out = {
        "status": status,
        "steps": steps,
        "notes": notes,
        "iterations": sum(s["ratios"] is not None for s in steps),
        "variables": None,
        "objective_value": None,
        "constraints": [],
        "ray": None,
        "alternative": False,
        "degenerate": False,
        "graph": graph(c, constraints) if len(c) == 2 else None,
    }
    if status in ("optimal", "unbounded"):
        out["variables"] = [str(v) for v in x]
        out["objective_value"] = str(sum(a * b for a, b in zip(c, x)))
        out["degenerate"] = any(values[b] == 0 for b in basis)
        for i, (a, op, b) in enumerate(constraints):
            lhs = sum(v * w for v, w in zip(a, x))
            slack = b - lhs if op == "<=" else lhs - b if op == ">=" else Fraction(0)
            out["constraints"].append(
                {
                    "name": f"R{i + 1}",
                    "lhs": str(lhs),
                    "rhs": str(b),
                    "slack": str(slack),
                    "binding": lhs == b,
                }
            )
        if status == "optimal":
            # Um custo zero só significa solução alternativa se permite mover x.
            for j in range(len(names)):
                if j not in basis and table[-1][j] == 0:
                    direction = [Fraction(int(k == j)) for k in range(len(names))]
                    for i, b in enumerate(basis):
                        direction[b] = -table[i][j]
                    ratios = [r[-1] / r[j] for r in table[:-1] if r[j] > 0]
                    if any(direction[: len(c)]) and (not ratios or min(ratios) > 0):
                        out["alternative"] = True
        if status == "unbounded":
            direction = [Fraction(int(j == entering)) for j in range(len(names))]
            for i, b in enumerate(basis):
                direction[b] = -table[i][entering]
            out["ray"] = [str(v) for v in direction[: len(c)]]
    return out


def graph(c, constraints):
    lines = [(a, b) for a, _, b in constraints] + [
        ([Fraction(1), Fraction(0)], Fraction(0)),
        ([Fraction(0), Fraction(1)], Fraction(0)),
    ]

    def feasible(x):
        if any(v < 0 for v in x):
            return False
        for a, op, b in constraints:
            lhs = sum(v * w for v, w in zip(a, x))
            if (
                (op == "<=" and lhs > b)
                or (op == ">=" and lhs < b)
                or (op == "=" and lhs != b)
            ):
                return False
        return True

    vertices = set()
    for (a, b), (d, e) in combinations(lines, 2):
        det = a[0] * d[1] - a[1] * d[0]
        if det:
            x = ((b * d[1] - a[1] * e) / det, (a[0] * e - b * d[0]) / det)
            if feasible(x):
                vertices.add(x)
    pts = sorted(vertices)
    return {
        "vertices": [
            {
                "x": float(x),
                "y": float(y),
                "exact": [str(x), str(y)],
                "z": str(c[0] * x + c[1] * y),
            }
            for x, y in pts
        ],
        "constraints": [
            {"a": float(a[0]), "b": float(a[1]), "op": op, "rhs": float(b)}
            for a, op, b in constraints
        ],
        "objective": [float(v) for v in c],
    }
