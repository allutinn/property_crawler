{{ config(
    materialized='incremental',
    unique_key='data_date'
) }}

SELECT
  -- Basic Listing Info
  data_date,
  a ->> 'id' AS id,
  a ->> 'friendlyId' AS friendly_id,
  a ->> 'text' AS description,
  a ->> 'status' AS status,

  -- Location
  a -> 'property' ->> 'streetAddressFreeForm' AS address,
  a -> 'property' -> 'postCode' ->> 'postCode' AS post_code,
  a -> 'property' -> 'municipality' ->> 'defaultName' AS municipality,
  a -> 'property' -> 'region' ->> 'defaultName' AS region,
  a -> 'property' -> 'geoCode' ->> 'latitude' AS latitude,
  a -> 'property' -> 'geoCode' ->> 'longitude' AS longitude,

  -- Property Details
  a -> 'residenceDetailsDTO' ->> 'livingArea' AS living_area,
  a -> 'residenceDetailsDTO' ->> 'totalArea' AS total_area,
  a -> 'residenceDetailsDTO' ->> 'roomCount' AS room_count,
  a -> 'residenceDetailsDTO' ->> 'roomStructure' AS room_structure,
  a -> 'residenceDetailsDTO' ->> 'floorCount' AS floor_count,
  a -> 'residenceDetailsDTO' ->> 'constructionFinishedYear' AS year_built,
  a -> 'residenceDetailsDTO' ->> 'outerRoofMaterialDescription' AS roof_type,
  a -> 'residenceDetailsDTO' ->> 'heatingSystemsDescription' AS heating_type,
  a -> 'residenceDetailsDTO' -> 'energyCertificate' ->> 'energyCertificateDescription' AS energy_certifica_misc,
  a -> 'residenceDetailsDTO' -> 'energyCertificate' ->> 'energyCertificateType' AS energy_certificate_type,
  a -> 'residenceDetailsDTO' ->> 'kitchenDescription' AS kitchen,
  a -> 'residenceDetailsDTO' ->> 'bathroomDescription' AS bathroom,
  a -> 'property' ->> 'residentialPropertyType' AS property_type,
  a -> 'property' ->> 'ownershipType' AS ownership_type,

  -- Pricing
  a ->> 'sellingPrice' AS price,
  CAST(a ->> 'sellingPrice' AS DOUBLE)
    / NULLIF(CAST(a -> 'residenceDetailsDTO' ->> 'livingArea' AS DOUBLE), 0) AS price_per_m2,

  -- Costs
  a -> 'property' ->> 'periodicChargesAdditionalInfo' AS cost_text,
  a -> 'property' -> 'periodicCharges' -> 0 ->> 'price' AS property_tax,

  -- Zoning / Legal
  a -> 'property' -> 'constructionRightDTO' ->> 'description' AS zoning_info,
  a -> 'property' -> 'plot' ->> 'plotDescription' AS plot_type,
  a -> 'property' -> 'plot' ->> 'plotArea' AS plot_area,

  -- Contact Info
  a -> 'announcementContactInfo' ->> 'name' AS contact_name,
  a -> 'announcementContactInfo' ->> 'phone' AS contact_phone,
  a -> 'announcementContactInfo' ->> 'officeName' AS contact_office,

  -- Availability
  a ->> 'availabilityDescription' AS availability,

  -- External Reference
  a -> 'announcementOriginDetails' ->> 'customerItemCode' AS external_code,

  -- Renovation history
  a -> 'property' ->> 'renovationsDoneDescription' AS renovations

FROM {{ ref('landing_etuovi_announcements') }} a
