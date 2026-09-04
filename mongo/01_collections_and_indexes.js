// ============================================================
// StaySpot :: 01_collections_and_indexes.js
// Collection creation (with JSON Schema validation) + indexes
// Run with: mongosh <connection_string> 01_collections_and_indexes.js
// ============================================================

db = db.getSiblingDB("stayspot");

// ------------------------------------------------------------
// PropertyAmenities - flexible catalog docs
// ------------------------------------------------------------
db.createCollection("PropertyAmenities", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["property_id", "house_rules", "accessibility_features"],
      properties: {
        property_id: { bsonType: "string", description: "FK -> properties.id (UUID as string)" },
        house_rules: {
          bsonType: "array",
          items: { bsonType: "string" }
        },
        accessibility_features: {
          bsonType: "array",
          items: { bsonType: "string" }
        },
        amenities: {
          bsonType: "object",
          description: "arbitrary nested amenity flags/values, schema-flexible"
        }
      }
    }
  }
});

// ------------------------------------------------------------
// PropertyReviews - structured reviews
// ------------------------------------------------------------
db.createCollection("PropertyReviews", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["property_id", "rating", "tags", "created_at"],
      properties: {
        property_id: { bsonType: "string" },
        guest_id:    { bsonType: "string" },
        rating:      { bsonType: "int", minimum: 1, maximum: 5 },
        tags:        { bsonType: "array", items: { bsonType: "string" } },
        comment:     { bsonType: "string" },
        created_at:  { bsonType: "date" }
      }
    }
  }
});

// ------------------------------------------------------------
// SearchSessions - geospatial pin-drop logs
// ------------------------------------------------------------
db.createCollection("SearchSessions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["session_id", "location", "created_at"],
      properties: {
        session_id: { bsonType: "string" },
        location: {
          bsonType: "object",
          required: ["type", "coordinates"],
          properties: {
            type: { enum: ["Point"] },
            coordinates: {
              bsonType: "array",
              minItems: 2,
              maxItems: 2,
              items: { bsonType: "double" }
            }
          }
        },
        created_at: { bsonType: "date" }
      }
    }
  }
});

// ------------------------------------------------------------
// Indexes
// ------------------------------------------------------------

// Geospatial: required for $geoNear in Workflow 3.
db.SearchSessions.createIndex({ location: "2dsphere" });

// TTL: auto-expire search pins after 2 hours (7200s).
db.SearchSessions.createIndex(
  { created_at: 1 },
  { expireAfterSeconds: 7200 }
);

// Supporting indexes for review analytics (Workflow 4).
db.PropertyReviews.createIndex({ property_id: 1 });
db.PropertyReviews.createIndex({ rating: 1 });
db.PropertyReviews.createIndex({ tags: 1 });

db.PropertyAmenities.createIndex({ property_id: 1 }, { unique: true });

print("StaySpot collections + indexes created.");
