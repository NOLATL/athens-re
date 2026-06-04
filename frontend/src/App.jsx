import { useState, useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, CircleMarker, GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

// Fix default marker icon paths broken by Vite bundling
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL("leaflet/dist/images/marker-icon-2x.png", import.meta.url).href,
  iconUrl: new URL("leaflet/dist/images/marker-icon.png", import.meta.url).href,
  shadowUrl: new URL("leaflet/dist/images/marker-shadow.png", import.meta.url).href,
});

const COLORS = {
  bg: "#f4f6f8",
  card: "#ffffff",
  cardHover: "#f8f9fa",
  accent: "#8b5cf6",
  accentDim: "#7c3aed",
  green: "#16a34a",
  red: "#dc2626",
  orange: "#ea580c",
  blue: "#2563eb",
  text: "#111827",
  textDim: "#6b7280",
  border: "#e5e7eb",
  highlight: "#f9fafb",
};

const tabs = [
  { id: "map", label: "📍 Property Map" },
  { id: "overview", label: "Market Overview" },
  { id: "cashflow", label: "Cash Flow Calculator" },
  { id: "development", label: "Development Intel" },
  { id: "strategy", label: "Economics" },
];

const PROPERTIES = [
  {
    id: 1,
    address: "122 Park Ridge Ct, Athens 30605",
    price: "$305,000",
    type: "Duplex — 4BR/2BA",
    property_type: "Multi-Family (2-4 Unit)",
    beds: 4,
    sqft: 1800,
    county: "clarke",
    confidence: "high",
    rent: "$2,000/mo (est. $1,000/side)",
    why: "Best entry-level cash flow play on the market. One side freshly updated (new LVP, granite countertops) and VACANT — you set the rent. Other side tenant-occupied for immediate income. Near UGA, downtown, and Loop 10. At $305K with 25% down, monthly mortgage ~$1,450. Two sides at $1,000 each = positive cash flow from day one.",
    url: "https://www.redfin.com/city/36057/GA/Athens-Clarke/multi-family-homes-for-sale",
    lat: 33.934262,
    lng: -83.340972,
  },
  {
    id: 2,
    address: "121-123 Ashmore Ct, Athens 30601",
    price: "$255,000",
    type: "Duplex — 4BR/4BA",
    property_type: "Multi-Family (2-4 Unit)",
    beds: 4,
    sqft: 1600,
    county: "clarke",
    confidence: "high",
    rent: "$1,800–2,000/mo combined (est.)",
    why: "Lowest-priced multifamily in Athens right now. North Athens location. At $255K the price-to-rent ratio is the best you'll find. Needs in-person inspection to confirm condition. If it checks out, the cash flow math works even at 6.5% rates with conservative rent assumptions.",
    url: "https://www.homes.com/athens-ga/multi-family-homes-for-sale/",
    lat: 33.987887,
    lng: -83.361785,
  },
  {
    id: 3,
    address: "150 Creekwood Dr, Athens 30606",
    price: "$435,000",
    type: "Triplex — 3× 2BR/1BA (3,700 sqft)",
    property_type: "Multi-Family (2-4 Unit)",
    beds: 6,
    sqft: 3700,
    county: "clarke",
    confidence: "high",
    rent: "$3,100/mo (current leases)",
    why: "Highest income property available. Three 2BR/1BA units generating $3,100/mo with all leases secured through July 2026. Basement unit includes private garage. $37,200/yr gross rent on $435K purchase = ~6.5% gross yield. Day-one cash flow with zero lease-up risk. West Athens near Loop 10.",
    url: "https://www.movoto.com/athens-ga/multi-family/",
    lat: 33.967046,
    lng: -83.445743,
  },
  {
    id: 4,
    address: "230 Rustwood Dr, Athens 30606",
    price: "$271,000",
    type: "Duplex",
    property_type: "Multi-Family (2-4 Unit)",
    beds: 4,
    sqft: 1500,
    county: "clarke",
    confidence: "medium",
    rent: "~$1,800–2,000/mo (est. $1,000/side)",
    why: "Listed on Compass. West Athens / Normaltown area — near planned Middle Oconee Greenway expansion. 11-acre parcel is unusual and adds long-term land value. Confirm unit layout, current rent roll, and exact asking price. If rents are near $1,000/side, cap rate could exceed 6%.",
    url: "https://www.compass.com/homes-for-sale/athens-ga/multi-family/",
    lat: 33.98997,
    lng: -83.470228,
  },
  {
    id: 5,
    address: "123 Garden Ln, Athens 30606",
    price: "$275,000",
    type: "SFH — 3BR/2BA",
    property_type: "Single Family Residential",
    beds: 3,
    sqft: 1400,
    county: "clarke",
    confidence: "medium",
    rent: "$1,650–1,900/mo",
    why: "Turnkey investment near UGA Vet Med Teaching Hospital, Hwy 316, and downtown. Updated kitchen and baths, hardwood + tile, deck. Advertised as investment property. Strong rental demand from vet school and grad students. Confirm current asking price and whether tenant-occupied.",
    url: "https://www.homes.com/athens-ga/",
    lat: 33.920168,
    lng: -83.382369,
  },
  {
    id: 6,
    address: "250 Little St #D106, Athens 30605",
    price: "$205,000",
    type: "Condo — 2BR/1BA (795 sqft)",
    property_type: "Condo",
    beds: 2,
    sqft: 795,
    county: "clarke",
    confidence: "medium",
    rent: "$1,050–1,200/mo",
    why: "Lowest absolute price point at $205K. One mile from Sanford Stadium, near Firefly Trail and Botanical Gardens. CRITICAL: verify HOA/condo fees — if monthly dues exceed $200, cash flow gets very tight. Best for owner-occupant house-hack strategy or if HOA is low. Not ideal for pure investment if fees are high.",
    url: "https://www.redfin.com/city/36057/GA/Athens-Clarke/multi-family-homes-for-sale",
    lat: 33.949427,
    lng: -83.365749,
  },
  {
    id: 7,
    address: "1020 Deni Ct, Bogart 30622 (Oconee Co.)",
    price: "$500,000",
    type: "4-Unit Multifamily — 7BR/7.5BA",
    property_type: "Multi-Family (5+ Unit)",
    beds: 7,
    sqft: 4200,
    county: "oconee",
    confidence: "speculative",
    rent: "Fully occupied (amounts TBD)",
    why: "Rare Oconee County multifamily — almost never comes to market. Zoned for top-rated North Oconee schools (Hodges Mill Rd). All units occupied. Oconee's higher price point means this is more of an appreciation play than a cash flow winner. Long-term value in one of the strongest school districts in Georgia. Confirm asking price.",
    url: "https://www.redfin.com/city/36057/GA/Athens-Clarke/multi-family-homes-for-sale",
    lat: 33.899998,
    lng: -83.469155,
  },
  {
    id: 8,
    address: "8420 Macon Hwy, Athens 30606",
    price: "$500,000",
    type: "Duplex + 11 Acres on US 441 Corridor",
    property_type: "Multi-Family (2-4 Unit)",
    beds: 4,
    sqft: 2200,
    county: "oconee",
    confidence: "speculative",
    rent: "Current duplex income + commercial upside",
    why: "This is a corridor growth bet, not a pure cash-flow play. 11 acres directly on US 441 between Athens Academy and Watkinsville. Adjacent property already rezoned for office. Path of progress: Oconee Mercantile mixed-use project, Christian Brothers Automotive, and other commercial development emerging. Buy the income + land position while the corridor develops. Highest risk, highest upside on this list.",
    url: "https://www.compass.com/homes-for-sale/athens-ga/multi-family/",
    lat: 33.899762,
    lng: -83.408538,
  },
  {
    id: 9,
    address: "2019 S Lumpkin St, Athens 30606",
    price: "$550,000",
    type: "Duplex — Five Points",
    property_type: "Multi-Family (2-4 Unit)",
    beds: 4,
    sqft: 2000,
    county: "clarke",
    confidence: "speculative",
    rent: "$2,400–2,800/mo (premium location)",
    why: "Premium Five Points location — walking distance to UGA, Sanford Stadium, and downtown. Five Points has the highest median SFH price in Athens ($955K). At $550K this is a tough cash-flow play at current rates, but the neighborhood appreciation trend is the strongest in Athens. Best as a 5-10 year hold for equity growth rather than immediate cash flow.",
    url: "https://www.compass.com/homes-for-sale/athens-ga/multi-family/",
    lat: 33.932243,
    lng: -83.39202,
  },
];

// ── Shared components ────────────────────────────────────────────────────────

function Badge({ children, color = COLORS.accent }) {
  return (
    <span style={{ background: color + "18", color, padding: "3px 10px", borderRadius: "4px", fontSize: "11px", fontWeight: 600, letterSpacing: "0.5px", textTransform: "uppercase", border: `1px solid ${color}30` }}>
      {children}
    </span>
  );
}

function StatCard({ label, value, sub, trend }) {
  const trendColor =
    trend && (trend.startsWith("+") || trend.startsWith("↑")) ? COLORS.green
    : trend && (trend.startsWith("-") || trend.startsWith("↓")) ? COLORS.red
    : COLORS.textDim;
  return (
    <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "18px", flex: "1 1 160px", minWidth: 0 }}>
      <div style={{ fontSize: "11px", color: COLORS.textDim, fontWeight: 600, letterSpacing: "0.8px", textTransform: "uppercase", marginBottom: "8px" }}>{label}</div>
      <div style={{ fontSize: "26px", fontWeight: 700, color: COLORS.text }}>
        {value}
        {trend && <span style={{ fontSize: "13px", fontWeight: 600, marginLeft: "8px", color: trendColor }}>{trend}</span>}
      </div>
      {sub && <div style={{ fontSize: "12px", color: COLORS.textDim, marginTop: "4px" }}>{sub}</div>}
    </div>
  );
}

// ── Map helpers ──────────────────────────────────────────────────────────────

const PROP_TYPE_OPTIONS = [
  { key: "all",        label: "All Types" },
  { key: "multifamily", label: "Multi-Family" },
  { key: "sfh",        label: "Single Family" },
  { key: "condo",      label: "Condo / Townhouse" },
  { key: "distressed", label: "🔴 Distressed Parcels" },
];

function matchesPropType(p, filter) {
  if (filter === "all") return true;
  const t = (p.property_type || p.type || "").toLowerCase();
  if (filter === "multifamily") return t.includes("multi") || t.includes("duplex") || t.includes("triplex") || t.includes("quadplex");
  if (filter === "sfh")         return t.includes("single family") || t.includes("sfh");
  if (filter === "condo")       return t.includes("condo") || t.includes("townhouse");
  return true;
}

// Distressed parcel circle colors by distress score
function distressColor(score) {
  if (score >= 70) return "#ef4444"; // critical
  if (score >= 50) return "#fb923c"; // high
  return "#facc15";                  // watch list
}

// ACC zoning color palette — keyed by zone prefix
const ZONE_COLORS = {
  "RS":  { fill: "#4ade80", label: "Single-Family Residential" },
  "RM":  { fill: "#86efac", label: "Multi-Family Residential" },
  "RR":  { fill: "#bbf7d0", label: "Rural Residential" },
  "MU":  { fill: "#60a5fa", label: "Mixed Use" },
  "CN":  { fill: "#f59e0b", label: "Neighborhood Commercial" },
  "CB":  { fill: "#f97316", label: "Community Business" },
  "CS":  { fill: "#ef4444", label: "Shopping Center" },
  "CH":  { fill: "#dc2626", label: "Highway Commercial" },
  "LI":  { fill: "#a78bfa", label: "Light Industrial" },
  "HI":  { fill: "#7c3aed", label: "Heavy Industrial" },
  "G":   { fill: "#94a3b8", label: "Government / Public" },
  "P":   { fill: "#64748b", label: "Parks / Open Space" },
  "AG":  { fill: "#d97706", label: "Agriculture" },
};

