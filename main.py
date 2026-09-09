import cv2
import numpy as np
import os
import uuid

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


# ============================================
# SATQUERY AI — REAL BACKEND
# ============================================

app = FastAPI(title="SatQuery AI API")


# ============================================
# CORS
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# DIRECTORIES
# ============================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "outputs"
)

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# Serve generated visualization files
app.mount(
    "/outputs",
    StaticFiles(directory=OUTPUT_DIR),
    name="outputs",
)


# ============================================
# QUERY RESPONSE
# ============================================

def generate_response(query, summary, changes):

    q = query.lower().strip()

    if (
        "building" in q
        or "buildings" in q
        or "construction" in q
        or "structure" in q
        or "structures" in q
    ):
        message = (
            "Potential structural changes were detected "
            "in the satellite imagery. Candidate regions "
            "may correspond to changes in built structures."
        )

    elif (
        "vegetation" in q
        or "trees" in q
        or "tree" in q
        or "green" in q
        or "land cover" in q
        or "land-cover" in q
    ):
        message = (
            "Potential land-cover changes were detected. "
            "Some candidate regions show differences that "
            "may indicate vegetation loss, growth, or other "
            "surface-cover changes."
        )

    elif (
        "water" in q
        or "river" in q
        or "lake" in q
        or "coast" in q
        or "coastal" in q
    ):
        message = (
            "Candidate surface changes were detected in "
            "the comparison. These regions can be reviewed "
            "using the visualization layers."
        )

    elif (
        "road" in q
        or "roads" in q
        or "highway" in q
        or "street" in q
        or "transport" in q
    ):
        message = (
            "Potential changes were detected in areas that "
            "may contain transportation infrastructure. "
            "The detected regions can be inspected using "
            "the visualization layers."
        )

    elif (
        "largest" in q
        or "biggest" in q
        or "significant" in q
        or "major" in q
    ):
        message = (
            f"The largest detected change region contains "
            f"{summary['largestRegionPixels']} changed pixels. "
            f"{summary['detectedRegions']} candidate regions "
            f"were identified."
        )

    elif (
        "where" in q
        or "location" in q
        or "locations" in q
        or "region" in q
        or "regions" in q
    ):
        message = (
            f"{summary['detectedRegions']} candidate change "
            "regions were detected. Their locations and "
            "bounding boxes can be inspected in the "
            "Change Regions visualization."
        )

    else:
        message = (
            f"Analysis complete. I detected "
            f"{summary['detectedRegions']} candidate regions "
            f"of change between the two satellite images. "
            f"The estimated changed area is "
            f"{summary['changedAreaPercentage']}% "
            "of the valid overlap."
        )

    return {
        "success": True,
        "message": message,
        "summary": summary,
        "changes": changes,
        "query": query,
    }


# ============================================
# IMAGE PROCESSING
# ============================================

