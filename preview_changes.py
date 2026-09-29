"""Compare a regenerated GeoJSON with the published one and draw the changes on a map.

Prints a summary (for the CircleCI log) and writes a self-contained HTML map:
new points in green, removed points in red, unchanged points in grey.

Usage: python preview_changes.py PUBLISHED.geojson NEW.geojson MAP.html
"""

import html
import json
import sys
from collections import Counter
from pathlib import Path

STATUSES = ("added", "removed", "unchanged")
REMOVED_WARNING = (
    "{n} point(s) would be removed. The list is cumulative, so check the spreadsheet "
    "before approving. (An edited row shows up as its old version removed and its "
    "new version added, at the same spot.)"
)


def coordinates(feature: dict) -> list | None:
    """[lon, lat], or None when the spreadsheet row had no Latitude/Longitude."""
    return (feature.get("geometry") or {}).get("coordinates")


def load(path: str) -> tuple[str, Counter, dict]:
    """Return the layer name, a count of each distinct point, and each point's feature."""
    data = json.loads(Path(path).read_text())
    counts, features = Counter(), {}
    for f in data["features"]:
        coords = coordinates(f)
        # Round to ~1 cm so float noise from re-saving the spreadsheet isn't shown as a change
        lonlat = [round(c, 7) for c in coords] if coords else None
        key = json.dumps([f["properties"], lonlat], sort_keys=True)
        counts[key] += 1
        features.setdefault(key, {"properties": f["properties"], "geometry": f["geometry"]})
    return data.get("name", Path(path).stem), counts, features


def describe(point: dict) -> str:
    coords = coordinates(point)
    where = f"({coords[1]:.5f}, {coords[0]:.5f})" if coords else "(NO COORDINATES)"
    fields = " | ".join(str(v) for v in point["properties"].values())
    return f"{fields}  {where}"


def compare(published_path: str, new_path: str) -> dict:
    old_name, old, old_features = load(published_path)
    new_name, new, new_features = load(new_path)
    features = old_features | new_features
    groups = {"added": new - old, "removed": old - new, "unchanged": new & old}

    points = [
        {"status": status, **features[key]}
        for status in STATUSES
        for key in groups[status].elements()
    ]

    return {
        "old_name": old_name,
        "new_name": new_name,
        "old_total": old.total(),
        "new_total": new.total(),
        "counts": {s: groups[s].total() for s in STATUSES},
        "points": points,
    }


def print_summary(diff: dict) -> None:
    print(f"Published: {diff['old_name']} ({diff['old_total']} points)")
    print(f"New:       {diff['new_name']} ({diff['new_total']} points)")
    for status, sign in (("added", "+"), ("removed", "-")):
        changed = [p for p in diff["points"] if p["status"] == status]
        print(f"\n{len(changed)} {status} point(s)")
        for point in changed:
            print(f"  {sign} {describe(point)}")
    if not diff["counts"]["added"] and not diff["counts"]["removed"]:
        print("\nNo points were added or removed; there is nothing new to publish.")
    if diff["counts"]["removed"]:
        print(f"\nWARNING: {REMOVED_WARNING.format(n=diff['counts']['removed'])}")
    unmapped = [p for p in diff["points"] if p["status"] == "added" and not coordinates(p)]
    if unmapped:
        print(
            f"\nWARNING: {len(unmapped)} new row(s) have no Latitude/Longitude "
            "and won't appear on the map."
        )