function zoningStyle(feature) {
  const zone = (feature.properties?.CurrentZn || "").trim();
  const prefix = zone.replace(/[^A-Z-]/g, "").split("-")[0];
  const cfg = ZONE_COLORS[prefix] || ZONE_COLORS[zone] || { fill: "#94a3b8" };
  return {
    fillColor: cfg.fill,
    fillOpacity: 0.35,
    color: cfg.fill,
    weight: 0.5,
    opacity: 0.6,
  };
}

// ── Census choropleth helpers ─────────────────────────────────────────────────

const CENSUS_VARS = {
  median_household_income: {
    label: "Median Income",
    format: (v) => `$${(v / 1000).toFixed(0)}K`,
    colors: ["#ffffcc", "#a1dab4", "#41b6c4", "#2c7fb8", "#253494"],
  },
  renter_pct: {
    label: "Renter %",
    format: (v) => `${v.toFixed(0)}%`,
    colors: ["#f1eef6", "#d4b9da", "#c994c7", "#df65b0", "#91003f"],
  },
  median_gross_rent: {
    label: "Median Rent",
    format: (v) => `$${v.toLocaleString()}`,
    colors: ["#ffffd4", "#fed98e", "#fe9929", "#d95f0e", "#993404"],
  },
  median_home_value: {
    label: "Home Value",
    format: (v) => `$${(v / 1000).toFixed(0)}K`,
    colors: ["#eff3ff", "#bdd7e7", "#6baed6", "#2171b5", "#084594"],
  },
  vacancy_rate: {
    label: "Vacancy Rate",
    format: (v) => `${v.toFixed(1)}%`,
    colors: ["#fff5eb", "#fee6ce", "#fdd0a2", "#fdae6b", "#d94801"],
  },
  median_age: {
    label: "Median Age",
    format: (v) => `${typeof v === "number" ? v.toFixed(1) : v} yrs`,
    colors: ["#f7fbff", "#c6dbef", "#9ecae1", "#4292c6", "#08519c"],
  },
};

function computeQuintileBreaks(features, varName) {
  const vals = features
    .map((f) => f.properties?.[varName])
    .filter((v) => v !== null && v !== undefined && !isNaN(v))
    .sort((a, b) => a - b);
  if (vals.length === 0) return [];
  const breaks = [];
  for (let i = 0; i <= 5; i++) {
    const idx = Math.floor(((vals.length - 1) * i) / 5);
    breaks.push(vals[idx]);
  }
  return breaks; // [min, q20, q40, q60, q80, max]
}

function censusColorForValue(value, breaks, colors) {
  if (value === null || value === undefined || breaks.length < 2) return "#94a3b8";
  for (let i = 0; i < colors.length; i++) {
    if (value <= breaks[i + 1]) return colors[i];
  }
  return colors[colors.length - 1];
}

