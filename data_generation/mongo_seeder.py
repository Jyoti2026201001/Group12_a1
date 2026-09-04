"""
StaySpot :: mongo_seeder.py
Generates mock data for PropertyAmenities, PropertyReviews, SearchSessions.

Target scale:
  - 500,000+ SearchSessions geospatial pings

Uses pymongo bulk_write with InsertOne for throughput.
"""

import os
import random
import uuid
from datetime import datetime, timedelta

from faker import Faker
from pymongo import MongoClient, InsertOne

fake = Faker()
random.seed(42)

MONGO_URI = os.environ.get("STAYSPOT_MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "stayspot"

NUM_PROPERTIES = 1_000
NUM_REVIEWS = 30_000
NUM_SEARCH_SESSIONS = 550_000   # > 500,000 required
BATCH_SIZE = 10_000

# A handful of city centers to cluster synthetic search pins around,
# for more realistic geospatial distribution than pure random noise.
CITY_CENTERS = [
    (12.9716, 77.5946),   # Bengaluru
    (19.0760, 72.8777),   # Mumbai
    (28.6139, 77.2090),   # Delhi
    (13.0827, 80.2707),   # Chennai
    (40.7128, -74.0060),  # New York
]

REVIEW_TAGS = [
    "clean", "great_location", "friendly_host", "value_for_money",
    "noisy", "spacious", "poor_wifi", "amazing_view", "as_described",
    "responsive_host", "comfortable_beds", "parking_issues",
]


def jitter_point(lat, lng, km_radius=8):
    # ~1 degree latitude ≈ 111km; cheap local jitter, fine for mock data.
    deg_radius = km_radius / 111.0
    return (
        lat + random.uniform(-deg_radius, deg_radius),
        lng + random.uniform(-deg_radius, deg_radius),
    )


def seed_property_amenities(db, property_ids):
    docs = []
    for pid in property_ids:
        docs.append({
            "property_id": pid,
            "house_rules": random.sample(
                ["no_smoking", "no_pets", "no_parties", "quiet_hours_after_10pm", "id_required"],
                k=random.randint(1, 4),
            ),
            "accessibility_features": random.sample(
                ["step_free_access", "wide_doorways", "accessible_bathroom", "elevator"],
                k=random.randint(0, 3),
            ),
            "amenities": {
                "wifi": random.choice([True, False]),
                "kitchen": random.choice([True, False]),
                "pool": random.choice([True, False]),
                "max_guests": random.randint(1, 10),
            },
        })
    db.PropertyAmenities.insert_many(docs)


def seed_property_reviews(db, property_ids, n):
    ops = []
    for _ in range(n):
        ops.append(InsertOne({
            "property_id": random.choice(property_ids),
            "guest_id": str(uuid.uuid4()),
            "rating": random.randint(1, 5),
            "tags": random.sample(REVIEW_TAGS, k=random.randint(1, 4)),
            "comment": fake.sentence(nb_words=12),
            "created_at": fake.date_time_between(start_date="-1y", end_date="now"),
        }))
        if len(ops) >= BATCH_SIZE:
            db.PropertyReviews.bulk_write(ops, ordered=False)
            ops = []
    if ops:
        db.PropertyReviews.bulk_write(ops, ordered=False)


def seed_search_sessions(db, n):
    ops = []
    now = datetime.now()
    for _ in range(n):
        lat, lng = random.choice(CITY_CENTERS)
        jlat, jlng = jitter_point(lat, lng)
        ops.append(InsertOne({
            "session_id": str(uuid.uuid4()),
            "location": {
                "type": "Point",
                "coordinates": [round(jlng, 6), round(jlat, 6)],  # GeoJSON: [lng, lat]
            },
            # Skew recency so the TTL/geoNear demo has live-looking data.
            "created_at": now - timedelta(minutes=random.randint(0, 180)),
        }))
        if len(ops) >= BATCH_SIZE:
            db.SearchSessions.bulk_write(ops, ordered=False)
            ops = []
    if ops:
        db.SearchSessions.bulk_write(ops, ordered=False)


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    property_ids = [str(uuid.uuid4()) for _ in range(NUM_PROPERTIES)]

    print("Seeding PropertyAmenities...")
    seed_property_amenities(db, property_ids)

    print("Seeding PropertyReviews...")
    seed_property_reviews(db, property_ids, NUM_REVIEWS)

    print("Seeding SearchSessions...")
    seed_search_sessions(db, NUM_SEARCH_SESSIONS)

    print("Done.")


if __name__ == "__main__":
    main()
