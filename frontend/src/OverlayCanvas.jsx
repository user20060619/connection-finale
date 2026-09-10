import { useEffect, useRef, useState } from "react";

// Draws the change mask and bounding boxes on top of the source image
// client-side, from the mask image + region coordinates the API already
// returns, instead of only showing the backend's pre-rendered JPGs. Lets us
// toggle the mask and highlight one region on hover without a round trip to
// the server.
export default function OverlayCanvas({ imageSrc, maskSrc, regions = [] }) {
  const canvasRef = useRef(null);
  const [hoveredId, setHoveredId] = useState(null);
  const [naturalSize, setNaturalSize] = useState(null);
  const [showMask, setShowMask] = useState(true);
  const loadedImages = useRef({});

  function loadImage(src) {
    return new Promise((resolve, reject) => {
      if (!src) return resolve(null);
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = src;
    });
  }

  useEffect(() => {
    if (!imageSrc) return;
    let cancelled = false;

    Promise.all([loadImage(imageSrc), loadImage(maskSrc)]).then(
      ([baseImage, maskImage]) => {
        if (cancelled || !baseImage) return;
        loadedImages.current = { baseImage, maskImage };
        setNaturalSize({ width: baseImage.naturalWidth, height: baseImage.naturalHeight });

        const canvas = canvasRef.current;
        if (!canvas) return;
        canvas.width = baseImage.naturalWidth;
        canvas.height = baseImage.naturalHeight;

        redraw(hoveredId);
      }
    );

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageSrc, maskSrc, regions]);

  useEffect(() => {
    redraw(hoveredId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hoveredId, showMask]);

  function redraw(activeId) {
    const canvas = canvasRef.current;
    const { baseImage, maskImage } = loadedImages.current;
    if (!canvas || !baseImage) return;

    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(baseImage, 0, 0);

    if (showMask && maskImage) {
      ctx.drawImage(maskImage, 0, 0, canvas.width, canvas.height);
    }

    draw(ctx, regions, activeId);
  }

  function draw(ctx, regionList, activeId) {
    regionList.forEach((region) => {
      const isActive = region.id === activeId;
      ctx.strokeStyle = isActive ? "#facc15" : "#22c55e";
      ctx.lineWidth = isActive ? 4 : 2;
      ctx.strokeRect(region.x, region.y, region.width, region.height);

      const label = `#${region.id}`;
      ctx.font = "bold 20px sans-serif";
      const textWidth = ctx.measureText(label).width;
      ctx.fillStyle = isActive ? "#facc15" : "#22c55e";
      ctx.fillRect(region.x, Math.max(region.y - 26, 0), textWidth + 10, 24);
      ctx.fillStyle = "#0b1220";
      ctx.fillText(label, region.x + 5, Math.max(region.y - 8, 18));
    });
  }

  function handleMouseMove(event) {
    if (!naturalSize) return;
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const scaleX = naturalSize.width / rect.width;
    const scaleY = naturalSize.height / rect.height;
    const x = (event.clientX - rect.left) * scaleX;
    const y = (event.clientY - rect.top) * scaleY;

    const hit = regions.find(
      (region) =>
        x >= region.x &&
        x <= region.x + region.width &&
        y >= region.y &&
        y <= region.y + region.height
    );
    setHoveredId(hit ? hit.id : null);
  }

  if (!imageSrc) {
    return (
      <div className="visualization-empty">
        <strong>Overlay unavailable</strong>
        <span>No source image to draw regions on yet.</span>
      </div>
    );
  }

  const hoveredRegion = regions.find((region) => region.id === hoveredId);

  return (
    <div className="overlay-canvas-wrap">
      {maskSrc && (
        <label className="overlay-canvas-mask-toggle">
          <input
            type="checkbox"
            checked={showMask}
            onChange={(event) => setShowMask(event.target.checked)}
          />
          Show change mask
        </label>
      )}
      <canvas
        ref={canvasRef}
        className="overlay-canvas"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredId(null)}
      />
      {hoveredRegion && (
        <div className="overlay-canvas-tooltip">
          <strong>Region #{hoveredRegion.id}</strong>
          <span>{hoveredRegion.area?.toLocaleString()} px area</span>
        </div>
      )}
    </div>
  );
}
