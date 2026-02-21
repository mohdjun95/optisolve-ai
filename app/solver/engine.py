from ortools.linear_solver import pywraplp


def solve_lp(c_obj, A_ub, b_ub, A_eq, b_eq, bounds, is_integer_vars,
             problem_type="Minimization", variable_names=None):
    """Solve an LP/MILP problem using OR-Tools.

    Returns a dict with solution details including sensitivity analysis
    for pure LP problems (via GLOP solver).
    """
    if not c_obj:
        return {
            "success": False,
            "status_str": "MODEL_INVALID",
            "error": "Objective coefficients are missing.",
            "obj_val": None,
            "var_vals": None,
            "solver_version": "",
        }

    num_vars = len(c_obj)

    if not is_integer_vars or len(is_integer_vars) != num_vars:
        is_integer_vars = [False] * num_vars
    if not bounds or len(bounds) != num_vars:
        bounds = [(0, None)] * num_vars
    if not variable_names or len(variable_names) != num_vars:
        variable_names = [f"x{i+1}" for i in range(num_vars)]

    num_int_vars = sum(is_integer_vars)
    is_pure_lp = (num_int_vars == 0)

    # Choose solver: GLOP for pure LP (supports sensitivity), SCIP/CBC for MILP
    if is_pure_lp:
        solver = pywraplp.Solver.CreateSolver('GLOP')
        if not solver:
            solver = pywraplp.Solver.CreateSolver('CBC')
    else:
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            solver = pywraplp.Solver.CreateSolver('CBC')

    if not solver:
        return {"success": False, "status_str": "NO_SOLVER",
                "error": "No compatible solver available."}

    infinity = solver.infinity()
    variables = []

    for i in range(num_vars):
        lower_b_raw, upper_b_raw = bounds[i] if bounds and i < len(bounds) else (0, None)
        lower_b = -infinity if lower_b_raw is None else float(lower_b_raw)
        upper_b = infinity if upper_b_raw is None else float(upper_b_raw)
        current_is_integer = is_integer_vars[i] if i < len(is_integer_vars) else False
        if current_is_integer and (lower_b_raw is None or lower_b == -infinity):
            lower_b = 0.0
        var_name = variable_names[i]
        if current_is_integer:
            variables.append(solver.IntVar(lower_b, upper_b, var_name))
        else:
            variables.append(solver.NumVar(lower_b, upper_b, var_name))

    # Build constraints and keep references for sensitivity analysis
    constraint_refs = []

    if A_ub and b_ub and len(A_ub) > 0:
        for i in range(len(A_ub)):
            if num_vars > 0 and (not A_ub[i] or len(A_ub[i]) != num_vars):
                continue
            expr = solver.Sum([A_ub[i][j] * variables[j] for j in range(num_vars)])
            ct = solver.Add(expr <= float(b_ub[i]))
            constraint_refs.append(('ub', i, ct))

    if A_eq and b_eq and len(A_eq) > 0:
        for i in range(len(A_eq)):
            if num_vars > 0 and (not A_eq[i] or len(A_eq[i]) != num_vars):
                continue
            expr = solver.Sum([A_eq[i][j] * variables[j] for j in range(num_vars)])
            ct = solver.Add(expr == float(b_eq[i]))
            constraint_refs.append(('eq', i, ct))

    objective = solver.Objective()
    if num_vars > 0 and c_obj:
        for i in range(num_vars):
            objective.SetCoefficient(variables[i], float(c_obj[i]))
        if problem_type == "Maximization":
            objective.SetMaximization()
        else:
            objective.SetMinimization()
    else:
        objective.SetMinimization()

    status = solver.Solve()

    status_map = {
        pywraplp.Solver.OPTIMAL: "OPTIMAL",
        pywraplp.Solver.FEASIBLE: "FEASIBLE",
        pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
        pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
        pywraplp.Solver.ABNORMAL: "ABNORMAL",
        pywraplp.Solver.MODEL_INVALID: "MODEL_INVALID",
        pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED",
    }

    solution = {
        "success": False,
        "status_code": status,
        "status_str": status_map.get(status, f"UNKNOWN_{status}"),
        "obj_val": None,
        "var_vals": None,
        "solver_version": solver.SolverVersion(),
        "num_vars": num_vars,
        "num_constraints": solver.NumConstraints(),
        "num_integer_vars": num_int_vars,
        "num_continuous_vars": num_vars - num_int_vars,
        "problem_type": problem_type,
        "is_pure_lp": is_pure_lp,
        "variable_names": variable_names,
    }

    if status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        solution["success"] = True
        solution["obj_val"] = objective.Value()
        var_vals = []
        for i, var in enumerate(variables):
            val = var.solution_value()
            var_is_int = is_integer_vars[i] if i < len(is_integer_vars) else False
            display_val = round(val) if var_is_int and abs(val - round(val)) < 1e-9 else val
            var_info = {
                "name": variable_names[i],
                "value": display_val,
                "type": "Integer" if var_is_int else "Continuous",
                "lower_bound": bounds[i][0] if bounds and i < len(bounds) else 0,
                "upper_bound": bounds[i][1] if bounds and i < len(bounds) else None,
            }
            if is_pure_lp:
                try:
                    var_info["reduced_cost"] = var.reduced_cost()
                except Exception:
                    var_info["reduced_cost"] = None
            var_vals.append(var_info)
        solution["var_vals"] = var_vals

        # Sensitivity analysis for pure LP
        if is_pure_lp:
            constraint_details = []
            for ct_type, ct_idx, ct_ref in constraint_refs:
                try:
                    dual = ct_ref.dual_value()
                except Exception:
                    dual = None

                if ct_type == 'ub':
                    row = A_ub[ct_idx]
                    rhs = float(b_ub[ct_idx])
                else:
                    row = A_eq[ct_idx]
                    rhs = float(b_eq[ct_idx])

                lhs_value = sum(row[j] * variables[j].solution_value() for j in range(num_vars))
                slack = rhs - lhs_value

                constraint_details.append({
                    "type": ct_type,
                    "index": ct_idx,
                    "rhs": rhs,
                    "lhs_value": round(lhs_value, 10),
                    "slack": round(slack, 10),
                    "dual_value": dual,
                })
            solution["constraint_details"] = constraint_details

    return solution
