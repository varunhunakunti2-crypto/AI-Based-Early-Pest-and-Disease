/**
 * GeoJSON type declarations for frontend H3 GIS components.
 *
 * Provides minimal GeoJSON types for Leaflet integration.
 */

declare namespace GeoJSON {
  interface Position extends Array<number> {
    0: number; // longitude
    1: number; // latitude
    2?: number; // altitude
  }

  interface GeometryObject {
    type: string;
    bbox?: number[];
  }

  interface Point extends GeometryObject {
    type: "Point";
    coordinates: Position;
  }

  interface MultiPoint extends GeometryObject {
    type: "MultiPoint";
    coordinates: Position[];
  }

  interface LineString extends GeometryObject {
    type: "LineString";
    coordinates: Position[];
  }

  interface MultiLineString extends GeometryObject {
    type: "MultiLineString";
    coordinates: Position[][];
  }

  interface Polygon extends GeometryObject {
    type: "Polygon";
    coordinates: Position[][];
  }

  interface MultiPolygon extends GeometryObject {
    type: "MultiPolygon";
    coordinates: Position[][][];
  }

  interface GeometryCollection extends GeometryObject {
    type: "GeometryCollection";
    geometries: GeometryObject[];
  }

  type Geometry =
    | Point
    | MultiPoint
    | LineString
    | MultiLineString
    | Polygon
    | MultiPolygon
    | GeometryCollection;

  interface Feature<G = Geometry, P = Record<string, any>> {
    type: "Feature";
    id?: string | number;
    geometry: G;
    properties: P;
    bbox?: number[];
  }

  interface FeatureCollection<G = Geometry, P = Record<string, any>> {
    type: "FeatureCollection";
    features: Feature<G, P>[];
    bbox?: number[];
  }
}

export {};
