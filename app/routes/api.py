import pathlib
from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from ..config import GOOGLE_API_KEY, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB
from ..solver.extractor import extract_lp_from_file
from ..solver.engine import solve_lp

router = APIRouter()


@router.post("/solve")
async def solve(
    file: UploadFile = File(...),
    api_key: str = Form(""),
    model_name: str = Form("gemini-1.5-pro-latest"),
):
    # Resolve API key: user-provided takes priority, then server env
    effective_key = api_key.strip() or GOOGLE_API_KEY
    if not effective_key:
        raise HTTPException(status_code=400, detail="No API key provided. Enter one in the app or set GOOGLE_API_KEY on the server.")

    # Validate file extension
    suffix = pathlib.Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    # Read file bytes
    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_UPLOAD_SIZE_MB}MB limit.")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Step 1: Extract LP formulation via Gemini
    extraction = extract_lp_from_file(effective_key, file_bytes, file.filename, model_name)

    if "error" in extraction:
        return {
            "success": False,
            "stage": "extraction",
            "error": extraction["error"],
            "extraction": None,
            "solution": None,
        }

    # Step 2: Solve with OR-Tools
    solution = solve_lp(
        c_obj=extraction["c"],
        A_ub=extraction["A_ub"],
        b_ub=extraction["b_ub"],
        A_eq=extraction["A_eq"],
        b_eq=extraction["b_eq"],
        bounds=extraction["bounds"],
        is_integer_vars=extraction["is_integer_variable"],
        problem_type=extraction["problem_type"],
        variable_names=extraction.get("variable_names"),
    )

    return {
        "success": solution.get("success", False),
        "stage": "complete",
        "extraction": {
            "problem_type": extraction["problem_type"],
            "variable_names": extraction.get("variable_names", []),
            "num_vars": len(extraction["c"]),
            "num_inequality": len(extraction["A_ub"]) if extraction["A_ub"] else 0,
            "num_equality": len(extraction["A_eq"]) if extraction["A_eq"] else 0,
            "num_integer": sum(extraction["is_integer_variable"]) if extraction["is_integer_variable"] else 0,
            "c": extraction["c"],
            "A_ub": extraction["A_ub"],
            "b_ub": extraction["b_ub"],
            "A_eq": extraction["A_eq"],
            "b_eq": extraction["b_eq"],
            "bounds": extraction["bounds"],
            "is_integer_variable": extraction["is_integer_variable"],
        },
        "solution": solution,
        "error": solution.get("error"),
    }
