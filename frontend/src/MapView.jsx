import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// The uploaded JPGs carry no embedded GPS/GeoTIFF metadata, so this renders
// an approximate reference location rather than a precisely geocoded scene.
// Said out loud in the UI rather than implied, in keeping with this project's
// own rule: computed numbers are exact, everything else says what it is.
const KNOWN_SCENES = [
  { match: /mumbai/i, label: "Mumbai, India", center: [19.076, 72.8777] },
  { match: /mahalaxmi/i, label: "Mahalaxmi, Mumbai, India", center: [18.9827, 72.8189] },
];

const DEFAULT_SCENE = { label: "Approximate demo location", center: [19.076, 72.8777] };

function resolveScene(hintText) {
  if (hintText) {
    const found = KNOWN_SCENES.find((scene) => scene.match.test(hintText));
    if (found) return found;
  }
  return DEFAULT_SCENE;
}

export default function MapView({ hintText }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const scene = resolveScene(hintText);

    const map = L.map(containerRef.current, {
      center: scene.center,
      zoom: 12,
      attributionControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    L.circle(scene.center, {
      radius: 1500,
      color: "#2563eb",
      fillColor: "#3b82f6",
      fillOpacity: 0.15,
    }).addTo(map);

    L.marker(scene.center).addTo(map).bindPopup(scene.label).openPopup();

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [hintText]);

  const scene = resolveScene(hintText);

  return (
    <div className="map-view">
      <div ref={containerRef} className="map-view-canvas" />
      <div className="map-view-caption">
        <strong>{scene.label}</strong>
        <span>
          Approximate reference location — the uploaded images carry no
          embedded GPS metadata, so this is illustrative, not a geocoded fix.
        </span>
      </div>
    </div>
  );
}
