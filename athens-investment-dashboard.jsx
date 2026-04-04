import { useState, useEffect, useRef } from "react";

const COLORS = {
  bg: "#0f1419",
  card: "#1a2028",
  cardHover: "#1e2630",
  accent: "#d4a853",
  accentDim: "#b8923f",
  green: "#4ade80",
  red: "#ef4444",
  orange: "#fb923c",
  blue: "#60a5fa",
  text: "#e8e6e1",
  textDim: "#8b9299",
  border: "#2a3340",
  highlight: "#2a3340",
};

const tabs = [
  { id: "map", label: "📍 Property Map" },
  { id: "overview", label: "Market Overview" },
  { id: "cashflow", label: "Cash Flow Calculator" },
  { id: "development", label: "Development Intel" },
  { id: "strategy", label: "Strategy & Next Steps" },
];

const PROPERTIES = [
  {
    id: 1,
    address: "122 Park Ridge Ct, Athens 30605",
    price: "$305,000",
    type: "Duplex — 4BR/2BA",
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
    price: "~$271,000",
    type: "Duplex",
    confidence: "medium",
    rent: "~$1,800–2,000/mo (est. $1,000/side)",
    why: "Listed on Compass. West Athens / Normaltown area — near planned Middle Oconee Greenway expansion. 11-acre parcel is unusual and adds long-term land value. VERIFY: confirm unit layout, current rent roll, and exact asking price. If rents are near $1,000/side, cap rate could exceed 6%.",
    url: "https://www.compass.com/homes-for-sale/athens-ga/multi-family/",
    lat: 33.989970,
    lng: -83.470228,
  },
  {
    id: 5,
    address: "123 Garden Ln, Athens 30606",
    price: "~$250–300K (verify)",
    type: "SFH — 3BR/2BA",
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
    price: "Price TBD (est. $500K+)",
    type: "4-Unit Multifamily — 7BR/7.5BA",
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
    confidence: "speculative",
    rent: "$2,400–2,800/mo (premium location)",
    why: "Premium Five Points location — walking distance to UGA, Sanford Stadium, and downtown. Five Points has the highest median SFH price in Athens ($955K). At $550K this is a tough cash-flow play at current rates, but the neighborhood appreciation trend is the strongest in Athens. Best as a 5-10 year hold for equity growth rather than immediate cash flow.",
    url: "https://www.compass.com/homes-for-sale/athens-ga/multi-family/",
    lat: 33.932243,
    lng: -83.392020,
  },
];

function Badge({ children, color = COLORS.accent }) {
  return (
    <span
      style={{
        background: color + "18",
        color: color,
        padding: "3px 10px",
        borderRadius: "4px",
        fontSize: "11px",
        fontWeight: 600,
        letterSpacing: "0.5px",
        textTransform: "uppercase",
        border: `1px solid ${color}30`,
      }}
    >
      {children}
    </span>
  );
}

function StatCard({ label, value, sub, trend }) {
  return (
    <div
      style={{
        background: COLORS.card,
        border: `1px solid ${COLORS.border}`,
        borderRadius: "8px",
        padding: "18px",
        flex: "1 1 180px",
      }}
    >
      <div
        style={{ fontSize: "11px", color: COLORS.textDim, fontWeight: 600, letterSpacing: "0.8px", textTransform: "uppercase", marginBottom: "8px" }}
      >
        {label}
      </div>
      <div style={{ fontSize: "26px", fontWeight: 700, color: COLORS.text, fontFamily: "'DM Sans', sans-serif" }}>
        {value}
        {trend && (
          <span
            style={{
              fontSize: "13px",
              fontWeight: 600,
              marginLeft: "8px",
              color: trend.startsWith("+") || trend.startsWith("↑") ? COLORS.green : trend.startsWith("-") || trend.startsWith("↓") ? COLORS.red : COLORS.textDim,
            }}
          >
            {trend}
          </span>
        )}
      </div>
      {sub && <div style={{ fontSize: "12px", color: COLORS.textDim, marginTop: "4px" }}>{sub}</div>}
    </div>
  );
}

