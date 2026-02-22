import json


def parse_json_to_lp_vars(json_string: str) -> dict:
    """Parse JSON output from Gemini into LP variable components.

    Returns a dict with keys: c, variable_names, A_ub, b_ub, A_eq, b_eq,
    bounds, is_integer_variable, problem_type.
    On failure, returns a dict with 'error' key.
    """
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse JSON from LLM output: {e}",
            "raw_output": json_string,
        }

    try:
        # --- Kill switch: reject non-LP documents ---
        if data.get("is_valid_lp") is False:
            reason = data.get("rejection_reason", "Document does not contain a valid LP/MILP problem.")
            return {"error": reason}

        # --- c (required) ---
        c = data.get("c")
        if not isinstance(c, list) or len(c) == 0:
            raise ValueError("'c' (objective coefficients) is missing or empty.")
        c = [float(x) for x in c]
        num_vars = len(c)

        # --- problem_type ---
        problem_type = data.get("problem_type", "Minimization")
        if problem_type not in ("Minimization", "Maximization"):
            problem_type = "Maximization" if "max" in str(problem_type).lower() else "Minimization"

        # --- variable_names (graceful fallback) ---
        variable_names = data.get("variable_names")
        if (isinstance(variable_names, list)
                and len(variable_names) == num_vars):
            variable_names = [str(n) for n in variable_names]
        else:
            variable_names = [f"x{i+1}" for i in range(num_vars)]

        # --- is_integer_variable ---
        is_int = data.get("is_integer_variable")
        if isinstance(is_int, list) and len(is_int) == num_vars:
            is_integer_variable = [bool(v) for v in is_int]
        else:
            is_integer_variable = [False] * num_vars

        # --- A_ub, b_ub ---
        A_ub = data.get("A_ub")
        b_ub = data.get("b_ub")
        if A_ub is not None and b_ub is not None:
            if not isinstance(A_ub, list) or not isinstance(b_ub, list):
                A_ub, b_ub = None, None
            elif len(A_ub) != len(b_ub):
                raise ValueError("Mismatch between A_ub rows and b_ub length.")
            else:
                A_ub = [[float(x) for x in row] for row in A_ub]
                b_ub = [float(x) for x in b_ub]
                # Validate column counts
                for i, row in enumerate(A_ub):
                    if len(row) != num_vars:
                        raise ValueError(f"A_ub row {i} has {len(row)} columns, expected {num_vars}.")
        else:
            A_ub, b_ub = None, None

        # --- A_eq, b_eq ---
        A_eq = data.get("A_eq")
        b_eq = data.get("b_eq")
        if A_eq is not None and b_eq is not None:
            if not isinstance(A_eq, list) or not isinstance(b_eq, list):
                A_eq, b_eq = None, None
            elif len(A_eq) != len(b_eq):
                raise ValueError("Mismatch between A_eq rows and b_eq length.")
            else:
                A_eq = [[float(x) for x in row] for row in A_eq]
                b_eq = [float(x) for x in b_eq]
                for i, row in enumerate(A_eq):
                    if len(row) != num_vars:
                        raise ValueError(f"A_eq row {i} has {len(row)} columns, expected {num_vars}.")
        else:
            A_eq, b_eq = None, None

        # --- bounds ---
        raw_bounds = data.get("bounds")
        if isinstance(raw_bounds, list) and len(raw_bounds) == num_vars:
            bounds = []
            for i, b in enumerate(raw_bounds):
                if not isinstance(b, (list, tuple)) or len(b) != 2:
                    bounds.append((0, None))
                    continue
                lb = None if b[0] is None else float(b[0])
                ub = None if b[1] is None else float(b[1])
                bounds.append((lb, ub))
        else:
            bounds = [(0, None)] * num_vars

        return {
            "c": c,
            "variable_names": variable_names,
            "A_ub": A_ub,
            "b_ub": b_ub,
            "A_eq": A_eq,
            "b_eq": b_eq,
            "bounds": bounds,
            "is_integer_variable": is_integer_variable,
            "problem_type": problem_type,
        }

    except Exception as e:
        return {
            "error": str(e),
            "raw_output": json_string,
        }
