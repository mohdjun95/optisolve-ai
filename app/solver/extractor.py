import google.generativeai as genai
import pathlib
import os
import tempfile

from .prompt import LP_EXTRACTION_PROMPT
from .parser import parse_json_to_lp_vars


def extract_lp_from_file(
    api_key: str,
    file_bytes: bytes,
    filename: str,
    model_name: str = "gemini-2.5-flash",
) -> dict:
    """Upload a file to Gemini, extract LP formulation via JSON mode, return parsed result.

    Returns a dict. On success it has keys: c, variable_names, A_ub, b_ub, A_eq, b_eq,
    bounds, is_integer_variable, problem_type. On failure it has an 'error' key.
    """
    if not api_key:
        return {"error": "Google API Key is missing."}

    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        return {"error": f"Error configuring Google API: {e}"}

    uploaded_file_resource = None
    temp_file_path = None

    try:
        model = genai.GenerativeModel(model_name)

        suffix = pathlib.Path(filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            temp_file_path = tmp.name

        uploaded_file_resource = genai.upload_file(
            path=temp_file_path,
            display_name=filename,
        )

        content_parts = [LP_EXTRACTION_PROMPT, uploaded_file_resource]

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        # Force JSON output for consistent, parseable results
        generation_config = genai.types.GenerationConfig(
            response_mime_type="application/json",
        )

        response = model.generate_content(
            content_parts,
            safety_settings=safety_settings,
            generation_config=generation_config,
        )

        if not response.parts or not hasattr(response, 'text'):
            feedback = ""
            if hasattr(response, 'prompt_feedback'):
                feedback = f" Prompt feedback: {response.prompt_feedback}"
            return {"error": f"API response is empty or does not contain text.{feedback}"}

        json_string = response.text.strip()
        return parse_json_to_lp_vars(json_string)

    except Exception as e:
        return {"error": f"API call or processing failed: {e}"}

    finally:
        if uploaded_file_resource:
            try:
                genai.delete_file(uploaded_file_resource.name)
            except Exception:
                pass
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
