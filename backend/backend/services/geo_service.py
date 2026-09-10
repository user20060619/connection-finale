import cv2
import numpy as np
import os
from PIL import Image

def calculate_ndvi(nir_band, red_band):
    """NDVI = (NIR - RED) / (NIR + RED)"""
    ndvi = (nir_band.astype(np.float32) - red_band.astype(np.float32)) / (nir_band.astype(np.float32) + red_band.astype(np.float32) + 1e-10)
    return ndvi

def calculate_ndwi(green_band, nir_band):
    """NDWI = (GREEN - NIR) / (GREEN + NIR)"""
    ndwi = (green_band.astype(np.float32) - nir_band.astype(np.float32)) / (green_band.astype(np.float32) + nir_band.astype(np.float32) + 1e-10)
    return ndwi

def calculate_area_percentage(mask, pixel_size_meters=10):
    """Calculate area in km² from mask pixels"""
    total_pixels = mask.size
    changed_pixels = np.sum(mask > 0)
    changed_percentage = (changed_pixels / total_pixels) * 100
    area_km2 = (changed_pixels * pixel_size_meters * pixel_size_meters) / 1_000_000
    return changed_percentage, area_km2

def detect_water_changes(before_path, after_path):
    """Detect water changes using NDWI"""
    
    before = cv2.imread(before_path)
    after = cv2.imread(after_path)
    
    if before is None or after is None:
        return {"error": "Could not load images"}
    
    height = min(before.shape[0], after.shape[0])
    width = min(before.shape[1], after.shape[1])
    before = cv2.resize(before, (width, height))
    after = cv2.resize(after, (width, height))
    
    before_green = before[:, :, 1].astype(np.float32)
    before_nir = before[:, :, 2].astype(np.float32)
    after_green = after[:, :, 1].astype(np.float32)
    after_nir = after[:, :, 2].astype(np.float32)
    
    ndwi_before = calculate_ndwi(before_green, before_nir)
    ndwi_after = calculate_ndwi(after_green, after_nir)
    
    water_loss = ndwi_before - ndwi_after
    water_loss_mask = water_loss > 0.1
    
    water_gain = ndwi_after - ndwi_before
    water_gain_mask = water_gain > 0.1
    
    total_pixels = water_loss_mask.size
    lost_pixels = np.sum(water_loss_mask)
    gained_pixels = np.sum(water_gain_mask)
    
    lost_percentage = (lost_pixels / total_pixels) * 100
    gained_percentage = (gained_pixels / total_pixels) * 100
    
    return {
        "ndwi_before": float(np.mean(ndwi_before)),
        "ndwi_after": float(np.mean(ndwi_after)),
        "water_loss_percentage": round(lost_percentage, 2),
        "water_gain_percentage": round(gained_percentage, 2),
        "water_changed": round(lost_percentage + gained_percentage, 2)
    }

def analyze_single_image(image_path):
    """Compute quick vegetation/water/structure/brightness proxies for one image."""
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Could not read the uploaded image")

    height, width = image.shape[:2]
    total_pixels = height * width

    blue = image[:, :, 0].astype(np.int16)
    green = image[:, :, 1].astype(np.int16)
    red = image[:, :, 2].astype(np.int16)

    # Vegetation proxy: excess green index
    excess_green = (2 * green) - red - blue
    vegetation_percentage = (np.count_nonzero(excess_green > 15) / total_pixels) * 100

    # Water proxy: NDWI-style index (same green/red-as-nir convention used
    # elsewhere in this module) rather than a raw "blue-dominant" threshold,
    # which misses turbid/muddy water that isn't visually blue.
    ndwi = calculate_ndwi(green.astype(np.float32), red.astype(np.float32))
    water_percentage = (np.count_nonzero(ndwi > 0) / total_pixels) * 100

    # Structure proxy: edge density
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 160)
    edge_density = (np.count_nonzero(edges) / total_pixels) * 100

    brightness = float(np.mean(gray))

    return {
        "vegetationPercentage": round(vegetation_percentage, 2),
        "waterPercentage": round(water_percentage, 2),
        "edgeDensity": round(edge_density, 2),
        "brightness": round(brightness, 2),
    }


