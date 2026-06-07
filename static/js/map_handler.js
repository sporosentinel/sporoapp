// MapLibre + PMTiles integration for Offline-First mapping

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize PMTiles protocol in MapLibre GL
    if (window.pmtiles) {
        let protocol = new pmtiles.Protocol();
        maplibregl.addProtocol("pmtiles", protocol.tile);
    } else {
        console.warn("PMTiles library not loaded; falling back to standard raster/vector tile schemas.");
    }

    // 2. Initialize Farmer Local Map (Centered on regional hub coords)
    // High-humidity Coastal: Lat 18.97, Lon 72.82 (Mumbai region)
    // Aspergillus-prone South: Lat 13.08, Lon 80.27 (Chennai region)
    const storedRegion = localStorage.getItem("sporo_region") || "High-humidity Coastal";
    let mapCenter = [72.82, 18.97]; // default coastal
    if (storedRegion === "Aspergillus-prone South") {
        mapCenter = [80.27, 13.08];
    } else if (storedRegion === "Northern Grain Belt") {
        mapCenter = [76.77, 30.73];
    } else if (storedRegion === "Western Drylands") {
        mapCenter = [70.90, 26.91];
    }

    const map = new maplibregl.Map({
        container: 'map',
        style: {
            version: 8,
            sources: {
                // OpenStreetMap raster fallback
                'osm-raster': {
                    type: 'raster',
                    tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                    tileSize: 256,
                    attribution: '&copy; OpenStreetMap contributors'
                },
                // Offline Packaged Vector Region Source using PMTiles
                'packaged-region': {
                    type: 'vector',
                    url: 'pmtiles:///static/regional_map.pmtiles'
                }
            },
            layers: [
                {
                    id: 'raster-basemap',
                    type: 'raster',
                    source: 'osm-raster',
                    layout: {
                        visibility: 'visible'
                    }
                }
            ]
        },
        center: mapCenter,
        zoom: 9
    });

    map.addControl(new maplibregl.NavigationControl());

    // 3. Download Offline Map tiles (PMTiles package)
    const downloadBtn = document.getElementById("download-tiles-btn");
    if (downloadBtn) {
        downloadBtn.addEventListener("click", () => {
            downloadBtn.disabled = true;
            downloadBtn.textContent = "Caching Vector Regions...";
            
            // Trigger fetch of PMTiles file to store it in cache
            fetch("/static/regional_map.pmtiles")
                .then(res => {
                    if (res.ok) {
                        return caches.open("sporo-cache-v1").then(cache => {
                            cache.put("/static/regional_map.pmtiles", res);
                            downloadBtn.textContent = "Downloaded (Offline Available)";
                        });
                    } else {
                        throw new Error("PMTiles asset not found on server");
                    }
                })
                .catch(err => {
                    console.error("Vector map caching failed", err);
                    downloadBtn.textContent = "Failed. Dynamic Cache Active";
                    downloadBtn.disabled = false;
                });
        });
    }

    // 4. Load local regional risk overlay polygons/markers
    let localOverlays = [];
    const overlayBtn = document.getElementById("load-risk-overlay-btn");
    
    if (overlayBtn) {
        overlayBtn.addEventListener("click", () => {
            loadLocalRiskOverlay(map, mapCenter, storedRegion);
        });
    }

    // Load overlay on startup automatically
    map.on('load', () => {
        loadLocalRiskOverlay(map, mapCenter, storedRegion);
    });
});

// Render local polygons on MapLibre indicating microclimate hazard levels
function loadLocalRiskOverlay(map, center, regionName) {
    // Generate risk coordinates around center
    const lng = center[0];
    const lat = center[1];
    
    // Set colors based on region risk
    let riskColor = "#ef4444"; // Red for South
    let riskLevel = "Critical (Aspergillus)";
    if (regionName.includes("Coastal")) {
        riskColor = "#f59e0b"; // Orange/Yellow
        riskLevel = "Caution (Penicillium)";
    } else if (regionName.includes("Northern")) {
        riskColor = "#10b981"; // Green
        riskLevel = "Safe (Low Risk)";
    } else {
        riskColor = "#84cc16"; // Monitor
        riskLevel = "Monitor (Drylands)";
    }

    // Add source and layers for risk polygons
    const sourceId = 'local-risk-poly';
    if (map.getSource(sourceId)) {
        map.removeLayer('risk-poly-layer');
        map.removeLayer('risk-border-layer');
        map.removeSource(sourceId);
    }

    // Draw a circular polygon surrounding the region center
    const polygonGeoJSON = createGeoJSONCircle(center, 4.0); // 4km radius
    
    map.addSource(sourceId, {
        type: 'geojson',
        data: polygonGeoJSON
    });

    map.addLayer({
        id: 'risk-poly-layer',
        type: 'fill',
        source: sourceId,
        layout: {},
        paint: {
            'fill-color': riskColor,
            'fill-opacity': 0.35
        }
    });

    map.addLayer({
        id: 'risk-border-layer',
        type: 'line',
        source: sourceId,
        layout: {},
        paint: {
            'line-color': riskColor,
            'line-width': 2
        }
    });

    // Fly to center
    map.flyTo({ center: center, zoom: 11 });

    // Add HTML Popup Marker indicating storage bins
    const el = document.createElement('div');
    el.style.width = '16px';
    el.style.height = '16px';
    el.style.borderRadius = '50%';
    el.style.background = 'white';
    el.style.border = '3px solid ' + riskColor;
    el.style.cursor = 'pointer';
    el.style.pointerEvents = 'auto'; // Enable mouse/pointer click captures

    const popup = new maplibregl.Popup({ offset: 15 })
        .setHTML(`<strong>Silo Region Hub</strong><br>Status: ${riskLevel}`);

    const marker = new maplibregl.Marker({ element: el })
        .setLngLat(center)
        .setPopup(popup)
        .addTo(map);

    // Direct event listener to toggle popup window on click
    el.addEventListener('click', (e) => {
        e.stopPropagation();
        marker.togglePopup();
    });
}

// Generate GeoJSON coordinate array representing a circle
function createGeoJSONCircle(center, radiusKm, points = 64) {
    const coords = {
        latitude: center[1],
        longitude: center[0]
    };

    const km = radiusKm;
    const ret = [];
    const distanceX = km / (111.32 * Math.cos(coords.latitude * Math.PI / 180));
    const distanceY = km / 110.57;

    for (let i = 0; i < points; i++) {
        const theta = (i / points) * (2 * Math.PI);
        const x = distanceX * Math.cos(theta);
        const y = distanceY * Math.sin(theta);
        ret.push([coords.longitude + x, coords.latitude + y]);
    }
    ret.push(ret[0]); // Close polygon

    return {
        type: 'Feature',
        geometry: {
            type: 'Polygon',
            coordinates: [ret]
        }
    };
}
