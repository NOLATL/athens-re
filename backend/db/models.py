"""SQLAlchemy models for the Athens RE investment platform."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    source = Column(String(50))          # "redfin" | "zillow"
    source_id = Column(String(100), unique=True)
    address = Column(String(255))
    city = Column(String(100))
    county = Column(String(50))          # "clarke" | "oconee"
    zip_code = Column(String(10))
    lat = Column(Float)
    lng = Column(Float)

    # Listing data
    list_price = Column(Integer)
    price_per_sqft = Column(Float)
    sqft = Column(Integer)
    bedrooms = Column(Integer)
    bathrooms = Column(Float)
    property_type = Column(String(50))   # sfh | duplex | triplex | quadplex | condo
    year_built = Column(Integer)
    days_on_market = Column(Integer)
    original_list_price = Column(Integer)
    price_reductions = Column(Integer, default=0)

    # Computed / enriched
    estimated_rent = Column(Integer)
    rent_confidence = Column(String(20))
    monthly_cash_flow = Column(Float)
    cash_on_cash_return = Column(Float)
    cap_rate = Column(Float)
    composite_score = Column(Float)

    # GIS flags
    flood_zone = Column(String(10))
    zoning_code = Column(String(50))
    in_historic_district = Column(Boolean, default=False)
    school_district = Column(String(100))

    # Metadata
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, default=True)
    listing_url = Column(String(500))
    raw_data = Column(JSON)


class RentComp(Base):
    __tablename__ = "rent_comps"

    id = Column(Integer, primary_key=True)
    address = Column(String(255))
    lat = Column(Float)
    lng = Column(Float)
    bedrooms = Column(Integer)
    bathrooms = Column(Float)
    sqft = Column(Integer)
    monthly_rent = Column(Integer)
    source = Column(String(50))
    listed_date = Column(DateTime)
    leased_date = Column(DateTime)


class DevelopmentProject(Base):
    __tablename__ = "development_projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    project_type = Column(String(100))
    status = Column(String(50))
    lat = Column(Float)
    lng = Column(Float)
    investment_amount = Column(Float)
    description = Column(Text)
    source_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)


class DistressedParcel(Base):
    __tablename__ = "distressed_parcels"

    id = Column(Integer, primary_key=True)
    parcel_id = Column(String(100), unique=True, index=True)
    address = Column(String(255))
    lat = Column(Float)
    lng = Column(Float)
    county = Column(String(50))           # "clarke" | "oconee"

    # Distress scoring
    distress_score = Column(Integer, default=0)
    distress_tier = Column(String(20))    # "high" | "medium" | "low"
    signals = Column(JSON)                # list of active signal keys

    # Financial context
    assessed_value = Column(Float)
    tax_owed = Column(Float)
    tax_year = Column(Integer)

    # Owner info
    owner_name = Column(String(255))
    owner_mailing_address = Column(String(500))
    absentee_owner = Column(Boolean, default=False)

    # GIS enrichment (from existing modules)
    zoning_code = Column(String(50))
    lot_size_acres = Column(Float)
    year_built = Column(Integer)
    proximity_score = Column(Float)       # from proximity_scoring.py

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    raw_data = Column(JSON)


class AlertLog(Base):
    __tablename__ = "alert_log"

    id = Column(Integer, primary_key=True)
    property_source_id = Column(String(100))
    score = Column(Float)
    alert_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