function makeIcon(p, rank) {
  const color = COLORS.accent;
  return L.divIcon({
    className: "",
    html: `<div style="width:28px;height:28px;border-radius:50%;background:${color};border:3px solid #fff;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;color:#fff;box-shadow:0 2px 6px rgba(0,0,0,0.3);cursor:pointer;">${rank ?? p.id}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  });
}

function MapResizer({ trigger }) {
  const map = useMap();
  useEffect(() => {
    setTimeout(() => map.invalidateSize(), 50);
  }, [trigger, map]);
  return null;
}

function MapFlyTo({ selected, properties }) {
  const map = useMap();
  useEffect(() => {
    if (!selected) return;
    const p = properties.find((x) => x.id === selected);
    if (p) map.flyTo([p.lat, p.lng], 15, { animate: true, duration: 0.8 });
  }, [selected, properties, map]);
  return null;
}

// ── Tab: Property Map ────────────────────────────────────────────────────────

function PropertyMap({ onLoadCalculator }) {
  const [properties, setProperties] = useState(PROPERTIES);
  const [listingsLoading, setListingsLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [filter, setFilter] = useState("sfh");
  const [showDistressed, setShowDistressed] = useState(false);
  const [dismissed, setDismissed] = useState(() => {
    try { return new Set(JSON.parse(localStorage.getItem("re_dismissed") || "[]")); }
    catch { return new Set(); }
  });
  const [showDismissed, setShowDismissed] = useState(false);
  const [distressedParcels, setDistressedParcels] = useState([]);
  const [selectedDistressed, setSelectedDistressed] = useState(null);
  const [showZoning, setShowZoning] = useState(false);
  const [zoningData, setZoningData] = useState(null);
  const [zoningLoading, setZoningLoading] = useState(false);
  const [showCensus, setShowCensus] = useState(false);
  const [censusData, setCensusData] = useState(null);
  const [censusLoading, setCensusLoading] = useState(false);
  const [censusVar, setCensusVar] = useState("median_household_income");
  const [censusBreaks, setCensusBreaks] = useState([]);
  const [topN, setTopN] = useState(25);
  const [cashFlowCache, setCashFlowCache] = useState({});
  const [compsCache, setCompsCache] = useState({});
  const [scoreCache, setScoreCache] = useState({});
  const [trafficCache, setTrafficCache] = useState({});
  const markerRefs = useRef({});
  const cardRefs = useRef({});
  const fetchedComps = useRef(new Set());
  const fetchedTraffic = useRef(new Set());

  const dismissProperty = (id) => {
    const next = new Set(dismissed);
    next.add(String(id));
    setDismissed(next);
    localStorage.setItem("re_dismissed", JSON.stringify([...next]));
    if (selected === id) setSelected(null);
  };
  const undismissProperty = (id) => {
    const next = new Set(dismissed);
    next.delete(String(id));
    setDismissed(next);
    localStorage.setItem("re_dismissed", JSON.stringify([...next]));
  };

  // Fetch distressed parcels from API when layer is toggled on
  useEffect(() => {
    if (!showDistressed || distressedParcels.length > 0) return;
    fetch(`${API_URL}/api/distressed-parcels?min_score=25&limit=200`)
      .then((r) => r.json())
      .then((data) => {
        const features = data.features || [];
        setDistressedParcels(features);
      })
      .catch(() => {
        setDistressedParcels([]);
      });
  }, [showDistressed]);

  // Fetch zoning GeoJSON when layer is toggled on (fetch once, cache in state)
  useEffect(() => {
    if (!showZoning || zoningData !== null) return;
    setZoningLoading(true);
    fetch(`${API_URL}/api/zoning-geojson`)
      .then((r) => {
        if (!r.ok) return null;
        return r.json();
      })
      .then((data) => {
        setZoningData(data && data.type === "FeatureCollection" ? data : null);
        setZoningLoading(false);
      })
      .catch(() => {
        setZoningData(null);
        setZoningLoading(false);
      });
  }, [showZoning]);

  // Fetch census GeoJSON when layer is toggled on (fetch once, cache in state)
  useEffect(() => {
    if (!showCensus || censusData !== null) return;
    setCensusLoading(true);
    fetch(`${API_URL}/api/census-tracts`)
      .then((r) => {
        if (!r.ok) return null;
        return r.json();
      })
      .then((data) => {
        setCensusData(data && data.type === "FeatureCollection" ? data : null);
        setCensusLoading(false);
      })
      .catch(() => {
        setCensusData(null);
        setCensusLoading(false);
      });
  }, [showCensus]);

  // Fetch live listings from API on mount; fall back to seed data if unavailable
  useEffect(() => {
    fetch(`${API_URL}/api/properties`)
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setProperties(data);
        }
        setListingsLoading(false);
      })
      .catch(() => setListingsLoading(false));
  }, []);

  // Recompute quintile breaks when census data or selected variable changes
  useEffect(() => {
    if (!censusData) return;
    const breaks = computeQuintileBreaks(censusData.features || [], censusVar);
    setCensusBreaks(breaks);
  }, [censusData, censusVar]);

  useEffect(() => {
    if (!selected) return;
    const ref = markerRefs.current[selected];
    if (ref) ref.openPopup();
  }, [selected]);

  // Populate cash flow cache from pre-computed property data when a card is opened
  useEffect(() => {
    if (!selected || cashFlowCache[selected]) return;
    const p = properties.find((x) => x.id === selected);
    if (!p) return;

    if (p.cash_flow && p.rent_estimate) {
      setCashFlowCache((prev) => ({
        ...prev,
        [selected]: { loading: false, data: { rent_estimate: p.rent_estimate, cash_flow: p.cash_flow } },
      }));
      return;
    }

    // Fall back to API when pre-computed data isn't available
    const price = parseFloat((p.price || "").replace(/[$,~]/g, "").match(/[\d.]+/)?.[0] || "");
    if (!price || isNaN(price)) return;
    setCashFlowCache((prev) => ({ ...prev, [selected]: { loading: true } }));
    const params = new URLSearchParams({
      price, lat: p.lat, lng: p.lng,
      beds: p.beds || 2, sqft: p.sqft || 0,
      property_type: p.property_type || "",
      county: p.county || "clarke",
      hoa_monthly: p.hoa_monthly || 0,
      address: p.address || "",
    });
    fetch(`${API_URL}/api/cash-flow?${params}`)
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then((data) => setCashFlowCache((prev) => ({ ...prev, [selected]: { loading: false, data } })))
      .catch(() => setCashFlowCache((prev) => ({ ...prev, [selected]: { loading: false, error: true } })));
  }, [selected, properties]);

  // Fetch comp analysis when a card is opened (on-demand, cached per property)
  useEffect(() => {
    if (!selected || fetchedComps.current.has(selected)) return;
    const p = properties.find((x) => x.id === selected);
    if (!p || !p.lat || !p.lng) return;
    const price = parseFloat((p.price || "").replace(/[$,~]/g, "").match(/[\d.]+/)?.[0] || "");
    if (!price || isNaN(price)) return;

    fetchedComps.current.add(selected);
    const params = new URLSearchParams({
      price,
      lat: p.lat,
      lng: p.lng,
      beds: p.beds || 2,
      sqft: p.sqft || 0,
      county: p.county || "clarke",
    });
    fetch(`${API_URL}/api/comps?${params}`)
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then((data) => setCompsCache((prev) => ({ ...prev, [selected]: data })))
      .catch(() => fetchedComps.current.delete(selected));
  }, [selected, properties]);


  // Fetch traffic corridor context when a card is opened (on-demand, cached per property)
  useEffect(() => {
    if (!selected || fetchedTraffic.current.has(selected)) return;
    const p = properties.find((x) => x.id === selected);
    if (!p || !p.lat || !p.lng) return;
    fetchedTraffic.current.add(selected);
    const params = new URLSearchParams({ lat: p.lat, lng: p.lng, radius_mi: 2.0 });
    fetch(`${API_URL}/api/traffic?${params}`)
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then((data) => setTrafficCache((prev) => ({ ...prev, [selected]: data })))
      .catch(() => fetchedTraffic.current.delete(selected));
  }, [selected, properties]);

  // Deep-link: ?property=<address> auto-selects and scrolls to a property.
  // Fires when properties updates so it works for both seed data and API-loaded data.
  useEffect(() => {
    const addr = new URLSearchParams(window.location.search).get("property");
    if (!addr || properties.length === 0) return;
    const match = properties.find((p) => (p.address || "").toLowerCase() === addr.toLowerCase());
    if (!match) return;
    setSelected(match.id);
    setTimeout(() => cardRefs.current[match.id]?.scrollIntoView({ behavior: "smooth", block: "start" }), 150);
  }, [properties]);

  // Populate score cache: use pre-computed fields when available, fall back to API for any gaps
  useEffect(() => {
    if (!properties.length) return;
    const precomputed = {};
    const needsApi = [];

    for (const p of properties) {
      if (scoreCache[p.id]) continue;
      if (p.composite_score != null) {
        precomputed[p.id] = {
          loading: false,
          data: {
            composite_score: p.composite_score,
            sub_scores: p.sub_scores || {},
            cash_flow_detail: p.cash_flow || {},
            proximity_detail: p.proximity_detail || null,
            traffic_detail: p.traffic_detail || null,
            flood_detail: p.flood_detail || null,
          },
        };
      } else if (p.lat && p.lng) {
        const price = parseFloat((p.price || "").replace(/[$,~]/g, "").match(/[\d.]+/)?.[0] || "");
        if (price && !isNaN(price)) needsApi.push(p);
      }
    }

    if (Object.keys(precomputed).length) setScoreCache((prev) => ({ ...prev, ...precomputed }));

    if (needsApi.length) {
      const loadingPatch = Object.fromEntries(needsApi.map((p) => [p.id, { loading: true }]));
      setScoreCache((prev) => ({ ...prev, ...loadingPatch }));
      const body = needsApi.map((p) => ({
        id: p.id,
        price: parseFloat((p.price || "").replace(/[$,~]/g, "").match(/[\d.]+/)?.[0]),
        lat: p.lat, lng: p.lng,
        beds: p.beds || 2, sqft: p.sqft || 0,
        property_type: p.property_type || "",
        county: p.county || "clarke",
        ...(p.year_built ? { year_built: p.year_built } : {}),
      }));
      fetch(`${API_URL}/api/score-batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
        .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then((results) => {
          const patch = {};
          for (const [id, data] of Object.entries(results)) {
            patch[id] = data.error ? { loading: false, error: true } : { loading: false, data };
          }
          setScoreCache((prev) => ({ ...prev, ...patch }));
        })
        .catch(() => {
          const errPatch = Object.fromEntries(needsApi.map((p) => [p.id, { loading: false, error: true }]));
          setScoreCache((prev) => ({ ...prev, ...errPatch }));
        });
    }
  }, [properties]);

  const filtered = properties
    .filter((p) => matchesPropType(p, filter))
    .filter((p) => showDismissed || !dismissed.has(String(p.id)))
    .slice()
    .sort((a, b) => {
      const sa = scoreCache[a.id]?.data?.composite_score ?? -1;
      const sb = scoreCache[b.id]?.data?.composite_score ?? -1;
      return sb - sa;
    });

  // Map from property id → rank (1-based) in the current sorted+filtered list
  const rankMap = Object.fromEntries(filtered.map((p, i) => [p.id, i + 1]));
  // Only show top N in list and on map
  const visibleFiltered = filtered.slice(0, topN);

  return (
    <div>
      <div style={{ display: "flex", gap: "8px", marginBottom: "12px", alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontSize: "12px", color: COLORS.textDim, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px", whiteSpace: "nowrap" }}>
          {showDistressed ? `${distressedParcels.length} parcels` : listingsLoading ? "Loading…" : `${filtered.length} listings`}
        </span>
        <select value={filter} onChange={(e) => { setFilter(e.target.value); setSelected(null); setShowDistressed(e.target.value === "distressed"); }}
          style={{ padding: "6px 12px", borderRadius: "6px", border: `1px solid ${COLORS.accent}`, background: COLORS.card, color: COLORS.text, fontSize: "12px", fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
          {PROP_TYPE_OPTIONS.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
        </select>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap", marginLeft: "auto" }}>
          {dismissed.size > 0 && (
            <button onClick={() => setShowDismissed((v) => !v)}
              style={{ padding: "6px 10px", borderRadius: "6px", border: `1px solid ${showDismissed ? COLORS.orange : COLORS.border}`, background: showDismissed ? COLORS.orange + "18" : "transparent", color: showDismissed ? COLORS.orange : COLORS.textDim, fontSize: "12px", fontWeight: 600, cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap" }}>
              Passed ({dismissed.size}) {showDismissed ? "▲" : "▼"}
            </button>
          )}
          <button onClick={() => setShowZoning((v) => !v)}
            style={{ padding: "6px 10px", borderRadius: "6px", border: `1px solid ${showZoning ? COLORS.blue : COLORS.border}`, background: showZoning ? COLORS.blue + "20" : "transparent", color: showZoning ? COLORS.blue : COLORS.textDim, fontSize: "12px", fontWeight: 600, cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap" }}>
            🗺 Zoning {zoningLoading ? "…" : showZoning ? "ON" : "OFF"}
          </button>

          <button onClick={() => setShowCensus((v) => !v)}
            style={{ padding: "6px 10px", borderRadius: "6px", border: `1px solid ${showCensus ? "#a78bfa" : COLORS.border}`, background: showCensus ? "#a78bfa20" : "transparent", color: showCensus ? "#a78bfa" : COLORS.textDim, fontSize: "12px", fontWeight: 600, cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap" }}>
            📊 Census {censusLoading ? "…" : showCensus ? "ON" : "OFF"}
          </button>
          {showCensus && (
            <select value={censusVar} onChange={(e) => setCensusVar(e.target.value)}
              style={{ padding: "6px 10px", borderRadius: "6px", border: `1px solid #a78bfa`, background: COLORS.card, color: COLORS.text, fontSize: "12px", fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
              {Object.entries(CENSUS_VARS).map(([key, cfg]) => (
                <option key={key} value={key}>{cfg.label}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      {!showDistressed && (
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "12px" }}>
          <span style={{ fontSize: "12px", fontWeight: 600, color: COLORS.textDim, whiteSpace: "nowrap" }}>Top {topN} pins</span>
          <div style={{ position: "relative", flex: 1, maxWidth: "280px" }}>
            <input type="range" min={1} max={filtered.length || 350} value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
              style={{ width: "100%", appearance: "none", height: "6px", borderRadius: "4px", outline: "none", cursor: "pointer",
                background: `linear-gradient(to right, ${COLORS.green} 0%, ${COLORS.green} ${(topN / (filtered.length || 350)) * 100}%, ${COLORS.border} ${(topN / (filtered.length || 350)) * 100}%, ${COLORS.border} 100%)` }} />
          </div>
          <span style={{ fontSize: "12px", color: COLORS.textDim, whiteSpace: "nowrap" }}>of {filtered.length}</span>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: showDistressed ? "1fr" : "minmax(0, 3fr) minmax(280px, 2fr)", gap: "14px" }}>
        <MapContainer center={[33.945, -83.4]} zoom={12} style={{ height: "clamp(420px, 60vh, 680px)", width: "100%", borderRadius: "8px", border: `1px solid ${COLORS.border}`, zIndex: 0 }}>
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            subdomains="abcd"
            maxZoom={20}
          />
          <MapFlyTo selected={selected} properties={properties} />
          <MapResizer trigger={showDistressed} />

          {showCensus && censusData && censusBreaks.length > 1 && (
            <GeoJSON
              key={`census-layer-${censusVar}`}
              data={censusData}
              style={(feature) => {
                const varCfg = CENSUS_VARS[censusVar];
                const val = feature.properties?.[censusVar];
                const fill = censusColorForValue(val, censusBreaks, varCfg.colors);
                return { fillColor: fill, fillOpacity: 0.55, color: "#fff", weight: 1, opacity: 0.6 };
              }}
              onEachFeature={(feature, layer) => {
                const props = feature.properties || {};
                const varCfg = CENSUS_VARS[censusVar];
                const val = props[censusVar];
                const name = props.NAME || props.TRACT || props.tract_code || "Tract";
                const income = props.median_household_income ? `$${(props.median_household_income / 1000).toFixed(0)}K` : "—";
                const renterPct = props.renter_pct ? `${props.renter_pct.toFixed(0)}%` : "—";
                const pop = props.total_population ? props.total_population.toLocaleString() : "—";
                layer.bindTooltip(
                  `<div style="font-family:system-ui;font-size:12px;min-width:140px;">
                    <strong>Census Tract ${name}</strong><br/>
                    <span style="color:#888">${varCfg.label}:</span> <strong>${val !== null && val !== undefined ? varCfg.format(val) : "—"}</strong><br/>
                    <span style="color:#888">Population:</span> ${pop}<br/>
                    <span style="color:#888">Med. Income:</span> ${income} &nbsp; <span style="color:#888">Renter:</span> ${renterPct}
                  </div>`,
                  { sticky: true, direction: "top" }
                );
              }}
            />
          )}

          {showZoning && zoningData && (
            <GeoJSON
              key="zoning-layer"
              data={zoningData}
              style={zoningStyle}
              onEachFeature={(feature, layer) => {
                const props = feature.properties || {};
                const zone = props.CurrentZn || props.CombinedZn || "Unknown";
                const acres = props.Acres ? `${parseFloat(props.Acres).toFixed(2)} ac` : "—";
                const parcel = props.PARCEL_NO || "—";
                layer.bindTooltip(
                  `<div style="font-family:system-ui;font-size:12px;"><strong>${zone}</strong><br/>Parcel: ${parcel}<br/>Lot: ${acres}</div>`,
                  { sticky: true, direction: "top" }
                );
              }}
            />
          )}

          {!showDistressed && visibleFiltered.map((p) => {
            return (
              <Marker key={p.id} position={[p.lat, p.lng]} icon={makeIcon(p, rankMap[p.id])}
                ref={(ref) => { if (ref) markerRefs.current[p.id] = ref; }}
                eventHandlers={{ click: () => { setSelected(p.id); setTimeout(() => cardRefs.current[p.id]?.scrollIntoView({ behavior: "smooth", block: "start" }), 50); } }}>
                <Popup maxWidth={300}>
                  <div style={{ fontFamily: "system-ui,sans-serif", minWidth: "240px" }}>
                    <div style={{ fontSize: "14px", fontWeight: 800, color: "#1a1a1a", marginBottom: "4px" }}>{p.address}</div>
                    <div style={{ fontSize: "18px", fontWeight: 800, color: "#8b5cf6", marginBottom: "6px" }}>{p.price}</div>
                    <div style={{ fontSize: "11px", color: "#555", marginBottom: "4px" }}>{p.type}</div>
                    <div style={{ fontSize: "11px", color: "#16a34a", fontWeight: 700, marginBottom: "8px" }}>
                      {(() => {
                        const re = cashFlowCache[p.id]?.data?.rent_estimate;
                        if (re?.mid) return `Est. rent: $${re.mid.toLocaleString()}/mo ($${re.low.toLocaleString()}–$${re.high.toLocaleString()})${re.per_unit ? " /unit" : ""}`;
                        return `Est. rent: ${p.rent}`;
                      })()}
                    </div>
                    <div style={{ fontSize: "11px", color: "#444", lineHeight: 1.5, marginBottom: "10px", borderTop: "1px solid #ddd", paddingTop: "8px" }}>
                      {p.why.substring(0, 200)}{p.why.length > 200 ? "…" : ""}
                    </div>
                    <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                      <a href={`https://www.google.com/maps/search/?api=1&query=${p.lat},${p.lng}`} target="_blank" rel="noopener noreferrer" style={{ padding: "5px 12px", border: "1px solid #8b5cf6", color: "#8b5cf6", borderRadius: "4px", fontSize: "11px", fontWeight: 700, textDecoration: "none" }}>Google Maps ↗</a>
                      <a href={p.url} target="_blank" rel="noopener noreferrer" style={{ padding: "5px 12px", border: "1px solid #8b5cf6", color: "#8b5cf6", borderRadius: "4px", fontSize: "11px", fontWeight: 700, textDecoration: "none" }}>Redfin ↗</a>
                      <a href={`https://www.zillow.com/homes/${encodeURIComponent(p.address.split(",")[0])}_rb/`} target="_blank" rel="noopener noreferrer" style={{ padding: "5px 12px", border: "1px solid #8b5cf6", color: "#8b5cf6", borderRadius: "4px", fontSize: "11px", fontWeight: 700, textDecoration: "none" }}>Zillow ↗</a>
                    </div>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {showDistressed && distressedParcels.map((feat, i) => {
            const props = feat.properties || feat;
            const coords = feat.geometry?.coordinates;
            if (!coords) return null;
            const [lng, lat] = coords;
            const score = props.distress_score || 0;
            const color = distressColor(score);
            return (
              <CircleMarker key={props.parcel_id || i} center={[lat, lng]}
                radius={score >= 70 ? 10 : score >= 50 ? 8 : 6}
                pathOptions={{ color, fillColor: color, fillOpacity: 0.75, weight: 2 }}
                eventHandlers={{ click: () => setSelectedDistressed(props.parcel_id) }}>
                <Popup maxWidth={320}>
                  <div style={{ fontFamily: "system-ui,sans-serif", minWidth: "260px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                      <span style={{ background: color, color: "#fff", fontSize: "10px", fontWeight: 800, padding: "2px 8px", borderRadius: "4px", textTransform: "uppercase" }}>
                        {props.distress_tier || "distressed"} · {score} pts
                      </span>
                      <span style={{ fontSize: "10px", color: "#888" }}>{props.county} co.</span>
                    </div>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#1a1a1a", marginBottom: "4px" }}>{props.address || "Unknown address"}</div>
                    <div style={{ fontSize: "11px", color: "#444", marginBottom: "8px" }}>
                      Owner: <strong>{props.owner_name || "—"}</strong>
                      {props.absentee_owner && <span style={{ color: "#ef4444", marginLeft: "6px", fontSize: "10px", fontWeight: 700 }}>ABSENTEE</span>}
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px", marginBottom: "8px", fontSize: "11px" }}>
                      <div><span style={{ color: "#888" }}>Assessed: </span><strong>{props.assessed_value ? `$${props.assessed_value.toLocaleString()}` : "—"}</strong></div>
                      <div><span style={{ color: "#888" }}>Tax owed: </span><strong style={{ color: "#ef4444" }}>{props.tax_owed ? `$${props.tax_owed.toLocaleString()}` : "—"}</strong></div>
                      <div><span style={{ color: "#888" }}>Zoning: </span><strong>{props.zoning_code || "—"}</strong></div>
                      <div><span style={{ color: "#888" }}>Lot: </span><strong>{props.lot_size_acres ? `${props.lot_size_acres} ac` : "—"}</strong></div>
                      <div><span style={{ color: "#888" }}>Year built: </span><strong>{props.year_built || "—"}</strong></div>
                      <div><span style={{ color: "#888" }}>Prox. score: </span><strong>{props.proximity_score ? `${Math.round(props.proximity_score)}/100` : "—"}</strong></div>
                    </div>
                    {props.signals && props.signals.length > 0 && (
                      <div style={{ borderTop: "1px solid #eee", paddingTop: "8px", marginBottom: "8px" }}>
                        <div style={{ fontSize: "10px", color: "#888", fontWeight: 700, textTransform: "uppercase", marginBottom: "4px" }}>Active Signals</div>
                        {props.signals.map((s) => (
                          <div key={s} style={{ fontSize: "10px", color: "#ef4444", marginBottom: "2px" }}>• {s.replace(/_/g, " ")}</div>
                        ))}
                      </div>
                    )}
                    {props.owner_mailing_address && (
                      <div style={{ fontSize: "10px", color: "#555", borderTop: "1px solid #eee", paddingTop: "6px" }}>
                        Mail: {props.owner_mailing_address}
                      </div>
                    )}
                    <a href={`https://www.google.com/maps/search/?api=1&query=${lat},${lng}`} target="_blank" rel="noopener noreferrer"
                      style={{ display: "inline-block", marginTop: "8px", padding: "5px 12px", border: "1px solid #8b5cf6", color: "#8b5cf6", borderRadius: "4px", fontSize: "11px", fontWeight: 700, textDecoration: "none" }}>
                      Google Maps ↗
                    </a>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>

        {!showDistressed && <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "clamp(420px, 60vh, 680px)", overflowY: "auto", paddingRight: "4px" }}>
          {visibleFiltered.map((p, idx) => {
            const isOpen = selected === p.id;
            const dotColor = COLORS.accent;
            const rank = idx + 1;
            return (
              <div key={p.id} ref={(el) => { if (el) cardRefs.current[p.id] = el; }} onClick={() => setSelected(isOpen ? null : p.id)}
                style={{ background: isOpen ? COLORS.cardHover : COLORS.card, border: `1px solid ${isOpen ? dotColor + "60" : COLORS.border}`, borderRadius: "8px", padding: "14px", cursor: "pointer", transition: "all 0.15s" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                  <div style={{ width: "22px", height: "22px", borderRadius: "50%", background: dotColor, flexShrink: 0, boxShadow: `0 0 6px ${dotColor}40`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontWeight: 800, color: "#fff" }}>{rank}</div>
                  <span style={{ fontWeight: 700, fontSize: "13px", color: COLORS.text, flex: 1 }}>{p.address}</span>
                  {dismissed.has(String(p.id)) ? (
                    <button onClick={(e) => { e.stopPropagation(); undismissProperty(p.id); }}
                      title="Restore"
                      style={{ marginLeft: "auto", padding: "2px 8px", fontSize: "10px", fontWeight: 700, color: COLORS.orange, background: COLORS.orange + "15", border: `1px solid ${COLORS.orange}40`, borderRadius: "4px", cursor: "pointer", fontFamily: "inherit", flexShrink: 0 }}>
                      Undo
                    </button>
                  ) : (
                    <button onClick={(e) => { e.stopPropagation(); dismissProperty(p.id); }}
                      title="Mark as reviewed / pass"
                      style={{ marginLeft: "auto", padding: "2px 8px", fontSize: "10px", fontWeight: 700, color: COLORS.textDim, background: "transparent", border: `1px solid ${COLORS.border}`, borderRadius: "4px", cursor: "pointer", fontFamily: "inherit", flexShrink: 0, opacity: 0.6 }}>
                      Pass
                    </button>
                  )}
                </div>
                <div style={{ display: "flex", gap: "12px", marginLeft: "30px", alignItems: "center" }}>
                  <span style={{ fontSize: "16px", fontWeight: 800, color: COLORS.accent }}>{p.price}</span>
                  <span style={{ fontSize: "12px", color: COLORS.textDim, alignSelf: "center" }}>{p.type}</span>
                  {(() => {
                    const se = scoreCache[p.id];
                    if (!se?.data?.composite_score) return null;
                    const total = se.data.composite_score;
                    const c = total >= 70 ? COLORS.green : total >= 50 ? COLORS.accent : COLORS.red;
                    const mcf = se.data.cash_flow_detail?.monthly_cash_flow;
                    const cfColor = mcf == null ? null : mcf >= 0 ? COLORS.green : COLORS.red;
                    return (
                      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "5px" }}>
                        {cfColor && <div title={mcf >= 0 ? `+$${Math.round(mcf)}/mo` : `-$${Math.abs(Math.round(mcf))}/mo`} style={{ width: "8px", height: "8px", borderRadius: "50%", background: cfColor, flexShrink: 0 }} />}
                        <span style={{ fontSize: "11px", fontWeight: 800, color: c, background: c + "18", border: `1px solid ${c}40`, borderRadius: "4px", padding: "2px 7px" }}>{total}</span>
                      </div>
                    );
                  })()}
                </div>
                {isOpen && (
                  <div style={{ marginTop: "12px", marginLeft: "30px", borderTop: `1px solid ${COLORS.border}`, paddingTop: "12px" }}>
                    {(() => {
                      const se = scoreCache[p.id];
                      if (!se) return null;
                      if (se.loading) return <div style={{ fontSize: "11px", color: COLORS.textDim, marginBottom: "10px", fontStyle: "italic" }}>Scoring…</div>;
                      if (se.error || !se.data) return null;
                      const sc = se.data;
                      const total = sc.composite_score;
                      const scoreColor = total >= 70 ? COLORS.green : total >= 50 ? COLORS.accent : COLORS.red;
                      const sub = sc.sub_scores || {};
                      const subRows = [
                        ["Cash Flow", sub.cash_flow],
                        ["Appreciation", sub.appreciation],
                        ["Entry Price", sub.entry_price],
                        ["Demand", sub.demand],
                        ["Risk", sub.risk],
                      ];
                      return (
                        <div style={{ marginBottom: "12px", padding: "10px 12px", background: COLORS.bg, borderRadius: "6px", border: `1px solid ${COLORS.border}` }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                            <span style={{ fontSize: "10px", color: COLORS.textDim, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" }}>Investment Score</span>
                            <span style={{ fontSize: "26px", fontWeight: 800, color: scoreColor, lineHeight: 1 }}>
                              {total}<span style={{ fontSize: "12px", color: COLORS.textDim, fontWeight: 400 }}>/100</span>
                            </span>
                          </div>
                          {subRows.map(([label, val]) => {
                            const v = val ?? 0;
                            const barColor = v >= 60 ? COLORS.green : v >= 35 ? COLORS.accent : COLORS.red;
                            return (
                              <div key={label} style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "3px" }}>
                                <span style={{ fontSize: "10px", color: COLORS.textDim, width: "78px", flexShrink: 0 }}>{label}</span>
                                <div style={{ flex: 1, height: "4px", background: COLORS.border, borderRadius: "2px" }}>
                                  <div style={{ width: `${v}%`, height: "100%", background: barColor, borderRadius: "2px" }} />
                                </div>
                                <span style={{ fontSize: "10px", fontWeight: 700, color: barColor, width: "24px", textAlign: "right" }}>{v}</span>
                              </div>
                            );
                          })}
                          {sc.proximity_detail && (
                            <div style={{ fontSize: "10px", color: COLORS.textDim, marginTop: "6px" }}>
                              {Object.entries(sc.proximity_detail.distances_miles || {}).slice(0, 3).map(([k, d]) => (
                                <span key={k} style={{ marginRight: "10px" }}>{k.replace(/_/g, " ")}: {d}mi</span>
                              ))}
                            </div>
                          )}
                          {sc.traffic_detail?.found && (
                            <div style={{ fontSize: "10px", color: COLORS.textDim, marginTop: "3px" }}>
                              <span style={{ color: sc.traffic_detail.tier === "heavy_corridor" ? COLORS.orange : sc.traffic_detail.tier === "urban_arterial" ? COLORS.accent : COLORS.textDim, fontWeight: 600 }}>
                                {(sc.traffic_detail.aadt / 1000).toFixed(0)}K AADT
                              </span>
                              <span style={{ marginLeft: "4px" }}>· {sc.traffic_detail.road} ({sc.traffic_detail.distance_miles}mi)</span>
                            </div>
                          )}
                        </div>
                      );
                    })()}
                    {(() => {
                      const cfEntry = cashFlowCache[p.id];
                      if (!cfEntry) return (
                        <div style={{ marginBottom: "10px" }}>
                          <span style={{ fontSize: "11px", color: COLORS.textDim, textTransform: "uppercase", fontWeight: 600 }}>Est. Rent: </span>
                          <span style={{ fontSize: "13px", color: COLORS.green, fontWeight: 700 }}>{p.rent}</span>
                        </div>
                      );
                      if (cfEntry.loading) return (
                        <div style={{ fontSize: "11px", color: COLORS.textDim, marginBottom: "10px", fontStyle: "italic" }}>Fetching rent estimates…</div>
                      );
                      if (cfEntry.error || !cfEntry.data) return null;
                      const { rent_estimate: re, cash_flow: cf } = cfEntry.data;
                      const cfColor = cf.monthly_cash_flow >= 0 ? COLORS.green : COLORS.red;
                      const cocColor = cf.cash_on_cash_pct >= 5 ? COLORS.green : cf.cash_on_cash_pct >= 0 ? COLORS.accent : COLORS.red;
                      const capColor = cf.cap_rate_pct >= 6 ? COLORS.green : cf.cap_rate_pct >= 4 ? COLORS.accent : COLORS.red;
                      const piti = cf.monthly_mortgage + cf.monthly_tax + cf.monthly_insurance;
                      const opex = cf.monthly_management + cf.monthly_maintenance + cf.monthly_vacancy;
                      const sources = re.sources || [];
                      const srcCount = sources.length;
                      return (
                        <>
                          {/* Rent estimate block */}
                          <div style={{ marginBottom: "10px", padding: "10px 12px", background: COLORS.bg, borderRadius: "6px", border: `1px solid ${COLORS.border}` }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                              <span style={{ fontSize: "10px", color: COLORS.textDim, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                                Rent Estimate{re.per_unit ? " (per unit)" : ""}
                              </span>
                              <span style={{ fontSize: "10px", color: COLORS.textDim }}>
                                {srcCount > 1 ? `avg of ${srcCount} sources` : re.method === "census_tract" ? "tract-adjusted" : "market avg"}
                              </span>
                            </div>
                            <div style={{ fontSize: "18px", fontWeight: 800, color: COLORS.green, marginBottom: "6px" }}>
                              ${re.mid.toLocaleString()}<span style={{ fontSize: "12px", fontWeight: 400, color: COLORS.textDim }}>/mo  &nbsp;range ${re.low.toLocaleString()}–${re.high.toLocaleString()}</span>
                            </div>
                            {sources.length > 0 && (
                              <div style={{ borderTop: `1px solid ${COLORS.border}`, paddingTop: "6px", display: "flex", flexDirection: "column", gap: "3px" }}>
                                {sources.map((s) => (
                                  <div key={s.source} style={{ display: "flex", justifyContent: "space-between", fontSize: "10px" }}>
                                    <span style={{ color: COLORS.textDim }}>
                                      {s.source}
                                      {s.method && s.method !== "aggregated" && s.method !== "internal_only" ? ` (${s.method.replace("_", " ")})` : ""}
                                      {s.sample_size ? ` · ${s.sample_size} listings` : ""}
                                    </span>
                                    <span style={{ fontWeight: 700, color: s.source === "Internal model" ? COLORS.accent : COLORS.text }}>
                                      ${s.mid.toLocaleString()}/mo
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                          {/* Cash flow block */}
                          <div style={{ marginBottom: "12px", padding: "10px 12px", background: COLORS.bg, borderRadius: "6px", border: `1px solid ${COLORS.border}` }}>
                            <div style={{ fontSize: "10px", color: COLORS.textDim, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>Cash Flow Analysis</div>
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 12px", fontSize: "12px", marginBottom: "8px" }}>
                              <div>
                                <span style={{ color: COLORS.textDim }}>Monthly CF: </span>
                                <span style={{ fontWeight: 800, color: cfColor }}>{cf.monthly_cash_flow >= 0 ? "+" : ""}${cf.monthly_cash_flow.toLocaleString()}</span>
                              </div>
                              <div>
                                <span style={{ color: COLORS.textDim }}>CoC return: </span>
                                <span style={{ fontWeight: 700, color: cocColor }}>{cf.cash_on_cash_pct}%</span>
                              </div>
                              <div>
                                <span style={{ color: COLORS.textDim }}>Cap rate: </span>
                                <span style={{ fontWeight: 700, color: capColor }}>{cf.cap_rate_pct}%</span>
                              </div>
                            </div>
                            <div style={{ fontSize: "10px", color: COLORS.textDim, lineHeight: 1.6 }}>
                              PITI ${piti.toLocaleString()} · Opex ${opex.toLocaleString()} · Down ${cf.down_payment.toLocaleString()}
                              {cf.hoa_monthly > 0 && ` · HOA $${cf.hoa_monthly.toLocaleString()}`}
                            </div>
                          </div>
                        </>
                      );
                    })()}
                    {(() => {
                      const comps = compsCache[p.id];
                      const traffic = trafficCache[p.id];
                      const dom = p.days_on_market;
                      const yr = p.year_built;
                      const ppsf = p.sqft > 0 && p.price ? Math.round(parseFloat((p.price || "").replace(/[$,~]/g, "").match(/[\d.]+/)?.[0] || 0) / p.sqft) : null;
                      const domColor = dom == null ? null : dom <= 7 ? COLORS.blue : dom <= 30 ? COLORS.textDim : dom <= 60 ? COLORS.orange : COLORS.red;
                      const domLabel = dom == null ? null : dom === 0 ? "Just listed" : dom <= 7 ? `${dom}d — fresh to market` : dom <= 30 ? `${dom} days on market` : dom <= 60 ? `${dom} days — seller may be flexible` : `${dom} days — stale listing, price leverage`;
                      const pvsLabel = comps?.price_vs_comps_pct != null ? (
                        comps.price_vs_comps_pct > 15 ? { text: `+${comps.price_vs_comps_pct}% above comps`, color: COLORS.red }
                        : comps.price_vs_comps_pct > 5 ? { text: `+${comps.price_vs_comps_pct}% above market`, color: COLORS.orange }
                        : comps.price_vs_comps_pct >= -5 ? { text: `${comps.price_vs_comps_pct > 0 ? "+" : ""}${comps.price_vs_comps_pct}% at market`, color: COLORS.green }
                        : { text: `${comps.price_vs_comps_pct}% below market — value`, color: COLORS.green }
                      ) : null;
                      // Traffic corridor signal
                      const trafficLabel = (() => {
                        if (!traffic?.found) return null;
                        const { road, aadt, tier, distance_miles } = traffic;
                        const aadtFmt = aadt >= 1000 ? `${(aadt / 1000).toFixed(0)}K` : aadt;
                        const tierColor = tier === "heavy_corridor" ? COLORS.orange : tier === "urban_arterial" ? COLORS.accent : COLORS.textDim;
                        const tierLabel = tier === "heavy_corridor" ? "heavy corridor" : tier === "urban_arterial" ? "urban arterial" : tier === "collector" ? "collector road" : "residential";
                        return { road, aadtFmt, tierColor, tierLabel, distance_miles };
                      })();
                      if (!domLabel && !yr && !comps?.comp_count && !trafficLabel) return null;
                      return (
                        <div style={{ marginBottom: "10px", padding: "8px 10px", background: COLORS.bg, borderRadius: "6px", border: `1px solid ${COLORS.border}` }}>
                          <div style={{ fontSize: "10px", color: COLORS.textDim, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "6px" }}>Seller Intelligence</div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 16px", fontSize: "11px" }}>
                            {domLabel && <span><span style={{ color: COLORS.textDim }}>DOM: </span><span style={{ fontWeight: 700, color: domColor }}>{domLabel}</span></span>}
                            {yr && <span><span style={{ color: COLORS.textDim }}>Built: </span><span style={{ fontWeight: 700, color: yr < 1970 ? COLORS.orange : COLORS.text }}>{yr}{yr < 1970 ? " — verify condition" : ""}</span></span>}
                            {ppsf && comps?.median_price_per_sqft && (
                              <span><span style={{ color: COLORS.textDim }}>$/sqft: </span><span style={{ fontWeight: 700, color: COLORS.text }}>${ppsf}</span><span style={{ color: COLORS.textDim }}> vs. ${comps.median_price_per_sqft} median </span>{pvsLabel && <span style={{ fontWeight: 700, color: pvsLabel.color }}>({pvsLabel.text})</span>}</span>
                            )}
                            {!ppsf && pvsLabel && <span><span style={{ color: COLORS.textDim }}>vs. comps: </span><span style={{ fontWeight: 700, color: pvsLabel.color }}>{pvsLabel.text}</span></span>}
                            {comps?.comp_count > 0 && <span style={{ color: COLORS.textDim }}>{comps.comp_count} comps within 4mi</span>}
                            {trafficLabel && (
                              <span>
                                <span style={{ color: COLORS.textDim }}>Traffic: </span>
                                <span style={{ fontWeight: 700, color: trafficLabel.tierColor }}>{trafficLabel.aadtFmt} AADT</span>
                                <span style={{ color: COLORS.textDim }}> · {trafficLabel.road} ({trafficLabel.distance_miles}mi) · </span>
                                <span style={{ fontWeight: 600, color: trafficLabel.tierColor }}>{trafficLabel.tierLabel}</span>
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })()}
                    {/* Price history — shows age of listing and any price drop */}
                    {(() => {
                      const prevPrice = p.previous_price;
                      const curPrice = parseFloat((p.price || "").replace(/[$,~]/g, "").match(/[\d.]+/)?.[0] || "");
                      const firstSeen = p.first_seen;
                      const daysOld = firstSeen
                        ? Math.round((Date.now() - new Date(firstSeen).getTime()) / 86400000)
                        : null;
                      const dropped = prevPrice && curPrice && prevPrice > curPrice;
                      if (!dropped && daysOld == null) return null;
                      return (
                        <div style={{ marginBottom: "10px", padding: "7px 10px", background: dropped ? COLORS.green + "08" : COLORS.bg, borderRadius: "6px", border: `1px solid ${dropped ? COLORS.green + "30" : COLORS.border}`, display: "flex", gap: "14px", flexWrap: "wrap", fontSize: "11px" }}>
                          {daysOld != null && (
                            <span>
                              <span style={{ color: COLORS.textDim }}>On market: </span>
                              <span style={{ fontWeight: 700, color: daysOld <= 7 ? COLORS.blue : daysOld <= 30 ? COLORS.text : COLORS.orange }}>
                                {daysOld === 0 ? "Just listed" : `${daysOld} day${daysOld !== 1 ? "s" : ""}`}
                              </span>
                            </span>
                          )}
                          {dropped && (
                            <span>
                              <span style={{ color: COLORS.textDim }}>Price drop: </span>
                              <span style={{ fontWeight: 700, color: COLORS.green }}>
                                ↓ from ${prevPrice.toLocaleString()}
                                <span style={{ fontWeight: 400, color: COLORS.textDim }}>
                                  {" "}(–${(prevPrice - curPrice).toLocaleString()})
                                </span>
                              </span>
                            </span>
                          )}
                        </div>
                      );
                    })()}
                    <p style={{ margin: "0 0 12px", fontSize: "12px", color: COLORS.textDim, lineHeight: 1.6 }}>{p.why}</p>
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                      <a href={`https://www.google.com/maps/search/?api=1&query=${p.lat},${p.lng}`} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
                        style={{ padding: "6px 14px", color: COLORS.accent, border: `1px solid ${COLORS.accent}40`, borderRadius: "5px", fontSize: "12px", fontWeight: 700, textDecoration: "none" }}>Google Maps ↗</a>
                      <a href={p.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
                        style={{ padding: "6px 14px", color: COLORS.accent, border: `1px solid ${COLORS.accent}40`, borderRadius: "5px", fontSize: "12px", fontWeight: 700, textDecoration: "none" }}>Redfin ↗</a>
                      <a href={`https://www.zillow.com/homes/${encodeURIComponent(p.address.split(",")[0])}_rb/`} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
                        style={{ padding: "6px 14px", color: COLORS.accent, border: `1px solid ${COLORS.accent}40`, borderRadius: "5px", fontSize: "12px", fontWeight: 700, textDecoration: "none" }}>Zillow ↗</a>
                      {onLoadCalculator && (
                        <button onClick={(e) => {
                          e.stopPropagation();
                          const priceVal = parseFloat((p.price || "").replace(/[$,~]/g, "").match(/[\d.]+/)?.[0] || "");
                          const rentMid = cashFlowCache[p.id]?.data?.rent_estimate?.mid;
                          onLoadCalculator({ price: priceVal || 275000, rent: rentMid || 1800, county: p.county || "clarke" });
                        }}
                          style={{ padding: "6px 14px", color: COLORS.green, background: "transparent", border: `1px solid ${COLORS.green}40`, borderRadius: "5px", fontSize: "12px", fontWeight: 700, cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap" }}>
                          Open in Calculator →
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>}
      </div>

      <div style={{ marginTop: "16px", background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "16px" }}>
        <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
          {showZoning && (
            <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap", borderLeft: `1px solid ${COLORS.border}`, paddingLeft: "24px" }}>
              <span style={{ fontSize: "11px", color: COLORS.textDim, fontWeight: 700, textTransform: "uppercase" }}>Zoning:</span>
              {Object.entries(ZONE_COLORS).slice(0, 8).map(([prefix, cfg]) => (
                <div key={prefix} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <div style={{ width: "10px", height: "10px", borderRadius: "2px", background: cfg.fill, opacity: 0.8 }} />
                  <span style={{ fontSize: "10px", color: COLORS.textDim }}>{prefix}</span>
                </div>
              ))}
            </div>
          )}
          {showDistressed && (
            <div style={{ display: "flex", alignItems: "center", gap: "16px", borderLeft: `1px solid ${COLORS.border}`, paddingLeft: "24px" }}>
              {[["#ef4444", "70+ pts", "Critical distress"], ["#fb923c", "50–69 pts", "High distress"], ["#facc15", "25–49 pts", "Watch list"]].map(([color, pts, label]) => (
                <div key={pts} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: color, border: `2px solid ${color}` }} />
                  <span style={{ fontSize: "11px", fontWeight: 700, color: COLORS.text }}>{label}</span>
                  <span style={{ fontSize: "10px", color: COLORS.textDim }}>{pts}</span>
                </div>
              ))}
            </div>
          )}
          {showCensus && censusBreaks.length > 1 && (() => {
            const varCfg = CENSUS_VARS[censusVar];
            return (
              <div style={{ display: "flex", alignItems: "center", gap: "8px", borderLeft: `1px solid ${COLORS.border}`, paddingLeft: "24px", flexWrap: "wrap" }}>
                <span style={{ fontSize: "11px", color: "#a78bfa", fontWeight: 700, textTransform: "uppercase" }}>{varCfg.label}:</span>
                {varCfg.colors.map((color, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: "3px" }}>
                    <div style={{ width: "18px", height: "12px", borderRadius: "2px", background: color, border: "1px solid #ffffff30" }} />
                    <span style={{ fontSize: "10px", color: COLORS.textDim }}>{varCfg.format(censusBreaks[i])}</span>
                  </div>
                ))}
                <span style={{ fontSize: "10px", color: COLORS.textDim }}>– {varCfg.format(censusBreaks[5])}</span>
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}

// ── Tab: Market Overview ─────────────────────────────────────────────────────

function MarketOverview() {
  return (
    <div>
      <div style={{ display: "flex", gap: "14px", flexWrap: "wrap", marginBottom: "24px" }}>
        <StatCard label="Median List Price" value="$375K" trend="↓ 2% YoY" sub="Clarke + Oconee — Mar 2026" />
        <StatCard label="Zillow Home Value" value="$307K" trend="+5.1% YoY" sub="Athens city typical value" />
        <StatCard label="Avg Days on Market" value="57" trend="+21% YoY" sub="More negotiating leverage" />
        <StatCard label="Active Listings" value="486+" trend="+143 vs last yr" sub="Clarke + Oconee combined" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "18px" }}>
        <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "22px" }}>
          <h3 style={{ margin: "0 0 16px", fontSize: "15px", fontWeight: 700, color: COLORS.accent, letterSpacing: "0.5px" }}>RENTAL MARKET SNAPSHOT</h3>
          {[
            { type: "Studio", rent: "$1,034–$1,100", sqft: "~423 sq ft" },
            { type: "1-Bedroom", rent: "$1,020–$1,350", sqft: "~701 sq ft" },
            { type: "2-Bedroom", rent: "$1,289–$1,510", sqft: "~1,062 sq ft" },
            { type: "3-Bedroom", rent: "$1,631–$2,043", sqft: "~1,345 sq ft" },
            { type: "4-Bedroom", rent: "$2,300–$2,500", sqft: "varies" },
          ].map((r) => (
            <div key={r.type} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: `1px solid ${COLORS.border}` }}>
              <div>
                <span style={{ fontWeight: 600, color: COLORS.text }}>{r.type}</span>
                <span style={{ color: COLORS.textDim, fontSize: "12px", marginLeft: "8px" }}>{r.sqft}</span>
              </div>
              <span style={{ fontWeight: 700, color: COLORS.green }}>{r.rent}</span>
            </div>
          ))}
          <div style={{ marginTop: "14px", fontSize: "12px", color: COLORS.textDim, lineHeight: 1.5 }}>
            Sources: RentCafe, Zillow, Rent.com, RentHop — Mar 2026. Athens rents ~22% below national avg. 1BR rents rose 13-17% YoY. 59% of Athens households are renters.
          </div>
        </div>
        <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "22px" }}>
          <h3 style={{ margin: "0 0 16px", fontSize: "15px", fontWeight: 700, color: COLORS.accent, letterSpacing: "0.5px" }}>MARKET CONDITIONS</h3>
          {[
            { label: "Absorption Rate", value: "3–3.5 months", note: "Up from 2.7 — shifting toward buyers" },
            { label: "2025 Avg Appreciation", value: "+3.6%", note: "Clarke+Oconee outpaced national 2.3%" },
            { label: "Mortgage Rates", value: "~6.0–6.5%", note: "Down from ~7% at start of 2025" },
            { label: "Millage Rate (Clarke)", value: "33.95 mills", note: "On 40% assessed value — no homestead exemption for rentals" },
            { label: "STR Regulation", value: "Restricted", note: "Owner-occupancy req'd in residential zones since Feb 2024" },
            { label: "Oconee Avg Sale Price", value: "$645K (2024)", note: "Higher price point, top-rated schools" },
          ].map((item) => (
            <div key={item.label} style={{ padding: "8px 0", borderBottom: `1px solid ${COLORS.border}` }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: "13px", color: COLORS.text }}>{item.label}</span>
                <span style={{ fontWeight: 700, color: COLORS.text, fontSize: "13px" }}>{item.value}</span>
              </div>
              <div style={{ fontSize: "11px", color: COLORS.textDim, marginTop: "2px" }}>{item.note}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Tab: Cash Flow Calculator ────────────────────────────────────────────────

function CashFlowCalc({ seed }) {
  const [price, setPrice] = useState(275000);
  const [down, setDown] = useState(25);
  const [rate, setRate] = useState(6.5);
  const [rent, setRent] = useState(1800);
  const lastSeedRef = useRef(null);
  useEffect(() => {
    if (!seed || seed === lastSeedRef.current) return;
    lastSeedRef.current = seed;
    if (seed.price) setPrice(seed.price);
    if (seed.rent) setRent(seed.rent);
  }, [seed]);
  const [tax, setTax] = useState(0);
  const [insurance, setInsurance] = useState(120);
  const [maintenance, setMaintenance] = useState(5);
  const [vacancy, setVacancy] = useState(5);
  const [mgmt, setMgmt] = useState(10);

  const loanAmt = price * (1 - down / 100);
  const monthlyRate = rate / 100 / 12;
  const nPayments = 360;
  const mortgage = loanAmt > 0 ? (loanAmt * monthlyRate * Math.pow(1 + monthlyRate, nPayments)) / (Math.pow(1 + monthlyRate, nPayments) - 1) : 0;
  const assessedValue = price * 0.4;
  const monthlyTax = tax > 0 ? tax / 12 : (assessedValue * 33.95) / 1000 / 12;
  const monthlyMaint = (rent * maintenance) / 100;
  const monthlyVacancy = (rent * vacancy) / 100;
  const monthlyMgmt = (rent * mgmt) / 100;
  const totalExpenses = mortgage + monthlyTax + insurance + monthlyMaint + monthlyVacancy + monthlyMgmt;
  const cashFlow = rent - totalExpenses;
  const annualCashFlow = cashFlow * 12;
  const cashOnCash = (annualCashFlow / (price * (down / 100))) * 100;
  const capRate = (((rent * 12) - (monthlyTax + insurance + monthlyMaint) * 12) / price) * 100;

  const inputStyle = { background: COLORS.bg, border: `1px solid ${COLORS.border}`, borderRadius: "6px", padding: "8px 12px", color: COLORS.text, fontSize: "14px", fontWeight: 600, width: "100%", boxSizing: "border-box" };
  const labelStyle = { fontSize: "11px", color: COLORS.textDim, fontWeight: 600, letterSpacing: "0.5px", textTransform: "uppercase", marginBottom: "4px", display: "block" };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "22px" }}>
      <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "22px" }}>
        <h3 style={{ margin: "0 0 18px", fontSize: "15px", fontWeight: 700, color: COLORS.accent }}>PROPERTY INPUTS</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "14px" }}>
          {[
            { label: "Purchase Price ($)", val: price, set: setPrice, step: 1000 },
            { label: "Down Payment (%)", val: down, set: setDown, step: 1 },
            { label: "Interest Rate (%)", val: rate, set: setRate, step: 0.1 },
            { label: "Monthly Rent ($)", val: rent, set: setRent, step: 50 },
            { label: "Annual Property Tax ($)", val: tax, set: setTax, step: 100, placeholder: "Auto: Clarke 33.95 mills" },
            { label: "Monthly Insurance ($)", val: insurance, set: setInsurance, step: 10 },
            { label: "Maintenance (% of rent)", val: maintenance, set: setMaintenance, step: 1 },
            { label: "Vacancy (% of rent)", val: vacancy, set: setVacancy, step: 1 },
            { label: "Management (% of rent)", val: mgmt, set: setMgmt, step: 1 },
          ].map((f) => (
            <div key={f.label}>
              <label style={labelStyle}>{f.label}</label>
              <input type="number" value={f.val} step={f.step} placeholder={f.placeholder} onChange={(e) => f.set(+e.target.value)} style={inputStyle} />
            </div>
          ))}
        </div>
        <div style={{ marginTop: "14px", fontSize: "11px", color: COLORS.textDim }}>
          Tax auto-calculates at Clarke County's 33.95 mills on 40% assessed value if left at $0. Override for Oconee County properties.
        </div>
      </div>
      <div>
        <div style={{ display: "flex", gap: "14px", marginBottom: "18px", flexWrap: "wrap" }}>
          <StatCard label="Monthly Cash Flow" value={`$${Math.round(cashFlow).toLocaleString()}`} trend={cashFlow >= 0 ? "✓ Positive" : "✗ Negative"} />
          <StatCard label="Cash-on-Cash Return" value={`${cashOnCash.toFixed(1)}%`} sub={`On $${(price * down / 100).toLocaleString()} invested`} />
        </div>
        <div style={{ display: "flex", gap: "14px", marginBottom: "18px", flexWrap: "wrap" }}>
          <StatCard label="Cap Rate" value={`${capRate.toFixed(1)}%`} sub="NOI / Purchase Price" />
          <StatCard label="Monthly Mortgage" value={`$${Math.round(mortgage).toLocaleString()}`} sub={`30yr fixed on $${Math.round(loanAmt).toLocaleString()}`} />
        </div>
        <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "22px" }}>
          <h3 style={{ margin: "0 0 14px", fontSize: "15px", fontWeight: 700, color: COLORS.accent }}>MONTHLY EXPENSE BREAKDOWN</h3>
          {[
            { label: "Mortgage (P&I)", val: mortgage, color: COLORS.red },
            { label: "Property Tax", val: monthlyTax, color: COLORS.orange },
            { label: "Insurance", val: insurance, color: COLORS.blue },
            { label: "Maintenance Reserve", val: monthlyMaint, color: COLORS.textDim },
            { label: "Vacancy Reserve", val: monthlyVacancy, color: COLORS.textDim },
            { label: "Property Management", val: monthlyMgmt, color: COLORS.accent },
          ].map((exp) => (
            <div key={exp.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={{ width: "8px", height: "8px", borderRadius: "2px", background: exp.color }} />
                <span style={{ fontSize: "13px", color: COLORS.text }}>{exp.label}</span>
              </div>
              <span style={{ fontWeight: 600, color: COLORS.text, fontSize: "13px" }}>${Math.round(exp.val).toLocaleString()}</span>
            </div>
          ))}
          <div style={{ display: "flex", justifyContent: "space-between", borderTop: `2px solid ${COLORS.accent}`, marginTop: "10px", paddingTop: "10px" }}>
            <span style={{ fontWeight: 700, color: COLORS.text }}>Total Expenses</span>
            <span style={{ fontWeight: 700, color: COLORS.red, fontSize: "15px" }}>${Math.round(totalExpenses).toLocaleString()}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "6px" }}>
            <span style={{ fontWeight: 700, color: COLORS.text }}>Gross Rent</span>
            <span style={{ fontWeight: 700, color: COLORS.green, fontSize: "15px" }}>${rent.toLocaleString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Tab: Development Intel ───────────────────────────────────────────────────

function DevelopmentIntel() {
  const projects = [
    {
      name: "SR 316 Freeway Conversion",
      status: "ACTIVE", statusColor: COLORS.green,
      investment: "$829M+ total program",
      timeline: "Multiple phases through ~2030",
      impact: "HIGH", impactColor: COLORS.red,
      details: "GDOT is converting the 40-mile SR 316 corridor from an at-grade highway to a limited-access freeway with interchanges. Three Oconee County contracts were just awarded in Jan 2025 (Dials Mill Extension interchange). Properties along the 316 corridor in Oconee and Barrow counties become significantly more accessible to Atlanta job centers.",
      investorAngle: "Buy in the 316 corridor now before interchange completions drive values up. Bogart and western Oconee are the sweet spot — still affordable, but directly benefiting from improved access.",
    },
    {
      name: "Akins Ford Arena District",
      status: "PLANNING", statusColor: COLORS.orange,
      investment: "$170M arena (complete) + district TBD",
      timeline: "Arena open Dec 2024; district development 12–48 months",
      impact: "HIGH", impactColor: COLORS.red,
      details: "The 8,500-seat arena opened in Dec 2024 and is already exceeding projections — 75 events in the first half of 2025, Rock Lobsters hockey breaking league attendance records. Classic Center's economic impact is on pace to hit $90M this year. The surrounding district is planned as a mixed-use development similar to The Battery in Cobb County.",
      investorAngle: "Properties within walking distance of the arena/Classic Center — especially duplexes or houses convertible to rentals — will benefit from event-night demand and the broader revitalization.",
    },
    {
      name: "Oconee Rivers Greenway Expansion",
      status: "FUNDED", statusColor: COLORS.blue,
      investment: "$7M via TSPLOST 2026",
      timeline: "Pending May 2026 voter approval",
      impact: "MODERATE", impactColor: COLORS.orange,
      details: "The Greenway was restored to TSPLOST 2026 after community advocacy. If voters approve in May, $7M will fund the first segment of the Middle Oconee River Greenway — connecting Forest Heights, Hampton Heights, Brooklyn, Sycamore Drive, Timothy Road, and Beechwood neighborhoods to Ben Burton Park.",
      investorAngle: "Properties near planned Greenway segments — particularly Beechwood, Timothy Road area, and Forest Heights — could see above-average appreciation as trail access improves walkability and desirability.",
    },
    {
      name: "UGA Enrollment Growth & Campus Expansion",
      status: "ACTIVE", statusColor: COLORS.green,
      investment: "$100M+ in campus construction",
      timeline: "New dorm Fall 2026; Med School 2026; Nursing 2027",
      impact: "HIGH", impactColor: COLORS.red,
      details: "UGA enrollment hit 43,146+ in fall 2024, growing ~845/year. A new 565-bed freshman dorm opens Fall 2026. The medical school is doubling class size to 120 in 2026. A new nursing school targets Fall 2027. Transfer enrollment surging — 3,283 new transfers in 2025.",
      investorAngle: "Transfer and grad students are the primary off-campus rental demand drivers. With 3,200+ transfers annually and growing, demand for 2-3BR rentals near campus will remain strong.",
    },
    {
      name: "Macon Highway (US 441) Corridor – Oconee",
      status: "EMERGING", statusColor: COLORS.accent,
      investment: "Private development",
      timeline: "Ongoing",
      impact: "MODERATE", impactColor: COLORS.orange,
      details: "The US 441/Macon Highway corridor between Athens Academy and Watkinsville is seeing major investment: Oconee Mercantile (planned mixed-use), Christian Brothers Automotive, and adjacent commercial rezoning. An 11-acre property at 8420 Macon Hwy is listed at $500K.",
      investorAngle: "This corridor represents the growth frontier between Athens and Watkinsville. The 4-unit property on Deni Court is a rare Oconee County multifamily find with excellent school zoning.",
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {projects.map((p) => (
        <div key={p.name} style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "22px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "8px" }}>
            <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: COLORS.text }}>{p.name}</h3>
            <div style={{ display: "flex", gap: "8px" }}>
              <Badge color={p.statusColor}>{p.status}</Badge>
              <Badge color={p.impactColor}>Impact: {p.impact}</Badge>
            </div>
          </div>
          <div style={{ display: "flex", gap: "24px", marginBottom: "14px", flexWrap: "wrap" }}>
            <div>
              <span style={{ fontSize: "11px", color: COLORS.textDim, textTransform: "uppercase" }}>Investment: </span>
              <span style={{ fontSize: "13px", color: COLORS.accent, fontWeight: 600 }}>{p.investment}</span>
            </div>
            <div>
              <span style={{ fontSize: "11px", color: COLORS.textDim, textTransform: "uppercase" }}>Timeline: </span>
              <span style={{ fontSize: "13px", color: COLORS.text }}>{p.timeline}</span>
            </div>
          </div>
          <p style={{ margin: "0 0 14px", fontSize: "13px", color: COLORS.textDim, lineHeight: 1.6 }}>{p.details}</p>
          <div style={{ background: COLORS.accent + "10", border: `1px solid ${COLORS.accent}30`, borderRadius: "6px", padding: "12px 16px" }}>
            <span style={{ fontSize: "11px", fontWeight: 700, color: COLORS.accent, textTransform: "uppercase", letterSpacing: "0.5px" }}>🎯 Investor Angle</span>
            <p style={{ margin: "6px 0 0", fontSize: "13px", color: COLORS.text, lineHeight: 1.5 }}>{p.investorAngle}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Tab: Strategy ────────────────────────────────────────────────────────────

function Strategy() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "18px" }}>
      <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "22px" }}>
        <h3 style={{ margin: "0 0 16px", fontSize: "15px", fontWeight: 700, color: COLORS.accent }}>WHY NOW</h3>
        <div style={{ fontSize: "13px", color: COLORS.textDim, lineHeight: 1.7 }}>
          {[
            "Market normalizing — inventory up 18% YoY, days on market up 21%. Buyers have leverage for the first time since pre-COVID.",
            "Mortgage rates settled near 6%, down from 7% in early 2025. Further improvement expected.",
            "Athens appreciation outperformed national avg (3.6% vs 2.3% in 2025), but growth is moderating to sustainable levels.",
            "Massive infrastructure investment (316 freeway, arena district) creating real catalysts for the next 5-10 years.",
            "UGA transfer + grad enrollment surging, creating sustained off-campus rental demand.",
            "Clarke County STR restrictions (Feb 2024) reduced short-term rental competition, stabilizing long-term rental demand.",
          ].map((item, i) => (
            <div key={i} style={{ display: "flex", gap: "10px", marginBottom: "12px" }}>
              <span style={{ color: COLORS.green, fontWeight: 700, flexShrink: 0 }}>✓</span>
              <span>{item}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "22px" }}>
        <h3 style={{ margin: "0 0 16px", fontSize: "15px", fontWeight: 700, color: COLORS.accent }}>RISKS TO WATCH</h3>
        <div style={{ fontSize: "13px", color: COLORS.textDim, lineHeight: 1.7 }}>
          {[
            "Georgia insurance costs rising statewide — get quotes before committing. Budget $100-$150/mo for SFH.",
            "Clarke County millage rate at 33.95 is substantial for non-homestead (rental) properties. No exemptions for investors.",
            "UGA new dorm (565 beds, Fall 2026) adds on-campus supply — could soften freshman-adjacent rental demand.",
            "Oconee County price point ($645K avg) may not pencil for cash flow — better as appreciation play.",
            "316 construction will cause 2-3 years of disruption before values fully reflect the improvement.",
            "National recession risk elevated in 2026 per UGA economic forecasters, though slow growth more likely than contraction.",
          ].map((item, i) => (
            <div key={i} style={{ display: "flex", gap: "10px", marginBottom: "12px" }}>
              <span style={{ color: COLORS.orange, fontWeight: 700, flexShrink: 0 }}>⚠</span>
              <span>{item}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}

// ── Documentation Modal ──────────────────────────────────────────────────────

function DocsModal({ onClose }) {
  const S = {
    overlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 1000, display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "24px 12px", overflowY: "auto" },
    box: { background: COLORS.card, borderRadius: "12px", border: `1px solid ${COLORS.border}`, width: "100%", maxWidth: "780px", padding: "clamp(16px, 3vw, 32px)", position: "relative", marginBottom: "24px" },
    h2: { margin: "0 0 20px", fontSize: "20px", fontWeight: 800, color: COLORS.text },
    h3: { margin: "24px 0 8px", fontSize: "13px", fontWeight: 700, color: COLORS.accent, textTransform: "uppercase", letterSpacing: "0.5px" },
    p: { margin: "0 0 10px", fontSize: "13px", color: COLORS.textDim, lineHeight: 1.7 },
    close: { position: "absolute", top: "16px", right: "16px", background: "none", border: "none", fontSize: "20px", cursor: "pointer", color: COLORS.textDim },
    table: { width: "100%", borderCollapse: "collapse", fontSize: "12px", marginBottom: "12px" },
    th: { textAlign: "left", padding: "6px 10px", background: COLORS.bg, color: COLORS.textDim, fontWeight: 700, borderBottom: `1px solid ${COLORS.border}` },
    td: { padding: "6px 10px", borderBottom: `1px solid ${COLORS.border}`, color: COLORS.text, verticalAlign: "top" },
  };
  return (
    <div style={S.overlay} onClick={onClose}>
      <div style={S.box} onClick={(e) => e.stopPropagation()}>
        <button style={S.close} onClick={onClose}>✕</button>
        <h2 style={S.h2}>Platform Documentation</h2>

        <h3 style={S.h3}>Purpose</h3>
        <p style={S.p}>Athens Real Estate Intelligence is a private investment research tool for identifying, scoring, and analyzing income-producing real estate in Clarke and Oconee Counties, Georgia. It aggregates public listing data, census demographics, traffic counts, zoning, flood zone, and proximity signals into a single composite score that prioritizes cash-flow quality.</p>
        <p style={S.p}>The platform is optimized for off-market awareness (distressed parcels), multifamily and single-family residential investments, and mid-term hold strategies (3–10 years) tied to Athens infrastructure growth catalysts.</p>

        <h3 style={S.h3}>Investment Strategy</h3>
        <p style={S.p}>Target properties that cash flow at purchase at current mortgage rates (~6.5–7%), have appreciation upside from UGA proximity or corridor development, and are priced at or below comparable sales. Secondary focus on distressed parcels where land value exceeds current-use value — particularly near SR-316, Prince Ave, and the new Arena District.</p>

        <h3 style={S.h3}>Composite Score Math (0–100)</h3>
        <table style={S.table}>
          <thead><tr><th style={S.th}>Component</th><th style={S.th}>Weight</th><th style={S.th}>How It's Calculated</th></tr></thead>
          <tbody>
            {[
              ["Cash Flow", "35%", "Monthly CF scored −$500→0 to +$500→100; blended 50/50 with CoC return (0%→0, 10%+→100)"],
              ["Appreciation", "25%", "Proximity score: weighted distance to UGA, downtown, Epps Bridge, schools, transit, greenway"],
              ["Entry Price", "20%", "List price vs. median of same-bedroom comps within 4 miles; 0.85× comps = 100, 1.15× = 0"],
              ["Demand", "10%", "60% proximity score + 40% GDOT traffic corridor signal (AADT-based, decays with distance)"],
              ["Risk", "10%", "Starts at 100; −30 if flood insurance required; −15 if pre-1980; −25 if pre-1960"],
            ].map(([c, w, d]) => <tr key={c}><td style={S.td}><strong>{c}</strong></td><td style={S.td}>{w}</td><td style={S.td}>{d}</td></tr>)}
          </tbody>
        </table>

        <h3 style={S.h3}>Rent Estimation</h3>
        <p style={S.p}><strong>Internal model:</strong> Starts from Athens market-average base rents by bedroom count (RentCafe/Zillow/RentHop, Mar 2026), adjusted by census tract median gross rent (ACS 5-year, ±35% clamp), UGA proximity premium (+15% ≤0.5mi, +8% ≤1.0mi), and Oconee school district premium (+8%). Output is a mid estimate ±12% range.</p>
        <p style={S.p}><strong>External sources:</strong> Craigslist Athens (/apa listings, percentile-based), Zumper market median (per-bedroom page), RentCafe market trends. All three scraped in parallel and cached for 1 hour. The displayed rent and the number used in scoring is the simple average of all source mids that return a result. The range shown is min–max across sources.</p>

        <h3 style={S.h3}>Cash Flow Model Assumptions</h3>
        <table style={S.table}>
          <thead><tr><th style={S.th}>Assumption</th><th style={S.th}>Default</th><th style={S.th}>Notes</th></tr></thead>
          <tbody>
            {[
              ["Down payment", "20%", "Conventional investment loan"],
              ["Mortgage rate", "7.0%", "Typical investor rate Mar 2026; adjustable in Cash Flow Calculator tab"],
              ["Loan term", "30 years", "Fixed amortization"],
              ["Property tax", "Clarke 1.17% / Oconee 0.85%", "Non-homestead (investor) millage; Clarke at 33.95 mills"],
              ["Insurance", "Clarke $1,200/yr / Oconee $1,400/yr", "Market estimate; get quotes — Georgia costs rising"],
              ["Vacancy", "8%", "~1 month/year; conservative for Athens market"],
              ["Maintenance", "1% of price/yr", "Standard rule of thumb"],
              ["Management", "8% of rent/mo", "Professional PM rate in Athens"],
            ].map(([a, d, n]) => <tr key={a}><td style={S.td}><strong>{a}</strong></td><td style={S.td}>{d}</td><td style={S.td}>{n}</td></tr>)}
          </tbody>
        </table>

        <h3 style={S.h3}>Distressed Parcel Scoring</h3>
        <p style={S.p}>Distress score (0–100) stacks public-record signals: tax delinquency (+30), tax sale list (+40), fi fa lien (+25), code violations (+15–20), absentee owner (+15), declining assessed value (+10), pre-1970 structure with no recent permits (+10). Properties scoring 50+ are classified high distress. Data is seeded from ACC public records; real-time scraping from qPublic and GSCCCA is the next phase.</p>

        <h3 style={S.h3}>Data Sources</h3>
        <p style={S.p}>Listing data: Redfin, Zillow, Compass, Homes.com, Movoto, Mashvisor · Rent data: RentCafe, Rent.com, RentHop, Zumper, Craigslist Athens · Demographics: ACS 5-Year Census (tract-level) · Traffic: GDOT AADT counts for major Athens corridors · Zoning: ACC Unified Development Ordinance GeoJSON · Flood: FEMA NFHL via ACC open data · Proximity: Haversine distance to UGA, downtown, Epps Bridge, schools, transit · Market context: Flagpole Athens, Athens CEO, 5Market Realty, ACC Gov, UGA Today</p>

        <h3 style={S.h3}>Limitations</h3>
        <p style={S.p}>All data as of March 31, 2026. Listing prices and availability change daily — verify before acting. Rent estimates are algorithmic and may not reflect current micro-market conditions. Distressed parcel data is seeded; not pulled live from county records. Nothing here is financial or legal advice.</p>
      </div>
    </div>
  );
}

// ── FAQ Modal ─────────────────────────────────────────────────────────────────

function FAQModal({ onClose }) {
  const [open, setOpen] = useState(null);
  const S = {
    overlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 1000, display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "24px 12px", overflowY: "auto" },
    box: { background: COLORS.card, borderRadius: "12px", border: `1px solid ${COLORS.border}`, width: "100%", maxWidth: "680px", padding: "clamp(16px, 3vw, 32px)", position: "relative", marginBottom: "24px" },
    h2: { margin: "0 0 20px", fontSize: "20px", fontWeight: 800, color: COLORS.text },
    close: { position: "absolute", top: "16px", right: "16px", background: "none", border: "none", fontSize: "20px", cursor: "pointer", color: COLORS.textDim },
    q: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 14px", cursor: "pointer", borderRadius: "6px", fontWeight: 600, fontSize: "13px", color: COLORS.text },
    a: { padding: "0 14px 12px", fontSize: "13px", color: COLORS.textDim, lineHeight: 1.7 },
    item: (isOpen) => ({ marginBottom: "6px", border: `1px solid ${isOpen ? COLORS.accent + "60" : COLORS.border}`, borderRadius: "8px", background: isOpen ? COLORS.accent + "08" : COLORS.card }),
  };
  const faqs = [
    ["How is the investment score calculated?", "The composite score (0–100) blends five components: Cash Flow (35%), Appreciation potential (25%), Entry Price vs. comps (20%), Demand signals (10%), and Risk (10%). Cash flow is the dominant driver — a property that doesn't pencil at current rates will score poorly regardless of location. See Documentation for the full math."],
    ["Why does a property show a score before I click it?", "All visible properties are batch-scored in a single background request when the page loads. This uses a parallel processing endpoint that scores all listings simultaneously rather than one at a time, so scores are ready before you expand a card."],
    ["What does the green/red dot next to the score mean?", "Green = positive monthly cash flow at the default assumptions (20% down, 7% rate, 8% vacancy, 8% management, 1% maintenance). Red = negative. Hover over the dot to see the exact monthly cash flow amount."],
    ["How accurate are the rent estimates?", "The internal model is calibrated to Athens March 2026 market data and adjusts for census tract, UGA proximity, and county. External sources (Craigslist, Zumper, RentCafe) are city-wide market medians by bedroom count — they don't reflect micro-neighborhood premiums. The averaged figure is a reasonable starting point; always verify with a local PM or active rental comps before underwriting."],
    ["What is a Distressed Parcel and why does it matter?", "A distressed parcel is a property with public-record signals of financial or physical deterioration: tax delinquency, fi fa liens, code violations, or absentee ownership. These properties rarely appear on Zillow or Redfin. The opportunity is buying at a significant discount to land value — especially in high-demand corridors where the land is worth more than the structure. The owner is often motivated."],
    ["What do the distressed tier colors mean?", "Red = Critical (score 70+): multiple serious signals, likely near tax sale. Orange = High (50–69): significant distress, owner likely motivated. Yellow = Watch (30–49): early signals, worth monitoring. Score is additive across signals — see Documentation for the full point breakdown."],
    ["How do I use this for outreach to distressed owners?", "The opportunity card shows the owner's mailing address (from qPublic county records). For absentee-owned properties, this is their out-of-state or out-of-area address. A direct mail campaign to the top 5–10 critical-distress parcels in target corridors is a high-ROI prospecting strategy."],
    ["What's the difference between Clarke and Oconee County properties?", "Clarke County has higher tax rates (33.95 mills, no investor exemptions), lower entry prices, and UGA-driven rental demand — better for cash flow. Oconee County has lower taxes, top-ranked schools, and higher median prices — better as an appreciation play or owner-occupied purchase. Most properties on this platform are Clarke County."],
    ["Why does the top-N slider exist?", "Ranking by composite score means the best cash-flow properties are always at the top. The slider lets you focus map pins on only the strongest candidates — e.g. 'show me the top 10 single-family homes' — reducing visual clutter on the map."],
    ["How current is the data?", "Listing data and market stats are as of March 31, 2026. Rent scrapers (Craigslist, Zumper, RentCafe) update live when you expand a card, cached for 1 hour. Census data is ACS 5-year estimates (2019–2023). GDOT traffic counts are from the most recent annual publication. Distressed parcel data is seeded and does not update automatically yet."],
    ["This isn't financial advice, right?", "Correct. This platform compiles public data and applies algorithmic scoring to aid research. It is not a substitute for professional appraisal, legal review, title search, physical inspection, or financial advice. Always verify all figures independently before making investment decisions."],
  ];
  return (
    <div style={S.overlay} onClick={onClose}>
      <div style={S.box} onClick={(e) => e.stopPropagation()}>
        <button style={S.close} onClick={onClose}>✕</button>
        <h2 style={S.h2}>Frequently Asked Questions</h2>
        {faqs.map(([q, a], i) => (
          <div key={i} style={S.item(open === i)} onClick={() => setOpen(open === i ? null : i)}>
            <div style={S.q}>
              <span>{q}</span>
              <span style={{ color: COLORS.accent, fontSize: "16px", marginLeft: "12px", flexShrink: 0 }}>{open === i ? "−" : "+"}</span>
            </div>
            {open === i && <div style={S.a}>{a}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Root ─────────────────────────────────────────────────────────────────────

export default function App() {
  const [activeTab, setActiveTab] = useState("map");
  const [showDocs, setShowDocs] = useState(false);
  const [showFAQ, setShowFAQ] = useState(false);
  const [dataAsOf, setDataAsOf] = useState("Mar 2026");
  const [calcSeed, setCalcSeed] = useState(null);

  const handleLoadCalculator = (seed) => {
    setCalcSeed(seed);
    setActiveTab("cashflow");
  };

  useEffect(() => {
    fetch(`${API_URL}/api/data-freshness`)
      .then((r) => r.json())
      .then((d) => { if (d.data_as_of) setDataAsOf(d.data_as_of); })
      .catch(() => {});
  }, []);

  return (
    <div style={{ background: COLORS.bg, minHeight: "100vh", color: COLORS.text, fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif" }}>
      {showDocs && <DocsModal onClose={() => setShowDocs(false)} />}
      {showFAQ && <FAQModal onClose={() => setShowFAQ(false)} />}
      <div style={{ maxWidth: "1440px", margin: "0 auto", padding: "20px 16px" }}>
        <div style={{ marginBottom: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px", flexWrap: "wrap" }}>
            <h1 style={{ margin: 0, fontSize: "clamp(16px, 2vw, 24px)", fontWeight: 800, color: COLORS.text, letterSpacing: "-0.5px", whiteSpace: "nowrap" }}>Athens Real Estate Intelligence</h1>
            <Badge>LIVE DATA — {dataAsOf}</Badge>
            <div style={{ marginLeft: "auto", display: "flex", gap: "8px", flexShrink: 0 }}>
              <button onClick={() => setShowDocs(true)} style={{ padding: "6px 14px", borderRadius: "6px", border: `1px solid ${COLORS.accent}`, background: "transparent", color: COLORS.accent, fontSize: "12px", fontWeight: 700, cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap" }}>Documentation</button>
              <button onClick={() => setShowFAQ(true)} style={{ padding: "6px 14px", borderRadius: "6px", border: `1px solid ${COLORS.accent}`, background: "transparent", color: COLORS.accent, fontSize: "12px", fontWeight: 700, cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap" }}>FAQ</button>
            </div>
          </div>
          <p style={{ margin: 0, fontSize: "13px", color: COLORS.textDim }}>Clarke County + Oconee County · Single-Family & Multifamily · Cash Flow Priority</p>
        </div>

        <div style={{ display: "flex", gap: "2px", marginBottom: "20px", background: COLORS.card, borderRadius: "8px", padding: "3px", border: `1px solid ${COLORS.border}`, overflowX: "auto" }}>
          {tabs.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              style={{ flex: "1 0 auto", padding: "10px 12px", background: activeTab === tab.id ? COLORS.accent : "transparent", color: activeTab === tab.id ? "#fff" : COLORS.textDim, border: "none", borderRadius: "6px", fontSize: "clamp(11px, 1.1vw, 13px)", fontWeight: 700, cursor: "pointer", transition: "all 0.15s", fontFamily: "inherit", letterSpacing: "0.3px", whiteSpace: "nowrap" }}>
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "map" && <PropertyMap onLoadCalculator={handleLoadCalculator} />}
        {activeTab === "overview" && <MarketOverview />}
        {activeTab === "cashflow" && <CashFlowCalc seed={calcSeed} />}
        {activeTab === "development" && <DevelopmentIntel />}
        {activeTab === "strategy" && <Strategy />}

        <div style={{ marginTop: "28px", padding: "16px", background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", fontSize: "11px", color: COLORS.textDim, lineHeight: 1.5 }}>
          <strong style={{ color: COLORS.accent }}>Data Sources:</strong> Zillow, Redfin, RentCafe, Rent.com, RentHop, Homes.com, Movoto, Mashvisor, Compass, Flagpole Athens, Athens CEO, 5Market Realty Market Reports, ACC Gov, GDOT, UGA Today, UGA Student Affairs, Friends of the Greenway ·{" "}
          <strong style={{ color: COLORS.accent }}>As of:</strong> March 31, 2026 ·{" "}
          <br />
          <strong style={{ color: COLORS.accent }}>Disclaimer:</strong> Research compiled from public sources. Not financial advice. Verify all data independently before making investment decisions.
        </div>
      </div>
    </div>
  );
}