function MarketOverview() {
  return (
    <div>
      <div style={{ display: "flex", gap: "14px", flexWrap: "wrap", marginBottom: "28px" }}>
        <StatCard label="Median List Price" value="$375K" trend="↓ 2% YoY" sub="Clarke + Oconee — Mar 2026" />
        <StatCard label="Zillow Home Value" value="$307K" trend="+5.1% YoY" sub="Athens city typical value" />
        <StatCard label="Avg Days on Market" value="57" trend="+21% YoY" sub="More negotiating leverage" />
        <StatCard label="Active Listings" value="486+" trend="+143 vs last yr" sub="Clarke + Oconee combined" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "18px" }}>
        <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "22px" }}>
          <h3 style={{ margin: "0 0 16px", fontSize: "15px", fontWeight: 700, color: COLORS.accent, letterSpacing: "0.5px" }}>
            RENTAL MARKET SNAPSHOT
          </h3>
          {[
            { type: "Studio", rent: "$1,034–$1,100", sqft: "~423 sq ft" },
            { type: "1-Bedroom", rent: "$1,020–$1,350", sqft: "~701 sq ft" },
            { type: "2-Bedroom", rent: "$1,289–$1,510", sqft: "~1,062 sq ft" },
            { type: "3-Bedroom", rent: "$1,631–$2,043", sqft: "~1,345 sq ft" },
            { type: "4-Bedroom", rent: "$2,300–$2,500", sqft: "varies" },
          ].map((r) => (
            <div
              key={r.type}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "10px 0",
                borderBottom: `1px solid ${COLORS.border}`,
              }}
            >
              <div>
                <span style={{ fontWeight: 600, color: COLORS.text }}>{r.type}</span>
                <span style={{ color: COLORS.textDim, fontSize: "12px", marginLeft: "8px" }}>{r.sqft}</span>
              </div>
              <span style={{ fontWeight: 700, color: COLORS.green, fontFamily: "'DM Sans', sans-serif" }}>{r.rent}</span>
            </div>
          ))}
          <div style={{ marginTop: "14px", fontSize: "12px", color: COLORS.textDim, lineHeight: 1.5 }}>
            Sources: RentCafe, Zillow, Rent.com, RentHop — Mar 2026. Athens rents are ~22% below the national avg. 
            1BR rents rose 13-17% YoY per RentHop. 59% of Athens households are renters.
          </div>
        </div>

        <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "22px" }}>
          <h3 style={{ margin: "0 0 16px", fontSize: "15px", fontWeight: 700, color: COLORS.accent, letterSpacing: "0.5px" }}>
            MARKET CONDITIONS
          </h3>
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

      <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "22px", marginTop: "18px" }}>
        <h3 style={{ margin: "0 0 14px", fontSize: "15px", fontWeight: 700, color: COLORS.accent, letterSpacing: "0.5px" }}>
          INVESTMENT-GRADE LISTING TYPES TO WATCH
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "14px" }}>
          {[
            {
              title: "In-Town Duplexes",
              price: "$225K–$335K",
              rents: "$1,000/side",
              note: "Five Points, near campus. One listed at $271K on Compass. Brick duplex w/ granite upgrades near UGA + Loop 10.",
              badge: "HIGH YIELD",
              badgeColor: COLORS.green,
            },
            {
              title: "Triplex — Oconee River",
              price: "$335K–$500K",
              rents: "$1,100–$1,400/unit",
              note: "Tri-plex on 2.22 acres on Oconee River. 3 units (1BR+2BR+1BR). Market rents $3,500+ combined.",
              badge: "FEATURED",
              badgeColor: COLORS.orange,
            },
            {
              title: "3BR SFH Near Campus",
              price: "$250K–$375K",
              rents: "$1,650–$1,900",
              note: "Tenant-occupied through July 2026. Updated kitchens, walking distance to UGA. Garden Lane area.",
              badge: "TURNKEY",
              badgeColor: COLORS.blue,
            },
          ].map((listing) => (
            <div
              key={listing.title}
              style={{
                background: COLORS.bg,
                border: `1px solid ${COLORS.border}`,
                borderRadius: "8px",
                padding: "16px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                <span style={{ fontWeight: 700, color: COLORS.text, fontSize: "14px" }}>{listing.title}</span>
                <Badge color={listing.badgeColor}>{listing.badge}</Badge>
              </div>
              <div style={{ fontSize: "22px", fontWeight: 700, color: COLORS.accent, marginBottom: "4px" }}>{listing.price}</div>
              <div style={{ fontSize: "13px", color: COLORS.green, marginBottom: "10px" }}>Est. rent: {listing.rents}</div>
              <div style={{ fontSize: "12px", color: COLORS.textDim, lineHeight: 1.5 }}>{listing.note}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CashFlowCalc() {
  const [price, setPrice] = useState(275000);
  const [down, setDown] = useState(25);
  const [rate, setRate] = useState(6.5);
  const [rent, setRent] = useState(1800);
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
  const cashOnCash = ((annualCashFlow) / (price * down / 100)) * 100;
  const capRate = ((rent * 12 - (monthlyTax + insurance + monthlyMaint) * 12) / price) * 100;

  const inputStyle = {
    background: COLORS.bg,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "6px",
    padding: "8px 12px",
    color: COLORS.text,
    fontSize: "14px",
    fontWeight: 600,
    width: "100%",
    boxSizing: "border-box",
    fontFamily: "'DM Sans', sans-serif",
  };

  const labelStyle = {
    fontSize: "11px",
    color: COLORS.textDim,
    fontWeight: 600,
    letterSpacing: "0.5px",
    textTransform: "uppercase",
    marginBottom: "4px",
    display: "block",
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "22px" }}>
      <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "22px" }}>
        <h3 style={{ margin: "0 0 18px", fontSize: "15px", fontWeight: 700, color: COLORS.accent }}>PROPERTY INPUTS</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
          <div>
            <label style={labelStyle}>Purchase Price ($)</label>
            <input type="number" value={price} onChange={(e) => setPrice(+e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Down Payment (%)</label>
            <input type="number" value={down} onChange={(e) => setDown(+e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Interest Rate (%)</label>
            <input type="number" step="0.1" value={rate} onChange={(e) => setRate(+e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Monthly Rent ($)</label>
            <input type="number" value={rent} onChange={(e) => setRent(+e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Annual Property Tax ($)</label>
            <input type="number" value={tax} onChange={(e) => setTax(+e.target.value)} style={inputStyle} placeholder="Auto: Clarke 33.95 mills" />
          </div>
          <div>
            <label style={labelStyle}>Monthly Insurance ($)</label>
            <input type="number" value={insurance} onChange={(e) => setInsurance(+e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Maintenance (% of rent)</label>
            <input type="number" value={maintenance} onChange={(e) => setMaintenance(+e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Vacancy (% of rent)</label>
            <input type="number" value={vacancy} onChange={(e) => setVacancy(+e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Management (% of rent)</label>
            <input type="number" value={mgmt} onChange={(e) => setMgmt(+e.target.value)} style={inputStyle} />
          </div>
        </div>
        <div style={{ marginTop: "14px", fontSize: "11px", color: COLORS.textDim }}>
          Tax auto-calculates at Clarke County's 33.95 mills on 40% assessed value if left at $0. Override for Oconee County properties.
        </div>
      </div>

      <div>
        <div style={{ display: "flex", gap: "14px", marginBottom: "18px", flexWrap: "wrap" }}>
          <StatCard
            label="Monthly Cash Flow"
            value={`$${Math.round(cashFlow).toLocaleString()}`}
            trend={cashFlow >= 0 ? "✓ Positive" : "✗ Negative"}
          />
          <StatCard label="Cash-on-Cash Return" value={`${cashOnCash.toFixed(1)}%`} sub={`On $${(price * down / 100).toLocaleString()} invested`} />
        </div>
        <div style={{ display: "flex", gap: "14px", marginBottom: "18px", flexWrap: "wrap" }}>
          <StatCard label="Cap Rate" value={`${capRate.toFixed(1)}%`} sub="NOI / Purchase Price" />
          <StatCard label="Monthly Mortgage" value={`$${Math.round(mortgage).toLocaleString()}`} sub={`${nPayments / 12}yr fixed on $${Math.round(loanAmt).toLocaleString()}`} />
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
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              borderTop: `2px solid ${COLORS.accent}`,
              marginTop: "10px",
              paddingTop: "10px",
            }}
          >
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

function DevelopmentIntel() {
  const projects = [
    {
      name: "SR 316 Freeway Conversion",
      status: "ACTIVE",
      statusColor: COLORS.green,
      investment: "$829M+ total program",
      timeline: "Multiple phases through ~2030",
      impact: "HIGH",
      impactColor: COLORS.red,
      details:
        "GDOT is converting the 40-mile SR 316 corridor from an at-grade highway to a limited-access freeway with interchanges. Three Oconee County contracts were just awarded in Jan 2025 (Dials Mill Extension interchange). This shrinks the Atlanta commute gap — properties along the 316 corridor in Oconee and Barrow counties become significantly more accessible to Atlanta job centers. Expect property values to rise in Bogart, Statham, and the western Oconee corridor as construction progresses.",
      investorAngle: "Buy in the 316 corridor now before interchange completions drive values up. Bogart and western Oconee are the sweet spot — still affordable, but directly benefiting from improved access.",
    },
    {
      name: "Akins Ford Arena District",
      status: "PLANNING",
      statusColor: COLORS.orange,
      investment: "$170M arena (complete) + district TBD",
      timeline: "Arena open Dec 2024; district development 12–48 months",
      impact: "HIGH",
      impactColor: COLORS.red,
      details:
        "The 8,500-seat arena opened in Dec 2024 and is already exceeding projections — 75 events in the first half of 2025, Rock Lobsters hockey breaking league attendance records. Classic Center's economic impact is on pace to hit $90M this year (up from $10M during COVID). The surrounding district is planned as a mixed-use development similar to The Battery in Cobb County. A new Arena District Steering Committee formed after the original master developer Mallory & Evans dropped out. Phase 1 planning is underway with Accenture consulting on scope.",
      investorAngle: "Properties within walking distance of the arena/Classic Center — especially duplexes or houses convertible to rentals — will benefit from event-night demand and the broader revitalization. The College Square $7M beautification project adds further upside to downtown rentals.",
    },
    {
      name: "Oconee Rivers Greenway Expansion",
      status: "FUNDED",
      statusColor: COLORS.blue,
      investment: "$7M via TSPLOST 2026",
      timeline: "Pending May 2026 voter approval",
      impact: "MODERATE",
      impactColor: COLORS.orange,
      details:
        "The Greenway was restored to TSPLOST 2026 after community advocacy. If voters approve in May, $7M will fund the first segment of the Middle Oconee River Greenway — connecting Forest Heights, Hampton Heights, Brooklyn, Sycamore Drive, Timothy Road, and Beechwood neighborhoods to Ben Burton Park and Beech Haven Park. Currently only ~10% of the planned network has been built in 30 years. A separate expansion along MLK Jr. Parkway from North Ave to 1st Street is already in design.",
      investorAngle: "Properties near planned Greenway segments — particularly Beechwood, Timothy Road area, and Forest Heights — could see above-average appreciation as trail access improves walkability and desirability. The MLK Parkway extension enhances east-side connectivity.",
    },
    {
      name: "UGA Enrollment Growth & Campus Expansion",
      status: "ACTIVE",
      statusColor: COLORS.green,
      investment: "$100M+ in campus construction",
      timeline: "New dorm Fall 2026; Med School 2026; Nursing 2027",
      impact: "HIGH",
      impactColor: COLORS.red,
      details:
        "UGA enrollment hit 43,146+ in fall 2024, growing ~845/year (accelerating). Fall 2025 saw record Georgia residents. A new 565-bed freshman dorm and dining/wellness center open Fall 2026. The medical school is doubling class size to 120 in 2026. A new nursing school targets Fall 2027. A BCM-site mixed-use development (apartments, parking, retail) is planned by 2027 on Lumpkin Street. Transfer enrollment is surging — 3,283 new transfers in 2025, with a goal of one transfer per every two freshmen.",
      investorAngle: "Transfer and grad students are the primary off-campus rental demand drivers — they don't live in dorms. With 3,200+ transfers annually and growing, demand for 2-3BR rentals near campus will remain strong. The medical and nursing school expansions add high-income professional renters to the pool.",
    },
    {
      name: "Macon Highway (US 441) Corridor – Oconee",
      status: "EMERGING",
      statusColor: COLORS.accent,
      investment: "Private development",
      timeline: "Ongoing",
      impact: "MODERATE",
      impactColor: COLORS.orange,
      details:
        "The US 441/Macon Highway corridor between Athens Academy and Watkinsville is seeing major investment: Oconee Mercantile (planned mixed-use), Christian Brothers Automotive, and adjacent commercial rezoning. An 11-acre property at 8420 Macon Hwy is listed at $500K. A 1020 Deni Court multifamily property (4 units, 7BR/7.5BA) is available in the North Oconee school zone near Hodges Mill Road.",
      investorAngle: "This corridor represents the growth frontier between Athens and Watkinsville. Commercial development lifts residential values. The 4-unit property on Deni Court is a rare Oconee County multifamily find with excellent school zoning.",
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
          <div
            style={{
              background: COLORS.accent + "10",
              border: `1px solid ${COLORS.accent}30`,
              borderRadius: "6px",
              padding: "12px 16px",
            }}
          >
            <span style={{ fontSize: "11px", fontWeight: 700, color: COLORS.accent, textTransform: "uppercase", letterSpacing: "0.5px" }}>
              🎯 Investor Angle
            </span>
            <p style={{ margin: "6px 0 0", fontSize: "13px", color: COLORS.text, lineHeight: 1.5 }}>{p.investorAngle}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function Strategy() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "18px" }}>
      <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "22px" }}>
        <h3 style={{ margin: "0 0 16px", fontSize: "15px", fontWeight: 700, color: COLORS.accent }}>WHY NOW</h3>
        <div style={{ fontSize: "13px", color: COLORS.textDim, lineHeight: 1.7 }}>
          {[
            "Market normalizing — inventory up 18% YoY, days on market up 21%. Buyers have leverage for the first time since pre-COVID.",
            "Mortgage rates settled near 6%, down from 7% in early 2025. Further improvement expected.",
            "Athens appreciation outperformed national avg (3.6% vs 2.3% in 2025), but growth is moderating to sustainable levels.",
            "Massive infrastructure investment (316 freeway, arena district) creating real catalysts for the next 5-10 years.",
            "UGA transfer + grad enrollment surging, creating sustained off-campus rental demand independent of freshman dorm capacity.",
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
            "UGA new dorm (565 beds, Fall 2026) adds on-campus supply — doesn't affect transfers/grads but could soften freshman-adjacent rental demand.",
            "Oconee County price point ($645K avg) may not pencil for cash flow — better as appreciation play.",
            "316 construction will cause 2-3 years of disruption in the corridor before values fully reflect the improvement.",
            "National recession risk elevated in 2026 per UGA economic forecasters, though slow growth more likely than contraction.",
          ].map((item, i) => (
            <div key={i} style={{ display: "flex", gap: "10px", marginBottom: "12px" }}>
              <span style={{ color: COLORS.orange, fontWeight: 700, flexShrink: 0 }}>⚠</span>
              <span>{item}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ gridColumn: "1 / -1", background: COLORS.card, border: `1px solid ${COLORS.accent}40`, borderRadius: "8px", padding: "22px" }}>
        <h3 style={{ margin: "0 0 16px", fontSize: "15px", fontWeight: 700, color: COLORS.accent }}>IMMEDIATE ACTION PLAN</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px" }}>
          {[
            {
              step: "1",
              title: "This Week",
              items: [
                "Search Zillow/Redfin for duplexes under $350K in Clarke County — filter by 'investment property'",
                "Run cash flow calc on any listings with tenant-occupied units (known rent numbers)",
                "Check the Five Points duplex (~$271K on Compass) and the brick duplex with $1,000/side rents",
                "Get pre-approved — a pre-approval letter lets you move fast in this market",
              ],
            },
            {
              step: "2",
              title: "This Month",
              items: [
                "Drive the 316 corridor from Bogart to the Loop 10 interchange — note construction progress and surrounding development",
                "Tour the arena district area on foot — identify nearby rental properties",
                "Get 3 insurance quotes for a sample property to validate your expense assumptions",
                "Connect with a local investor-friendly agent (5Market Realty, Hank Bailey RE/MAX are active in this space)",
              ],
            },
            {
              step: "3",
              title: "Ongoing",
              items: [
                "Ask Claude for a refreshed research session monthly — new listings, market data updates, development news",
                "Track TSPLOST 2026 vote result (May 2026) for Greenway funding confirmation",
                "Monitor arena district steering committee announcements for development partner selection",
                "Watch for UGA medical school preliminary accreditation decision (expected Feb 2026)",
              ],
            },
          ].map((phase) => (
            <div key={phase.step} style={{ background: COLORS.bg, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "16px" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  marginBottom: "12px",
                }}
              >
                <div
                  style={{
                    width: "28px",
                    height: "28px",
                    borderRadius: "50%",
                    background: COLORS.accent,
                    color: COLORS.bg,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 800,
                    fontSize: "13px",
                  }}
                >
                  {phase.step}
                </div>
                <span style={{ fontWeight: 700, color: COLORS.text, fontSize: "14px" }}>{phase.title}</span>
              </div>
              {phase.items.map((item, i) => (
                <div key={i} style={{ fontSize: "12px", color: COLORS.textDim, lineHeight: 1.5, padding: "4px 0", borderBottom: i < phase.items.length - 1 ? `1px solid ${COLORS.border}` : "none" }}>
                  {item}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PropertyMap() {
  const [selected, setSelected] = useState(null);
  const [filter, setFilter] = useState("all");
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);

  const filtered = filter === "all" ? PROPERTIES : PROPERTIES.filter((p) => p.confidence === filter);
  const confidenceColors = { high: COLORS.green, medium: "#facc15", speculative: COLORS.orange };
  const confidenceLabels = { high: "High Confidence", medium: "Verify Details", speculative: "Speculative Upside" };

  useEffect(() => {
    // Load Leaflet CSS
    if (!document.getElementById("leaflet-css")) {
      const link = document.createElement("link");
      link.id = "leaflet-css";
      link.rel = "stylesheet";
      link.href = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css";
      document.head.appendChild(link);
    }
    // Load Leaflet JS
    const loadLeaflet = () =>
      new Promise((resolve) => {
        if (window.L) return resolve(window.L);
        const script = document.createElement("script");
        script.src = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js";
        script.onload = () => resolve(window.L);
        document.head.appendChild(script);
      });

    loadLeaflet().then((L) => {
      if (mapInstanceRef.current) return; // already initialized
      const map = L.map(mapRef.current, {
        center: [33.945, -83.40],
        zoom: 12,
        zoomControl: true,
        attributionControl: true,
      });

      // Use OpenStreetMap standard tiles
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(map);

      mapInstanceRef.current = map;

      // Add all property markers
      PROPERTIES.forEach((p) => {
        const color = confidenceColors[p.confidence];
        const icon = L.divIcon({
          className: "",
          html: `<div style="
            width:28px;height:28px;border-radius:50%;
            background:${color};
            border:3px solid #fff;
            display:flex;align-items:center;justify-content:center;
            font-size:12px;font-weight:800;color:#0f1419;
            box-shadow:0 2px 8px rgba(0,0,0,0.4), 0 0 12px ${color}60;
            cursor:pointer;
          ">${p.id}</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });

        const popupContent = `
          <div style="font-family:'DM Sans',system-ui,sans-serif;min-width:240px;max-width:280px;">
            <div style="font-size:14px;font-weight:800;color:#1a1a1a;margin-bottom:4px;">${p.address}</div>
            <div style="font-size:18px;font-weight:800;color:#b8923f;margin-bottom:6px;">${p.price}</div>
            <div style="font-size:11px;color:#555;margin-bottom:4px;">${p.type}</div>
            <div style="font-size:11px;color:#16a34a;font-weight:700;margin-bottom:8px;">Est. rent: ${p.rent}</div>
            <div style="font-size:11px;color:#444;line-height:1.5;margin-bottom:10px;border-top:1px solid #ddd;padding-top:8px;">${p.why.substring(0, 200)}${p.why.length > 200 ? "..." : ""}</div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;">
              <a href="${p.url}" target="_blank" rel="noopener" style="
                padding:5px 12px;background:#d4a853;color:#0f1419;border-radius:4px;
                font-size:11px;font-weight:700;text-decoration:none;
              ">View Listing →</a>
              <a href="https://www.google.com/maps/search/?api=1&query=${p.lat},${p.lng}" target="_blank" rel="noopener" style="
                padding:5px 12px;border:1px solid #d4a853;color:#d4a853;border-radius:4px;
                font-size:11px;font-weight:700;text-decoration:none;
              ">Google Maps ↗</a>
              <a href="https://www.zillow.com/homes/${encodeURIComponent(p.address.split(",")[0])}_rb/" target="_blank" rel="noopener" style="
                padding:5px 12px;border:1px solid #60a5fa;color:#60a5fa;border-radius:4px;
                font-size:11px;font-weight:700;text-decoration:none;
              ">Zillow ↗</a>
            </div>
          </div>
        `;

        const marker = L.marker([p.lat, p.lng], { icon })
          .addTo(map)
          .bindPopup(popupContent, { maxWidth: 300, className: "custom-popup" });

        markersRef.current.push({ id: p.id, marker, confidence: p.confidence });
      });

      // Style the popups
      const style = document.createElement("style");
      style.textContent = `
        .custom-popup .leaflet-popup-content-wrapper {
          background: #fff;
          border-radius: 8px;
          box-shadow: 0 8px 30px rgba(0,0,0,0.3);
          padding: 0;
        }
        .custom-popup .leaflet-popup-content { margin: 14px; }
        .custom-popup .leaflet-popup-tip { background: #fff; }
        .leaflet-control-attribution { font-size: 9px !important; opacity: 0.6; }
        .leaflet-control-zoom a {
          background: #fff !important;
          color: #333 !important;
          border-color: #ccc !important;
        }
        .leaflet-control-zoom a:hover { background: #f0f0f0 !important; }
      `;
      document.head.appendChild(style);
    });

    return () => {
      // Cleanup on unmount
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        markersRef.current = [];
      }
    };
  }, []);

  // Update marker visibility when filter changes
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    markersRef.current.forEach(({ marker, confidence }) => {
      if (filter === "all" || confidence === filter) {
        marker.addTo(mapInstanceRef.current);
      } else {
        marker.remove();
      }
    });
  }, [filter]);

  // Pan to selected property
  useEffect(() => {
    if (!mapInstanceRef.current || !selected) return;
    const p = PROPERTIES.find((prop) => prop.id === selected);
    if (p) {
      mapInstanceRef.current.setView([p.lat, p.lng], 14, { animate: true });
      const m = markersRef.current.find((mk) => mk.id === selected);
      if (m) m.marker.openPopup();
    }
  }, [selected]);

  return (
    <div>
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px", alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontSize: "12px", color: COLORS.textDim, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>Filter:</span>
        {[
          { key: "all", label: "All Properties" },
          { key: "high", label: "🟢 High Confidence" },
          { key: "medium", label: "🟡 Verify Details" },
          { key: "speculative", label: "🟠 Speculative" },
        ].map((f) => (
          <button
            key={f.key}
            onClick={() => { setFilter(f.key); setSelected(null); }}
            style={{
              padding: "6px 14px",
              borderRadius: "6px",
              border: `1px solid ${filter === f.key ? COLORS.accent : COLORS.border}`,
              background: filter === f.key ? COLORS.accent + "20" : "transparent",
              color: filter === f.key ? COLORS.accent : COLORS.textDim,
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: "16px" }}>
        {/* Leaflet map container */}
        <div
          ref={mapRef}
          style={{
            height: "580px",
            borderRadius: "8px",
            border: `1px solid ${COLORS.border}`,
            overflow: "hidden",
            zIndex: 0,
          }}
        />

        {/* Property card list */}
        <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "580px", overflowY: "auto", paddingRight: "4px" }}>
          {filtered.map((p) => {
            const isOpen = selected === p.id;
            const dotColor = confidenceColors[p.confidence];
            return (
              <div
                key={p.id}
                onClick={() => setSelected(isOpen ? null : p.id)}
                style={{
                  background: isOpen ? COLORS.cardHover : COLORS.card,
                  border: `1px solid ${isOpen ? dotColor + "60" : COLORS.border}`,
                  borderRadius: "8px",
                  padding: "14px",
                  cursor: "pointer",
                  transition: "all 0.15s",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      <div style={{
                        width: "22px", height: "22px", borderRadius: "50%", background: dotColor, flexShrink: 0,
                        boxShadow: `0 0 6px ${dotColor}60`, display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: "11px", fontWeight: 800, color: COLORS.bg,
                      }}>{p.id}</div>
                      <span style={{ fontWeight: 700, fontSize: "13px", color: COLORS.text }}>{p.address}</span>
                    </div>
                    <div style={{ display: "flex", gap: "12px", marginLeft: "30px" }}>
                      <span style={{ fontSize: "16px", fontWeight: 800, color: COLORS.accent }}>{p.price}</span>
                      <span style={{ fontSize: "12px", color: COLORS.textDim, alignSelf: "center" }}>{p.type}</span>
                    </div>
                  </div>
                </div>

                {isOpen && (
                  <div style={{ marginTop: "12px", marginLeft: "30px", borderTop: `1px solid ${COLORS.border}`, paddingTop: "12px" }}>
                    <div style={{ marginBottom: "10px" }}>
                      <span style={{ fontSize: "11px", color: COLORS.textDim, textTransform: "uppercase", fontWeight: 600 }}>Est. Rent: </span>
                      <span style={{ fontSize: "13px", color: COLORS.green, fontWeight: 700 }}>{p.rent}</span>
                    </div>
                    <p style={{ margin: "0 0 12px", fontSize: "12px", color: COLORS.textDim, lineHeight: 1.6 }}>{p.why}</p>
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                      <a href={p.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
                        style={{
                          display: "inline-flex", alignItems: "center", gap: "5px", padding: "6px 14px",
                          background: COLORS.accent, color: COLORS.bg, borderRadius: "5px",
                          fontSize: "12px", fontWeight: 700, textDecoration: "none", fontFamily: "inherit",
                        }}>View Listing →</a>
                      <a href={`https://www.google.com/maps/search/?api=1&query=${p.lat},${p.lng}`} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
                        style={{
                          display: "inline-flex", alignItems: "center", gap: "5px", padding: "6px 14px",
                          background: "transparent", color: COLORS.accent, border: `1px solid ${COLORS.accent}40`,
                          borderRadius: "5px", fontSize: "12px", fontWeight: 700, textDecoration: "none", fontFamily: "inherit",
                        }}>Google Maps ↗</a>
                      <a href={`https://www.zillow.com/homes/${encodeURIComponent(p.address.split(",")[0])}_rb/`} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
                        style={{
                          display: "inline-flex", alignItems: "center", gap: "5px", padding: "6px 14px",
                          background: "transparent", color: COLORS.blue, border: `1px solid ${COLORS.blue}40`,
                          borderRadius: "5px", fontSize: "12px", fontWeight: 700, textDecoration: "none", fontFamily: "inherit",
                        }}>Zillow ↗</a>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ marginTop: "16px", background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: "8px", padding: "16px" }}>
        <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
          {Object.entries(confidenceLabels).map(([key, label]) => (
            <div key={key} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div style={{ width: "12px", height: "12px", borderRadius: "50%", background: confidenceColors[key], boxShadow: `0 0 6px ${confidenceColors[key]}40` }} />
              <div>
                <span style={{ fontSize: "12px", fontWeight: 700, color: COLORS.text }}>{label}</span>
                <span style={{ fontSize: "11px", color: COLORS.textDim, marginLeft: "6px" }}>
                  {key === "high" && "— Strong cash flow math, verified data, actionable now"}
                  {key === "medium" && "— Promising but price/rent/condition needs confirmation"}
                  {key === "speculative" && "— Appreciation play or corridor bet, not pure cash flow"}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState("map");

  return (
    <div
      style={{
        background: COLORS.bg,
        minHeight: "100vh",
        color: COLORS.text,
        fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif",
        padding: "0",
      }}
    >
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "32px 24px" }}>
        <div style={{ marginBottom: "28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "6px" }}>
            <h1
              style={{
                margin: 0,
                fontSize: "24px",
                fontWeight: 800,
                color: COLORS.text,
                letterSpacing: "-0.5px",
              }}
            >
              Athens GA Investment Research
            </h1>
            <Badge>LIVE DATA — MAR 2026</Badge>
          </div>
          <p style={{ margin: 0, fontSize: "13px", color: COLORS.textDim }}>
            Clarke County + Oconee County · Single-Family & Multifamily · Cash Flow Priority
          </p>
        </div>

        <div
          style={{
            display: "flex",
            gap: "2px",
            marginBottom: "24px",
            background: COLORS.card,
            borderRadius: "8px",
            padding: "3px",
            border: `1px solid ${COLORS.border}`,
          }}
        >
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                flex: 1,
                padding: "10px 16px",
                background: activeTab === tab.id ? COLORS.accent : "transparent",
                color: activeTab === tab.id ? COLORS.bg : COLORS.textDim,
                border: "none",
                borderRadius: "6px",
                fontSize: "13px",
                fontWeight: 700,
                cursor: "pointer",
                transition: "all 0.15s",
                fontFamily: "inherit",
                letterSpacing: "0.3px",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "map" && <PropertyMap />}
        {activeTab === "overview" && <MarketOverview />}
        {activeTab === "cashflow" && <CashFlowCalc />}
        {activeTab === "development" && <DevelopmentIntel />}
        {activeTab === "strategy" && <Strategy />}

        <div
          style={{
            marginTop: "28px",
            padding: "16px",
            background: COLORS.card,
            border: `1px solid ${COLORS.border}`,
            borderRadius: "8px",
            fontSize: "11px",
            color: COLORS.textDim,
            lineHeight: 1.5,
          }}
        >
          <strong style={{ color: COLORS.accent }}>Data Sources:</strong> Zillow, Redfin, RentCafe, Rent.com, RentHop, Homes.com, Movoto, Mashvisor, Compass, Flagpole Athens, Athens CEO, 
          5Market Realty Market Reports, ACC Gov, GDOT, UGA Today, UGA Student Affairs, Friends of the Greenway · <strong style={{ color: COLORS.accent }}>As of:</strong> March 31, 2026 · 
          <strong style={{ color: COLORS.accent }}>Refresh:</strong> Start a new Claude conversation and ask for an updated Athens investment research session. Data is live at time of search, not auto-refreshing.
          <br /><strong style={{ color: COLORS.accent }}>Disclaimer:</strong> This is research compiled from public sources. Not financial advice. Verify all data independently before making investment decisions. Consult a licensed real estate agent, CPA, and attorney.
        </div>
      </div>
    </div>
  );
}
