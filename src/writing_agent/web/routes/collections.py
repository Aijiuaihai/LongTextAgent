"""Collection management endpoints."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from writing_agent.rag.collections import (
    delete_collection,
    export_collection_manifest,
    get_collection_stats,
    list_collections,
    rebuild_collection,
)
from writing_agent.rag.retriever import VectorRetriever
from writing_agent.rag.vector_index import load_chroma_index
from writing_agent.web.services.schemas import CollectionBuildRequest, RetrievalRequest

router = APIRouter()


@router.get("/collections")
def list_collections_endpoint(request: Request) -> list[dict[str, object]]:
    """List collections."""

    return list_collections(request.app.state.settings)


@router.post("/collections")
def build_collection_endpoint(
    payload: CollectionBuildRequest,
    request: Request,
) -> dict[str, object]:
    """Build or rebuild a collection."""

    if payload.reset:
        return rebuild_collection(
            payload.collection,
            payload.source_paths,
            request.app.state.settings,
        )
    return rebuild_collection(payload.collection, payload.source_paths, request.app.state.settings)


@router.get("/collections/{collection}/stats")
def collection_stats(collection: str, request: Request) -> dict[str, object]:
    """Show collection stats."""

    return get_collection_stats(collection, request.app.state.settings)


@router.delete("/collections/{collection}")
def delete_collection_endpoint(
    collection: str,
    request: Request,
    confirm: bool = False,
) -> dict[str, object]:
    """Delete a collection after explicit confirmation."""

    if not confirm:
        return JSONResponse({"error": "confirm=true is required"}, status_code=400)  # type: ignore[return-value]
    return {"deleted": delete_collection(collection, request.app.state.settings)}


@router.post("/collections/{collection}/retrieve")
def retrieve_collection(
    collection: str,
    payload: RetrievalRequest,
    request: Request,
) -> list[dict[str, object]]:
    """Run retrieval test against a collection."""

    vector_store = load_chroma_index(
        collection_name=collection,
        settings=request.app.state.settings,
    )
    results = VectorRetriever(vector_store).retrieve(payload.query, top_k=payload.top_k)
    return [result.model_dump(mode="json") for result in results]


@router.post("/collections/{collection}/export-manifest")
def export_manifest(collection: str, request: Request) -> dict[str, object]:
    """Export a collection manifest under outputs."""

    output = Path(request.app.state.settings.output_dir) / f"{collection}-manifest-export.json"
    path = export_collection_manifest(collection, output, request.app.state.settings)
    return {"path": str(path)}
