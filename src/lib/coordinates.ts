export interface CoordinateInput {
  geometry?: {
    type?: unknown;
    coordinates?: unknown;
  } | null;
  latitude?: unknown;
  longitude?: unknown;
  coordinates?: {
    latitude?: unknown;
    longitude?: unknown;
  } | null;
}

export interface NormalizedCoordinates {
  geoJson: [number, number];
  leaflet: [number, number];
}

function finiteNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function normalizeCoordinates(
  input: CoordinateInput | null | undefined,
): NormalizedCoordinates | null {
  if (!input) return null;

  const geometryCoordinates = Array.isArray(input.geometry?.coordinates)
    ? input.geometry.coordinates
    : null;
  const longitude = finiteNumber(
    geometryCoordinates?.[0] ?? input.longitude ?? input.coordinates?.longitude,
  );
  const latitude = finiteNumber(
    geometryCoordinates?.[1] ?? input.latitude ?? input.coordinates?.latitude,
  );

  if (
    longitude === null ||
    latitude === null ||
    longitude < -180 ||
    longitude > 180 ||
    latitude < -90 ||
    latitude > 90 ||
    (longitude === 0 && latitude === 0)
  ) {
    return null;
  }

  return {
    geoJson: [longitude, latitude],
    leaflet: [latitude, longitude],
  };
}
