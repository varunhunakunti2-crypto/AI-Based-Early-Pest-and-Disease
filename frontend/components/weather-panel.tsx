"use client";

import { useCallback, useRef, useState } from "react";
import type { FormEvent } from "react";

import {
  WEATHER_SOURCE,
  WeatherError,
  describeWeatherCode,
  fetchWeather,
  placeLabel,
  searchPlaces,
  type Place,
  type WeatherReport,
} from "@/lib/weather";
import {
  formatNumber,
  formatTemperature,
  localTime,
  shortDate,
  weekday,
} from "@/lib/weather-format";

import { WeatherGlyph } from "./weather-glyph";

export function WeatherPanel({
  initialPlace,
  initialReport,
  initialError,
}: {
  initialPlace: Place;
  initialReport: WeatherReport | null;
  initialError: string | null;
}) {
  const [place, setPlace] = useState<Place | null>(initialPlace);
  const [report, setReport] = useState<WeatherReport | null>(initialReport);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(initialError);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Place[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [locating, setLocating] = useState(false);

  const requestRef = useRef<AbortController | null>(null);

  // Fetch-only: all state updates happen after the await, so the effect below
  // never calls setState synchronously.
  const loadReport = useCallback(async (target: Place) => {
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;

    try {
      const nextReport = await fetchWeather(target, controller.signal);
      if (!controller.signal.aborted) {
        setReport(nextReport);
        setError(null);
        setLoading(false);
      }
    } catch (caught) {
      if (controller.signal.aborted) {
        return;
      }
      setReport(null);
      setError(
        caught instanceof WeatherError
          ? caught.message
          : "Weather could not be loaded for this location.",
      );
      setLoading(false);
    }
  }, []);

  const loadPlace = useCallback(
    (next: Place) => {
      setPlace(next);
      setLoading(true);
      setError(null);
      void loadReport(next);
    },
    [loadReport],
  );

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const term = query.trim();
    if (term.length === 0) {
      return;
    }

    setSearching(true);
    setSearchError(null);
    setResults([]);

    const controller = new AbortController();
    try {
      const places = await searchPlaces(term, controller.signal);
      setResults(places);
      if (places.length === 0) {
        setSearchError(`No place matched “${term}”. Try a town, district or city.`);
      }
    } catch (caught) {
      setSearchError(
        caught instanceof WeatherError
          ? caught.message
          : "Place search failed. Try again.",
      );
    } finally {
      setSearching(false);
    }
  }

  function choosePlace(next: Place) {
    setResults([]);
    setSearchError(null);
    setQuery(next.name);
    void loadPlace(next);
  }

  function useMyLocation() {
    if (!("geolocation" in navigator)) {
      setError("This browser does not expose a location. Search for a place instead.");
      return;
    }

    setLocating(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false);
        void loadPlace({
          id: -1,
          name: "Current location",
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          country: null,
          admin1: null,
          timezone: null,
        });
      },
      (geoError) => {
        setLocating(false);
        setError(
          geoError.code === geoError.PERMISSION_DENIED
            ? "Location permission was denied. Search for a place instead."
            : "Your location could not be determined. Search for a place instead.",
        );
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 },
    );
  }

  const condition = report ? describeWeatherCode(report.current.weatherCode) : null;

  return (
    <div className="page">
      <header className="page-header">
        <p className="eyebrow">Weather</p>
        <h1>Weather</h1>
        <p className="page-lede">
          Current conditions and a seven-day forecast for one location. Weather is
          context only — it is never turned into a pest or disease risk score on
          this page.
        </p>
      </header>

      <p className="notice notice-warning small">
        <span className="badge badge-muted">context only</span> A forecast is not a
        diagnosis and weather alone cannot confirm disease. Risk needs crop,
        location, verified reports and an approved model.
      </p>

      <section className="card" aria-labelledby="location-heading">
        <div className="panel-header">
          <h2 id="location-heading">Location</h2>
          {place ? (
            <span className="badge badge-muted">
              {place.latitude.toFixed(4)}, {place.longitude.toFixed(4)}
            </span>
          ) : null}
        </div>

        <form className="weather-search" role="search" onSubmit={handleSearch}>
          <label className="sr-only" htmlFor="weather-place">
            Place name
          </label>
          <input
            id="weather-place"
            type="text"
            value={query}
            placeholder="Search a town or district, e.g. Kolar"
            autoComplete="off"
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="submit" disabled={searching || query.trim().length === 0}>
            {searching ? "Searching…" : "Search"}
          </button>
          <button
            type="button"
            className="button-secondary"
            disabled={locating}
            onClick={useMyLocation}
          >
            {locating ? "Locating…" : "Use my location"}
          </button>
        </form>

        {searchError ? (
          <p className="error small" role="alert">
            {searchError}
          </p>
        ) : null}

        {results.length > 0 ? (
          <ul className="weather-results">
            {results.map((result) => (
              <li key={`${result.id}-${result.latitude}-${result.longitude}`}>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => choosePlace(result)}
                >
                  {placeLabel(result)}
                </button>
              </li>
            ))}
          </ul>
        ) : null}

        {place ? (
          <p className="small muted weather-selected">
            Showing: <strong>{placeLabel(place)}</strong>
            {place.timezone ? ` · ${place.timezone}` : ""}
          </p>
        ) : null}
      </section>

      {error ? (
        <div className="error" role="alert">
          <p>{error}</p>
          {place ? (
            <button
              type="button"
              className="button-secondary"
              onClick={() => void loadPlace(place)}
            >
              Retry
            </button>
          ) : null}
        </div>
      ) : null}

      {loading ? (
        <div className="empty-state" role="status">
          <p>Loading weather for {place ? placeLabel(place) : "the selected place"}…</p>
        </div>
      ) : null}

      {report && condition && !loading ? (
        <>
          <section className="card" aria-labelledby="now-heading">
            <div className="panel-header">
              <h2 id="now-heading">Right now</h2>
              <span className="badge badge-muted">{report.timezone}</span>
            </div>

            <div className="weather-current-main">
              <span className="weather-glyph">
                <WeatherGlyph name={condition.glyph} />
              </span>
              <div>
                <p className="weather-temp">
                  {formatTemperature(report.current.temperature)}
                </p>
                <p className="weather-condition">{condition.label}</p>
                <p className="small muted">
                  As of {localTime(report.current.time)}
                  {report.current.isDay === false ? " · night" : ""}
                  {report.current.apparentTemperature !== null
                    ? ` · feels like ${formatTemperature(report.current.apparentTemperature)}`
                    : ""}
                </p>
              </div>
            </div>

            <dl className="weather-metrics">
              <div className="weather-metric">
                <dt>Humidity</dt>
                <dd>{formatNumber(report.current.humidity, "%")}</dd>
              </div>
              <div className="weather-metric">
                <dt>Wind</dt>
                <dd>{formatNumber(report.current.windSpeed, " km/h")}</dd>
              </div>
              <div className="weather-metric">
                <dt>Precipitation</dt>
                <dd>{formatNumber(report.current.precipitation, " mm")}</dd>
              </div>
              <div className="weather-metric">
                <dt>Source</dt>
                <dd>
                  <a href="https://open-meteo.com/" rel="noreferrer">
                    Open-Meteo
                  </a>
                </dd>
              </div>
            </dl>
          </section>

          <section aria-labelledby="daily-heading">
            <div className="section-heading">
              <h2 id="daily-heading">Next 7 days</h2>
              <p className="small muted">
                Daily summary · fetched{" "}
                <time dateTime={report.fetchedAt} suppressHydrationWarning>
                  {new Date(report.fetchedAt).toLocaleTimeString()}
                </time>
              </p>
            </div>

            <ul className="weather-days">
              {report.daily.map((day) => {
                const dayCondition = describeWeatherCode(day.weatherCode);
                return (
                  <li key={day.date} className="weather-day">
                    <p className="weather-day-name">{weekday(day.date)}</p>
                    <p className="small muted">{shortDate(day.date)}</p>
                    <span className="weather-glyph weather-glyph-small">
                      <WeatherGlyph name={dayCondition.glyph} />
                    </span>
                    <p className="small">{dayCondition.label}</p>
                    <p className="weather-day-temp">
                      <strong>{formatTemperature(day.temperatureMax)}</strong>
                      {" / "}
                      {formatTemperature(day.temperatureMin)}
                    </p>
                    <p className="small muted">
                      {formatNumber(day.precipitationProbability, "%")} rain ·{" "}
                      {formatNumber(day.precipitationSum, " mm")}
                    </p>
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="card" aria-labelledby="source-heading">
            <h2 id="source-heading">About this data</h2>
            <p className="small">
              Conditions and forecast come from{" "}
              <a href={WEATHER_SOURCE.url} rel="noreferrer">
                {WEATHER_SOURCE.name}
              </a>{" "}
              ({WEATHER_SOURCE.licence}), a free weather service. Values are shown
              as received; missing readings are shown as “—” and never filled in.
            </p>
            <p className="small muted">
              Weather is one input to a regional outlook. It is not a diagnosis,
              and it does not by itself mean a pest or disease is present.
            </p>
          </section>
        </>
      ) : null}
    </div>
  );
}
