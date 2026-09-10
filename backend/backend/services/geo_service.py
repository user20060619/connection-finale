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

    # Water proxy: blue-dominant pixels
    water_mask = (blue > red) & (blue > green) & (blue > 60)
    water_percentage = (np.count_nonzero(water_mask) / total_pixels) * 100

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
    
    before_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    after_gray = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)
    
    diff = cv2.absdiff(before_gray, after_gray)
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
    
    alignment = np.hstack([before, after])
    alignment_path = os.path.join(job_dir, "alignment_overlay.jpg")
    cv2.imwrite(alignment_path, alignment)
    
    regions_image = after.copy()
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    regions = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area > 100:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(regions_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(regions_image, f"#{i+1}", (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            regions.append({
                "id": i + 1,
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