def process_images(
    before_path,
    after_path,
    job_id,
):
    # ========================================
    # LOAD IMAGES
    # ========================================

    img_2025 = cv2.imread(before_path)
    img_2026 = cv2.imread(after_path)

    if img_2025 is None:
        raise RuntimeError(
            "Could not read the before satellite image."
        )

    if img_2026 is None:
        raise RuntimeError(
            "Could not read the after satellite image."
        )

    print(
        "Before image loaded:",
        img_2025.shape
    )

    print(
        "After image loaded:",
        img_2026.shape
    )


    # ========================================
    # GRAYSCALE
    # ========================================

    gray_2025 = cv2.cvtColor(
        img_2025,
        cv2.COLOR_BGR2GRAY
    )

    gray_2026 = cv2.cvtColor(
        img_2026,
        cv2.COLOR_BGR2GRAY
    )


    # ========================================
    # FEATURE DETECTION
    # ========================================

    sift = cv2.SIFT_create()

    keypoints_2025, descriptors_2025 = (
        sift.detectAndCompute(
            gray_2025,
            None
        )
    )

    keypoints_2026, descriptors_2026 = (
        sift.detectAndCompute(
            gray_2026,
            None
        )
    )

    if (
        descriptors_2025 is None
        or descriptors_2026 is None
    ):
        raise RuntimeError(
            "Could not detect enough visual features "
            "in one or both satellite images."
        )

    print(
        "Features in before image:",
        len(keypoints_2025)
    )

    print(
        "Features in after image:",
        len(keypoints_2026)
    )


    # ========================================
    # FEATURE MATCHING
    # ========================================

    matcher = cv2.BFMatcher()

    matches = matcher.knnMatch(
        descriptors_2025,
        descriptors_2026,
        k=2
    )


    # ========================================
    # LOWE RATIO TEST
    # ========================================

    good_matches = []

    for pair in matches:

        if len(pair) < 2:
            continue

        m, n = pair

        if m.distance < 0.7 * n.distance:
            good_matches.append(m)

    print(
        "Good matches:",
        len(good_matches)
    )


    # ========================================
    # MATCH CHECK
    # ========================================

    if len(good_matches) < 10:
        raise RuntimeError(
            "Not enough reliable feature matches "
            "for image alignment."
        )


    # ========================================
    # MATCHING POINTS
    # ========================================

    points_2025 = np.float32(
        [
            keypoints_2025[m.queryIdx].pt
            for m in good_matches
        ]
    ).reshape(-1, 1, 2)

    points_2026 = np.float32(
        [
            keypoints_2026[m.trainIdx].pt
            for m in good_matches
        ]
    ).reshape(-1, 1, 2)


    # ========================================
    # HOMOGRAPHY
    # ========================================

    homography, mask = cv2.findHomography(
        points_2025,
        points_2026,
        cv2.RANSAC,
        5.0
    )

    if homography is None:
        raise RuntimeError(
            "Could not calculate image transformation."
        )

    if mask is None:
        raise RuntimeError(
            "Could not determine reliable image matches."
        )

    inliers = int(mask.sum())

    print(
        "Reliable matches after RANSAC:",
        inliers
    )


    # ========================================
    # ALIGN BEFORE IMAGE
    # ========================================

    height_2026, width_2026 = (
        gray_2026.shape
    )

    aligned_2025 = cv2.warpPerspective(
        img_2025,
        homography,
        (
            width_2026,
            height_2026
        )
    )


    # ========================================
    # VALID OVERLAP MASK
    # ========================================

    valid_2025 = (
        np.ones(
            img_2025.shape[:2],
            dtype=np.uint8
        ) * 255
    )

    valid_overlap = cv2.warpPerspective(
        valid_2025,
        homography,
        (
            width_2026,
            height_2026
        )
    )

    valid_kernel = np.ones(
        (15, 15),
        np.uint8
    )

    valid_overlap = cv2.erode(
        valid_overlap,
        valid_kernel,
        iterations=1
    )


    # ========================================
    # ALIGNMENT OVERLAY
    # ========================================

    alignment_overlay = cv2.addWeighted(
        aligned_2025,
        0.5,
        img_2026,
        0.5,
        0
    )


    # ========================================
    # DIFFERENCE
    # ========================================

    gray_aligned_2025 = cv2.cvtColor(
        aligned_2025,
        cv2.COLOR_BGR2GRAY
    )

    gray_2026_reference = cv2.cvtColor(
        img_2026,
        cv2.COLOR_BGR2GRAY
    )

    difference = cv2.absdiff(
        gray_aligned_2025,
        gray_2026_reference
    )

    difference_normalized = cv2.normalize(
        difference,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )


    # ========================================
    # CHANGE MASK
    # ========================================

    difference_blurred = cv2.GaussianBlur(
        difference,
        (5, 5),
        0
    )

    threshold_value = 40

    _, change_mask = cv2.threshold(
        difference_blurred,
        threshold_value,
        255,
        cv2.THRESH_BINARY
    )

    change_mask[
        valid_overlap == 0
    ] = 0


    # ========================================
    # MORPHOLOGICAL CLEANUP
    # ========================================

    kernel = np.ones(
        (5, 5),
        np.uint8
    )

    change_mask = cv2.morphologyEx(
        change_mask,
        cv2.MORPH_OPEN,
        kernel
    )

    change_mask = cv2.morphologyEx(
        change_mask,
        cv2.MORPH_CLOSE,
        kernel
    )


    # ========================================
    # REMOVE SMALL REGIONS
    # ========================================

    num_labels, labels, stats, centroids = (
        cv2.connectedComponentsWithStats(
            change_mask,
            connectivity=8
        )
    )

    MIN_AREA = 100

    clean_mask = np.zeros_like(
        change_mask
    )

    for i in range(
        1,
        num_labels
    ):

        area = stats[
            i,
            cv2.CC_STAT_AREA
        ]

        if area >= MIN_AREA:

            clean_mask[
                labels == i
            ] = 255

    change_mask = clean_mask


    # ========================================
    # CHANGE REGIONS
    # ========================================

    num_labels, labels, stats, centroids = (
        cv2.connectedComponentsWithStats(
            change_mask,
            connectivity=8
        )
    )

    MIN_REGION_AREA = 20

    change_regions = []

    for label in range(
        1,
        num_labels
    ):

        area = stats[
            label,
            cv2.CC_STAT_AREA
        ]

        if area < MIN_REGION_AREA:
            continue

        x = stats[
            label,
            cv2.CC_STAT_LEFT
        ]

        y = stats[
            label,
            cv2.CC_STAT_TOP
        ]

        w = stats[
            label,
            cv2.CC_STAT_WIDTH
        ]

        h = stats[
            label,
            cv2.CC_STAT_HEIGHT
        ]

        cx, cy = centroids[label]

        change_regions.append(
            {
                "id": len(change_regions) + 1,
                "area": int(area),
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
                "center_x": round(
                    float(cx),
                    2
                ),
                "center_y": round(
                    float(cy),
                    2
                ),
            }
        )


    # ========================================
    # CHANGE OVERLAY
    # ========================================

    change_overlay = img_2026.copy()

    red_overlay = change_overlay.copy()

    red_overlay[
        change_mask > 0
    ] = [0, 0, 255]

    change_overlay = cv2.addWeighted(
        img_2026,
        0.65,
        red_overlay,
        0.35,
        0
    )


    # ========================================
    # HEATMAP
    # ========================================

    heatmap = cv2.applyColorMap(
        difference_normalized,
        cv2.COLORMAP_JET
    )

    heatmap[
        valid_overlap == 0
    ] = 0


    # ========================================
    # REGION VISUALIZATION
    # ========================================

    region_output = img_2026.copy()

    for region in change_regions:

        x = region["x"]
        y = region["y"]
        w = region["width"]
        h = region["height"]

        cv2.rectangle(
            region_output,
            (x, y),
            (x + w, y + h),
            (0, 0, 255),
            2
        )

        cv2.putText(
            region_output,
            f"Change {region['id']}",
            (
                x,
                max(y - 8, 15)
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            1,
            cv2.LINE_AA
        )


    # ========================================
    # CHANGE STATISTICS
    # ========================================

    valid_pixels = np.count_nonzero(
        valid_overlap
    )

    changed_pixels = np.count_nonzero(
        change_mask
    )

    if valid_pixels > 0:

        change_percentage = (
            changed_pixels
            / valid_pixels
        ) * 100

    else:

        change_percentage = 0


    largest_region_pixels = 0

    if change_regions:

        largest_region_pixels = max(
            region["area"]
            for region in change_regions
        )


    summary = {
        "detectedRegions": len(
            change_regions
        ),
        "changedAreaPercentage": round(
            change_percentage,
            2
        ),
        "largestRegionPixels": int(
            largest_region_pixels
        ),
    }


    # ========================================
    # SAVE JOB OUTPUTS
    # ========================================

    job_output_dir = os.path.join(
        OUTPUT_DIR,
        job_id
    )

    os.makedirs(
        job_output_dir,
        exist_ok=True
    )


    def save_output(
        filename,
        image
    ):

        path = os.path.join(
            job_output_dir,
            filename
        )

        success = cv2.imwrite(
            path,
            image
        )

        if not success:
            raise RuntimeError(
                f"Could not save output: {filename}"
            )

        return (
            f"/outputs/{job_id}/{filename}"
        )


    visualization_urls = {
        "alignment": save_output(
            "alignment_overlay.jpg",
            alignment_overlay
        ),

        "changeOverlay": save_output(
            "change_overlay.jpg",
            change_overlay
        ),

        "heatmap": save_output(
            "change_heatmap.jpg",
            heatmap
        ),

        "mask": save_output(
            "change_mask.jpg",
            change_mask
        ),

        "regions": save_output(
            "change_regions.jpg",
            region_output
        ),

        "difference": save_output(
            "raw_difference.jpg",
            difference_normalized
        ),
    }


    # ========================================
    # RETURN PROCESSING RESULT
    # ========================================

    return {
        "summary": summary,
        "changes": change_regions,
        "visualizations": visualization_urls,
        "inliers": inliers,
    }


# ============================================
# ANALYZE ENDPOINT
# ============================================

@app.post("/analyze")
async def analyze(
    before_image: UploadFile = File(...),
    after_image: UploadFile = File(...),
    query: str = Form(...),
):

    job_id = uuid.uuid4().hex

    before_filename = (
        f"{job_id}_before"
        + os.path.splitext(
            before_image.filename or ".jpg"
        )[1]
    )

    after_filename = (
        f"{job_id}_after"
        + os.path.splitext(
            after_image.filename or ".jpg"
        )[1]
    )

    before_path = os.path.join(
        UPLOAD_DIR,
        before_filename
    )

    after_path = os.path.join(
        UPLOAD_DIR,
        after_filename
    )


    # ========================================
    # SAVE UPLOADED FILES
    # ========================================

    with open(
        before_path,
        "wb"
    ) as buffer:

        buffer.write(
            await before_image.read()
        )


    with open(
        after_path,
        "wb"
    ) as buffer:

        buffer.write(
            await after_image.read()
        )


    try:

        result = process_images(
            before_path,
            after_path,
            job_id
        )

        analysis = generate_response(
            query,
            result["summary"],
            result["changes"]
        )

        return {
            **analysis,

            "visualizations": (
                result["visualizations"]
            ),

            "receivedImages": {
                "before": True,
                "after": True,
            },

            "inliers": result["inliers"],
        }

    except Exception as error:

        return {
            "success": False,
            "message": str(error),
            "query": query,
            "visualizations": None,
        }


# ============================================
# SINGLE-IMAGE ANALYSIS (VQA)
# ============================================

def analyze_single_image(image_path):

    image = cv2.imread(image_path)

    if image is None:
        raise RuntimeError(
            "Could not read the uploaded satellite image."
        )

    height, width = image.shape[:2]
    total_pixels = height * width


    # ========================================
    # VEGETATION PROXY (EXCESS GREEN INDEX)
    # ========================================

    blue = image[:, :, 0].astype(np.int16)
    green = image[:, :, 1].astype(np.int16)
    red = image[:, :, 2].astype(np.int16)

    excess_green = (2 * green) - red - blue

    vegetation_pixels = np.count_nonzero(
        excess_green > 15
    )

    vegetation_percentage = (
        vegetation_pixels / total_pixels
    ) * 100


    # ========================================
    # WATER PROXY (BLUE DOMINANT PIXELS)
    # ========================================

    water_pixels = np.count_nonzero(
        (blue > red) & (blue > green) & (blue > 60)
    )

    water_percentage = (
        water_pixels / total_pixels
    ) * 100


    # ========================================
    # STRUCTURE PROXY (EDGE DENSITY)
    # ========================================

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    edges = cv2.Canny(gray, 60, 160)

    edge_density = (
        np.count_nonzero(edges) / total_pixels
    ) * 100


    # ========================================
    # BRIGHTNESS
    # ========================================

    brightness = float(np.mean(gray))

    return {
        "vegetationPercentage": round(vegetation_percentage, 2),
        "waterPercentage": round(water_percentage, 2),
        "edgeDensity": round(edge_density, 2),
        "brightness": round(brightness, 2),
    }


def generate_vqa_response(query, stats):

    q = query.lower().strip()

    if (
        "water" in q
        or "river" in q
        or "lake" in q
        or "coast" in q
    ):
        if stats["waterPercentage"] > 5:
            message = (
                f"Water-like pixels make up "
                f"{stats['waterPercentage']}% of the image, "
                "suggesting a visible water body."
            )
        else:
            message = (
                f"Only {stats['waterPercentage']}% of the image "
                "matches water-like coloring, so no significant "
                "water body appears to be present."
            )

    elif (
        "vegetation" in q
        or "tree" in q
        or "trees" in q
        or "green" in q
        or "forest" in q
    ):
        message = (
            f"Vegetation-like coloring covers approximately "
            f"{stats['vegetationPercentage']}% of the image."
        )

    elif (
        "building" in q
        or "buildings" in q
        or "structure" in q
        or "structures" in q
        or "urban" in q
    ):
        if stats["edgeDensity"] > 8:
            message = (
                f"Edge density is {stats['edgeDensity']}%, which is "
                "consistent with built structures or urban surfaces "
                "in this image."
            )
        else:
            message = (
                f"Edge density is only {stats['edgeDensity']}%, which "
                "suggests few or no distinct built structures in "
                "this image."
            )

    elif (
        "bright" in q
        or "dark" in q
        or "cloud" in q
        or "clouds" in q
    ):
        message = (
            f"The image has an average brightness of "
            f"{stats['brightness']} out of 255."
        )

    else:
        message = (
            f"This image shows approximately "
            f"{stats['vegetationPercentage']}% vegetation-like cover, "
            f"{stats['waterPercentage']}% water-like cover, and an "
            f"edge density of {stats['edgeDensity']}%, which can "
            "indicate the presence of built structures."
        )

    return message


@app.post("/vqa")
async def vqa(
    image: UploadFile = File(...),
    query: str = Form(...),
):

    job_id = uuid.uuid4().hex

    image_filename = (
        f"{job_id}_vqa"
        + os.path.splitext(
            image.filename or ".jpg"
        )[1]
    )

    image_path = os.path.join(
        UPLOAD_DIR,
        image_filename
    )

    with open(
        image_path,
        "wb"
    ) as buffer:

        buffer.write(
            await image.read()
        )

    try:

        stats = analyze_single_image(
            image_path
        )

        message = generate_vqa_response(
            query,
            stats
        )

        return {
            "success": True,
            "message": message,
            "query": query,
            "stats": stats,
        }

    except Exception as error:

        return {
            "success": False,
            "message": str(error),
            "query": query,
        }


# ============================================
# HEALTH CHECK
# ============================================

@app.get("/")
def root():

    return {
        "status": "online",
        "service": "SatQuery AI",
        "message": (
            "Satellite change detection "
            "backend is running."
        ),
    }