def write_map(diff: dict, out_path: str) -> None:
    # Escape <, > and & so spreadsheet text can't close the <script> block early
    data = (
        json.dumps(diff)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    page = (
        MAP_TEMPLATE.replace("__TITLE__", html.escape(diff["new_name"]))
        .replace("__REMOVED_WARNING__", html.escape(REMOVED_WARNING))
        .replace("__DATA__", data)
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"\nMap written to {out}")


MAP_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Preview: __TITLE__</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
  integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<style>
  html, body { height: 100%; margin: 0; font: 14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; color: #1f2328; }
  #map { position: absolute; inset: 0; background: #dfe7ec; }
  #panel { position: absolute; z-index: 1000; top: 12px; left: 12px; width: 340px; max-height: calc(100% - 24px);
    overflow: auto; box-sizing: border-box; padding: 14px 16px; background: #fff; border-radius: 10px;
    box-shadow: 0 2px 14px rgba(0, 0, 0, .25); }
  #panel h1 { font-size: 16px; margin: 0 0 2px; }
  #panel .sub { margin: 0 0 10px; color: #59636e; font-size: 12px; }
  .counts { display: flex; gap: 14px; margin: 0 0 10px; padding: 0; list-style: none; font-weight: 600; }
  .dot { display: inline-block; width: 10px; height: 10px; margin-right: 5px; border-radius: 50%; border: 2px solid; vertical-align: -1px; }
  .added .dot, .dot.added { background: #2da44e; border-color: #1a7f37; }
  .removed .dot, .dot.removed { background: #ff8182; border-color: #a40e26; }
  .unchanged .dot, .dot.unchanged { background: #afb8c1; border-color: #6e7781; }
  #changes { margin: 0; padding: 0; list-style: none; border-top: 1px solid #d1d9e0; }
  #changes li { padding: 8px 2px; border-bottom: 1px solid #d1d9e0; cursor: pointer; }
  #changes li:hover { background: #f6f8fa; }
  #changes .when { font-weight: 600; }
  #changes .what { color: #59636e; font-size: 12px; }
  #changes li.unmapped { cursor: default; }
  #changes .warn { color: #9a6700; font-size: 12px; font-weight: 600; }
  .empty { margin: 8px 0; padding: 8px 10px; background: #fff8c5; border-radius: 6px; }
  .alert { margin: 0 0 10px; padding: 8px 10px; background: #ffebe9; border: 1px solid #ffcecb; border-radius: 6px; color: #82071e; }
  .hint { margin: 10px 0 0; color: #59636e; font-size: 12px; }
  .popup .item + .item { margin-top: 8px; padding-top: 8px; border-top: 1px solid #d1d9e0; }
  .popup dl { display: grid; grid-template-columns: auto 1fr; gap: 1px 8px; margin: 4px 0 0; }
  .popup dt { color: #59636e; }
  .popup dd { margin: 0; }
  @media (max-width: 640px) {
    #panel { top: auto; bottom: 12px; right: 12px; width: auto; max-height: 45%; }
  }
</style>
</head>
<body>
<div id="map"></div>
<aside id="panel">
  <h1>Akoakoa restoration update</h1>
  <p class="sub" id="sub"></p>
  <ul class="counts" id="counts"></ul>
  <p class="alert" id="removed-warning" hidden>__REMOVED_WARNING__</p>
  <ul id="changes"></ul>
  <p class="hint">To publish, approve the <b>hold-for-review</b> job in CircleCI. To discard, cancel the workflow.</p>
</aside>
<script type="application/json" id="data">__DATA__</script>
<script>
  const diff = JSON.parse(document.getElementById("data").textContent);
  const LABEL = { added: "New", removed: "Removed", unchanged: "Unchanged" };
  const STYLE = {
    added: { color: "#1a7f37", fillColor: "#2da44e", radius: 9, fillOpacity: 0.95 },
    removed: { color: "#a40e26", fillColor: "#ff8182", radius: 9, fillOpacity: 0.95 },
    unchanged: { color: "#6e7781", fillColor: "#afb8c1", radius: 5, fillOpacity: 0.6 },
  };
  const ORDER = ["added", "removed", "unchanged"];

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const mapped = (p) => Boolean(p.geometry && p.geometry.coordinates);
  const latLng = (p) => [p.geometry.coordinates[1], p.geometry.coordinates[0]];
  const placeKey = (p) => latLng(p).join(",");

  const map = L.map("map", { zoomControl: false });
  L.control.zoom({ position: "topright" }).addTo(map);
  const streets = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  const satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 19, attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics" },
  );

  // Several activities often share one spot, so each popup lists everything at that spot.
  const places = new Map();
  for (const p of diff.points.filter(mapped)) {
    if (!places.has(placeKey(p))) places.set(placeKey(p), []);
    places.get(placeKey(p)).push(p);
  }
  function popup(key) {
    const box = el("div", "popup");
    const here = [...places.get(key)].sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status));
    for (const p of here) {
      const item = el("div", "item " + p.status);
      const head = el("div");
      head.append(el("span", "dot " + p.status), el("strong", "", LABEL[p.status]));
      const dl = el("dl");
      for (const [k, v] of Object.entries(p.properties)) dl.append(el("dt", "", k), el("dd", "", v ?? ""));
      item.append(head, dl);
      box.append(item);
    }
    return box;
  }

  // Draw unchanged first so new and removed points sit on top; one marker per spot and status.
  const layers = {}, markers = {};
  for (const status of ["unchanged", "removed", "added"]) {
    layers[status] = L.layerGroup().addTo(map);
    for (const p of diff.points.filter((q) => q.status === status && mapped(q))) {
      const key = placeKey(p);
      if (markers[status + key]) continue;
      markers[status + key] = L.circleMarker(latLng(p), { weight: 2, ...STYLE[status] })
        .bindPopup(() => popup(key), { maxWidth: 320 })
        .addTo(layers[status]);
    }
  }
  const overlays = {};
  for (const status of ORDER) overlays[LABEL[status] + " (" + diff.counts[status] + ")"] = layers[status];
  L.control.layers({ Streets: streets, Satellite: satellite }, overlays, { position: "topright" }).addTo(map);

  // Side panel: counts, then every added/removed point (click to zoom to it).
  document.getElementById("sub").textContent =
    diff.new_name + " (" + diff.new_total + " points) vs. published " + diff.old_name + " (" + diff.old_total + ")";
  const counts = document.getElementById("counts");
  for (const status of ORDER) {
    const li = el("li", status);
    li.append(el("span", "dot"), document.createTextNode(diff.counts[status] + " " + LABEL[status].toLowerCase()));
    counts.append(li);
  }
  if (diff.counts.removed) {
    const warning = document.getElementById("removed-warning");
    warning.textContent = warning.textContent.replace("{n}", diff.counts.removed);
    warning.hidden = false;
  }
  const list = document.getElementById("changes");
  const changed = diff.points.filter((p) => p.status !== "unchanged");
  if (!changed.length) {
    list.replaceWith(el("p", "empty", "No points were added or removed, so there is nothing new to publish."));
  }
  for (const p of changed) {
    const li = el("li", p.status);
    const when = el("div", "when");
    when.append(el("span", "dot"), document.createTextNode(LABEL[p.status] + ": " + [p.properties.Date, p.properties.Location].filter(Boolean).join(" · ")));
    li.append(when, el("div", "what", [p.properties.Activity, p.properties.SpeciesInfo, p.properties.Notes].filter(Boolean).join(" · ")));
    list.append(li);
    if (!mapped(p)) {
      li.classList.add("unmapped");
      li.append(el("div", "warn", "No Latitude/Longitude in the spreadsheet, so this row isn't on the map."));
      continue;
    }
    li.addEventListener("click", () => {
      fitTo([latLng(p)], Math.max(map.getZoom(), 15));
      markers[p.status + placeKey(p)].openPopup();
    });
  }

  // Zoom to the changes (or to everything when nothing changed), keeping them out from under the panel.
  function fitTo(latLngs, maxZoom) {
    const size = map.getSize(), box = document.getElementById("panel").getBoundingClientRect();
    const docked = box.top > size.y / 3;  // narrow screens dock the panel at the bottom
    map.fitBounds(L.latLngBounds(latLngs), {
      maxZoom,
      paddingTopLeft: [docked ? 40 : box.right + 40, 40],
      paddingBottomRight: [40, docked ? size.y - box.top + 40 : 40],
    });
  }
  const focus = changed.some(mapped) ? changed.filter(mapped) : diff.points.filter(mapped);
  if (focus.length) fitTo(focus.map(latLng), 14);
  else map.setView([19.6, -155.95], 9);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    result = compare(sys.argv[1], sys.argv[2])
    print_summary(result)
    write_map(result, sys.argv[3])
