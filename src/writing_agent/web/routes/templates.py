"""DOCX template endpoints."""

from pathlib import Path

from fastapi import APIRouter

from writing_agent.tools.docx_preflight import validate_docx_template

router = APIRouter()


@router.get("/templates")
def list_templates() -> dict[str, object]:
    """List local template assets."""

    root = Path("templates")
    docx_files = sorted(str(path) for path in root.glob("*.docx")) if root.exists() else []
    style_mappings = sorted(str(path) for path in root.glob("*.json")) if root.exists() else []
    return {"templates": docx_files, "style_mappings": style_mappings}


@router.post("/templates/preflight")
def preflight_template(payload: dict[str, str]) -> dict[str, object]:
    """Run DOCX template preflight."""

    result = validate_docx_template(
        payload["template_path"],
        style_mapping_path=payload.get("style_mapping_path"),
    )
    return result.model_dump(mode="json")