def align_images(before, after):
    """Register `before` onto `after`'s frame via SIFT features + homography.

    Falls back to the unaligned (resized) image if there aren't enough
    reliable feature matches, so a low-texture image pair degrades gracefully
    instead of throwing during a live demo.
    """
    gray_before = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    gray_after = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)

    height, width = gray_after.shape

    try:
        sift = cv2.SIFT_create()
        kp_before, desc_before = sift.detectAndCompute(gray_before, None)
        kp_after, desc_after = sift.detectAndCompute(gray_after, None)

        if desc_before is None or desc_after is None:
            raise RuntimeError("Not enough visual features to align images")

        matcher = cv2.BFMatcher()
        matches = matcher.knnMatch(desc_before, desc_after, k=2)

        good_matches = [m for m, n in matches if len(matches) and m.distance < 0.7 * n.distance]

        if len(good_matches) < 10:
            raise RuntimeError("Not enough reliable feature matches to align images")

        points_before = np.float32(
            [kp_before[m.queryIdx].pt for m in good_matches]
        ).reshape(-1, 1, 2)
        points_after = np.float32(
            [kp_after[m.trainIdx].pt for m in good_matches]
        ).reshape(-1, 1, 2)

        homography, mask = cv2.findHomography(points_before, points_after, cv2.RANSAC, 5.0)

        if homography is None or mask is None:
            raise RuntimeError("Could not compute a reliable transformation")

        aligned_before = cv2.warpPerspective(before, homography, (width, height))

        valid_mask = cv2.warpPerspective(
            np.ones((before.shape[0], before.shape[1]), dtype=np.uint8) * 255,
            homography,
            (width, height),
        )
        valid_mask = cv2.erode(valid_mask, np.ones((15, 15), np.uint8), iterations=1)

        return aligned_before, valid_mask, True

    except Exception:
        # Fall back to a plain resize-based comparison (previous behavior).
        return before, np.ones((height, width), dtype=np.uint8) * 255, False


def generate_visualizations(before_path, after_path, job_dir):
    """Generate all visualizations with real calculations"""
    before = cv2.imread(before_path)
    after = cv2.imread(after_path)

    if before is None or after is None:
        raise ValueError(f"Could not load images")

    height = min(before.shape[0], after.shape[0])
    width = min(before.shape[1], after.shape[1])
    before = cv2.resize(before, (width, height))
    after = cv2.resize(after, (width, height))

    aligned_before, valid_mask, aligned_ok = align_images(before, after)

    alignment_overlay = cv2.addWeighted(aligned_before, 0.5, after, 0.5, 0)
    alignment_path = os.path.join(job_dir, "alignment_overlay.jpg")
    cv2.imwrite(alignment_path, alignment_overlay)

    # Use the registered image for every downstream comparison so change
    # detection isn't picking up misalignment as "change".
    before = aligned_before

    before_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    after_gray = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(before_gray, after_gray)
    # Warping `before` onto `after`'s frame leaves black, uncovered border
    # pixels wherever the source image doesn't reach. Zero those out here so
    # they don't register as (false) large differences downstream, in the
    # raw diff, the heatmap's normalization range, and the change mask.
    diff[valid_mask == 0] = 0

    diff_path = os.path.join(job_dir, "raw_difference.jpg")
    cv2.imwrite(diff_path, diff)

    _, mask = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    mask_rgba = np.zeros((height, width, 4), dtype=np.uint8)
    mask_rgba[:, :, 0] = 255
    mask_rgba[:, :, 1] = 0
    mask_rgba[:, :, 2] = 0
    mask_rgba[:, :, 3] = mask
    mask_path = os.path.join(job_dir, "change_mask.png")
    cv2.imwrite(mask_path, mask_rgba)
    
    overlay = after.copy()
    overlay[mask > 0] = [0, 0, 255]
    overlay_path = os.path.join(job_dir, "change_overlay.jpg")
    cv2.imwrite(overlay_path, overlay)
    
    heatmap_normalized = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
    heatmap_colored = cv2.applyColorMap(heatmap_normalized, cv2.COLORMAP_JET)
    heatmap_path = os.path.join(job_dir, "change_heatmap.jpg")
    cv2.imwrite(heatmap_path, heatmap_colored)
    
    regions_image = after.copy()
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    regions = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 100:
            x, y, w, h = cv2.boundingRect(contour)
            region_id = len(regions) + 1
            cv2.rectangle(regions_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(regions_image, f"#{region_id}", (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            regions.append({
                "id": region_id,
                "type": "Detected change",
                "confidence": 0.85,
                "area": int(area),
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
                "center_x": int(x + w/2),
                "center_y": int(y + h/2)
            })
    
    regions_path = os.path.join(job_dir, "change_regions.jpg")
    cv2.imwrite(regions_path, regions_image)
    
    total_pixels = mask.size
    changed_pixels = np.sum(mask > 0)
    changed_percentage, area_km2 = calculate_area_percentage(mask)
    
    detected_regions = len(regions)
    largest_region = max([r["area"] for r in regions]) if regions else 0
    
    before_red = before[:, :, 2].astype(np.float32)
    before_nir = before[:, :, 0].astype(np.float32)
    after_red = after[:, :, 2].astype(np.float32)
    after_nir = after[:, :, 0].astype(np.float32)
    
    ndvi_before = calculate_ndvi(before_nir, before_red)
    ndvi_after = calculate_ndvi(after_nir, after_red)
    
    return {
        "diff_path": diff_path,
        "mask_path": mask_path,
        "overlay_path": overlay_path,
        "heatmap_path": heatmap_path,
        "alignment_path": alignment_path,
        "regions_path": regions_path,
        "regions": regions,
        "detected_regions": detected_regions,
        "changed_percentage": changed_percentage,
        "area_km2": area_km2,
        "largest_region": largest_region,
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "ndvi_before": float(np.mean(ndvi_before)),
        "ndvi_after": float(np.mean(ndvi_after))
    }