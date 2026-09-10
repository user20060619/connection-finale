"""
SatQuery AI Backend - Main API Server
Final integration version matching frontend contract
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
import uuid
import shutil
from datetime import datetime
import uvicorn
import math

from backend.pipeline import answer_query
from backend.services.geo_service import generate_visualizations, detect_water_changes, analyze_single_image

app = FastAPI(
    title="SatQuery AI",
    description="Satellite change detection and query system for SIH 2026",
    version="1.0.0"
)

# CORS configuration for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output directory for generated files
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Serve static files for visualizations
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


@app.get("/")
async def health_check():
    """Backend health status endpoint"""
    return {
        "status": "online",
        "service": "SatQuery AI",
        "message": "Satellite change detection backend is running.",
        "timestamp": datetime.now().isoformat()
    }


def generate_text_answer(query, results, water_results):
    """
    Generate a text answer based on the query and analysis results.
    Returns a concise answer matching frontend expectations.
    """
    query_lower = query.lower()
    
    # Vegetation questions
    vegetation_keywords = ["vegetation", "green", "plants", "trees", "forest", "crop", "ndvi"]
    if any(word in query_lower for word in vegetation_keywords):
        ndvi_change = results["ndvi_after"] - results["ndvi_before"]
        detected = results["detected_regions"]
        if ndvi_change > 0.05:
            return f"Vegetation increased by {abs(ndvi_change):.1%}. Found {detected} changed regions."
        elif ndvi_change < -0.05:
            return f"Vegetation decreased by {abs(ndvi_change):.1%}. Found {detected} changed regions."
        else:
            return f"No significant vegetation change. Found {detected} changed regions."
    
    # Water questions
    water_keywords = ["water", "river", "lake", "reservoir", "flood", "ndwi"]
    if any(word in query_lower for word in water_keywords):
        loss = water_results["water_loss_percentage"]
        gain = water_results["water_gain_percentage"]
        if gain > loss:
            return f"Water increased. New water detected in {gain:.1f}% of the area."
        elif loss > gain:
            return f"Water decreased. Water lost from {loss:.1f}% of the area."
        else:
            return f"Water changes detected. {water_results['water_changed']:.1f}% of the area changed."
    
    # General change questions
    change_keywords = ["change", "changed", "difference", "diff", "what changed"]
    if any(word in query_lower for word in change_keywords):
        return f"Detected {results['detected_regions']} change regions covering {results['changed_percentage']:.1f}% of the image."
    
    # Default answer
    return f"Analysis complete. Found {results['detected_regions']} changed regions in the image."


def ensure_finite(value, default=0):
    """Ensure value is a finite number (no NaN, Infinity, None)"""
    if value is None or math.isnan(value) or math.isinf(value):
        return default
    return value


@app.post("/analyze")
async def analyze_images(
    before_image: UploadFile = File(...),
    after_image: UploadFile = File(...),
    query: str = Form(...)
):
    """
    Analyze two satellite images and detect changes.
    Returns response matching the frontend contract.
    """
    try:
        # Generate unique job ID and create job directory
        job_id = str(uuid.uuid4())
        job_dir = os.path.join(OUTPUT_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

        # Save uploaded images
        before_path = os.path.join(job_dir, "before.jpg")
        after_path = os.path.join(job_dir, "after.jpg")

        with open(before_path, "wb") as f:
            shutil.copyfileobj(before_image.file, f)

        with open(after_path, "wb") as f:
            shutil.copyfileobj(after_image.file, f)

        # Generate visualizations and detect changes
        results = generate_visualizations(before_path, after_path, job_dir)

        # Detect water changes using NDWI
        water_results = detect_water_changes(before_path, after_path)

        # Generate dynamic text answer
        message = generate_text_answer(query, results, water_results)

        # Prepare response matching frontend contract
        response = {
            "success": True,
            "message": message,
            "summary": {
                "detectedRegions": ensure_finite(results["detected_regions"], 0),
                "changedAreaPercentage": ensure_finite(round(results["changed_percentage"] / 100, 4), 0),
                "largestRegionPixels": ensure_finite(results["largest_region"], 0)
            },
            "changes": results["regions"] if results["regions"] else [],
            "query": query,
            "visualizations": {
                "alignment": f"/outputs/{job_id}/alignment_overlay.jpg",
                "changeOverlay": f"/outputs/{job_id}/change_overlay.jpg",
                "heatmap": f"/outputs/{job_id}/change_heatmap.jpg",
                "mask": f"/outputs/{job_id}/change_mask.png",
                "regions": f"/outputs/{job_id}/change_regions.jpg",
                "difference": f"/outputs/{job_id}/raw_difference.jpg"
            }
        }

        return JSONResponse(content=response)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Processing failed: {str(e)}",
                "query": query if 'query' in locals() else None,
                "visualizations": None
            }
        )


@app.post("/query")
async def query_endpoint(query: str, image_ids: list[str] = []):
    """Legacy endpoint for backward compatibility"""
    return answer_query(query, image_ids)


def generate_vqa_answer(query, stats):
    """Templated single-image answer, same rule as /analyze: numbers are computed, not generated."""
    query_lower = query.lower()

    if any(w in query_lower for w in ["water", "river", "lake", "coast"]):
        if stats["waterPercentage"] > 5:
            return (f"Water-like pixels make up {stats['waterPercentage']}% of the image, "
                    "suggesting a visible water body.")
        return (f"Only {stats['waterPercentage']}% of the image matches water-like coloring, "
                "so no significant water body appears to be present.")

    if any(w in query_lower for w in ["vegetation", "tree", "trees", "green", "forest"]):
        return f"Vegetation-like coloring covers approximately {stats['vegetationPercentage']}% of the image."

    if any(w in query_lower for w in ["building", "buildings", "structure", "structures", "urban"]):
        if stats["edgeDensity"] > 8:
            return (f"Edge density is {stats['edgeDensity']}%, which is consistent with built "
                    "structures or urban surfaces in this image.")
        return (f"Edge density is only {stats['edgeDensity']}%, which suggests few or no "
                "distinct built structures in this image.")

    if any(w in query_lower for w in ["bright", "dark", "cloud", "clouds"]):
        return f"The image has an average brightness of {stats['brightness']} out of 255."

    return (f"This image shows approximately {stats['vegetationPercentage']}% vegetation-like cover, "
            f"{stats['waterPercentage']}% water-like cover, and an edge density of "
            f"{stats['edgeDensity']}%, which can indicate the presence of built structures.")


@app.post("/vqa")
async def vqa(
    image: UploadFile = File(...),
    query: str = Form(...)
):
    """Single-image visual question answering."""
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    image_path = os.path.join(job_dir, "vqa_image.jpg")
    with open(image_path, "wb") as f:
        shutil.copyfileobj(image.file, f)

    try:
        stats = analyze_single_image(image_path)
        message = generate_vqa_answer(query, stats)

        return {
            "success": True,
            "message": message,
            "query": query,
            "stats": stats,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Processing failed: {str(e)}",
                "query": query,
            }
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )