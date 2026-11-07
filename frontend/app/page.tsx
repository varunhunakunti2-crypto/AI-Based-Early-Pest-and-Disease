import Link from "next/link";

import { WeatherGlyph } from "@/components/weather-glyph";
import { ApiError, getHealth } from "@/lib/api";
import {
  DEFAULT_PLACE,
  WEATHER_SOURCE,
  WeatherError,
  describeWeatherCode,
  fetchWeather,
  placeLabel,
  type WeatherReport,
} from "@/lib/weather";
import {
  formatNumber,
  formatTemperature,
  localTime,
  shortDate,
  weekday,
} from "@/lib/weather-format";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Overview",
};

export default async function HomePage() {
  const [healthResult, weatherResult] = await Promise.allSettled([
    getHealth(),
    fetchWeather(DEFAULT_PLACE),
  ]);

  let service: string | null = null;
  let failure: string | null = null;

  if (healthResult.status === "fulfilled") {
    const health = healthResult.value;
    service = `${health.service} ${health.version} (${health.environment})`;
  } else {
    const error = healthResult.reason;
    failure =
      error instanceof ApiError
        ? `${error.status} ${error.problem?.code ?? "api_error"}`
        : "API unreachable";
  }

  let weather: WeatherReport | null = null;
  let weatherFailure: string | null = null;

  if (weatherResult.status === "fulfilled") {
    weather = weatherResult.value;
  } else {
    const error = weatherResult.reason;
    weatherFailure =
      error instanceof WeatherError
        ? error.message
        : "Weather could not be loaded for the default location.";
  }

  const condition = weather ? describeWeatherCode(weather.current.weatherCode) : null;

  return (
    <div className="page">
      <header className="page-header">
        <p className="eyebrow">Overview</p>
        <h1>Crop early warning</h1>
        <p className="page-lede">
          An explainable, offline-tolerant decision-support workspace. It answers
          two separate questions and never merges them into one risk number.
        </p>
      </header>

      <section className="card" aria-labelledby="status-heading">
        <div className="panel-header">
          <h2 id="status-heading">Platform status</h2>
          {service ? (
            <span className="badge">API reachable</span>
          ) : (
            <span className="badge badge-muted">API unavailable</span>
          )}
        </div>
        {service ? (
          <p className="mono">{service}</p>
        ) : (
          <p className="error" role="status">
            {failure}
          </p>
        )}
        <p className="muted small">
          This panel reports platform reachability only. It does not report pest
          or disease risk.
        </p>
      </section>

      <section className="card" aria-labelledby="weather-heading">
        <div className="panel-header">
          <h2 id="weather-heading">Weather context</h2>
          <span className="badge badge-muted">
            {placeLabel(weather?.place ?? DEFAULT_PLACE)}
          </span>
        </div>

        {weather && condition ? (
          <>
            <div className="weather-current-main">
              <span className="weather-glyph">
                <WeatherGlyph name={condition.glyph} />
              </span>
              <div>
                <p className="weather-temp">
                  {formatTemperature(weather.current.temperature)}
                </p>
                <p className="weather-condition">{condition.label}</p>
                <p className="small muted">
                  As of {localTime(weather.current.time)} (local time)
                  {weather.current.isDay === false ? " · night" : ""}
                  {weather.current.apparentTemperature !== null
                    ? ` · feels like ${formatTemperature(weather.current.apparentTemperature)}`
                    : ""}
                </p>
              </div>
            </div>

            <dl className="weather-metrics">
              <div className="weather-metric">
                <dt>Humidity</dt>
                <dd>{formatNumber(weather.current.humidity, "%")}</dd>
              </div>
              <div className="weather-metric">
                <dt>Wind</dt>
                <dd>{formatNumber(weather.current.windSpeed, " km/h")}</dd>
              </div>
              <div className="weather-metric">
                <dt>Precipitation</dt>
                <dd>{formatNumber(weather.current.precipitation, " mm")}</dd>
              </div>
              <div className="weather-metric">
                <dt>Source</dt>
                <dd>
                  <a href={WEATHER_SOURCE.url} rel="noreferrer">
                    {WEATHER_SOURCE.name}
                  </a>
                </dd>
              </div>
            </dl>

            <div className="weather-summary-head">
              <h3>Next days</h3>
              <p className="small muted">
                Fetched{" "}
                <time dateTime={weather.fetchedAt} suppressHydrationWarning>
                  {new Date(weather.fetchedAt).toLocaleTimeString("en-GB", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </time>
                {" · "}
                {WEATHER_SOURCE.licence}
              </p>
            </div>

            <ul className="weather-days">
              {weather.daily.slice(0, 4).map((day) => {
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

            <p className="small weather-summary-foot">
              <Link href="/weather">Open the full seven-day forecast</Link> to
              search another place or use your current location.
            </p>
          </>
        ) : (
          <p className="error" role="status">
            {weatherFailure ?? "Weather is unavailable for the default location."}
            {" "}
            <Link href="/weather">Try the weather page</Link>.
          </p>
        )}

        <p className="notice notice-warning small weather-context-note">
          <span className="badge badge-muted">context only</span> Weather can
          support scouting, but it is not a pest or disease risk score. Risk needs
          crop, location, verified reports and an approved model.
        </p>
      </section>

      <section aria-labelledby="outputs-heading">
        <div className="section-heading">
          <h2 id="outputs-heading">Two outputs, never merged</h2>
          <p className="muted small">
            Different questions, different data, different timestamps.
          </p>
        </div>

        <div className="output-grid">
          <article className="output-card">
            <p className="eyebrow">Photo assessment</p>
            <h3>What might be visible on this plant?</h3>
            <p className="small muted">
              One image plus crop context. Assistive triage — not a diagnosis and
              not a laboratory result.
            </p>
            <p className="chip-row">
              <span className="chip">Demo replies only</span>
              <span className="chip chip-muted">No image model connected</span>
            </p>
            <Link href="/chat" className="button">
              Open photo assessment
            </Link>
          </article>

          <article className="output-card output-card-muted">
            <p className="eyebrow">Area outlook</p>
            <h3>How likely is this threat in this area?</h3>
            <p className="small muted">
              Crop × target × geography × horizon. Arrives in a later phase; no
              forecast is computed or shown in this build.
            </p>
            <p className="chip-row">
              <span className="chip chip-muted">Not available in this phase</span>
              <span className="chip chip-muted">Coverage shown separately</span>
            </p>
            <Link href="/outlook" className="button button-secondary">
              View area outlook
            </Link>
          </article>
        </div>
      </section>

      <section aria-labelledby="sections-heading">
        <div className="section-heading">
          <h2 id="sections-heading">Workspace sections</h2>
          <p className="muted small">
            What is usable now, and what is still locked to a later phase.
          </p>
        </div>

        <div className="section-grid">
          <Link href="/chat" className="section-card">
            <span className="section-card-title">Photo assessment</span>
            <span className="small muted">
              Conversation list and thread, idempotent send and demo replies.
            </span>
            <span className="badge">Available</span>
          </Link>

          <Link href="/review" className="section-card">
            <span className="section-card-title">Review queue</span>
            <span className="small muted">
              Expert verification portal. Requires roles and review APIs that are
              not built yet.
            </span>
            <span className="badge badge-muted">Locked</span>
          </Link>

          <Link href="/outlook" className="section-card">
            <span className="section-card-title">Area outlook</span>
            <span className="small muted">
              Forecast, risk map and coverage. Deliberately separate from photo
              assessment.
            </span>
            <span className="badge badge-muted">Not in this phase</span>
          </Link>

          <Link href="/weather" className="section-card">
            <span className="section-card-title">Weather</span>
            <span className="small muted">
              Current conditions and a seven-day forecast for one location.
              Context only, never a risk score.
            </span>
            <span className="badge">Available</span>
          </Link>
        </div>
      </section>

      <section className="card" aria-labelledby="demo-heading">
        <div className="panel-header">
          <h2 id="demo-heading">Demo content</h2>
          <span className="badge badge-muted">demo</span>
        </div>
        <p className="small">
          The chat currently returns a labelled template reply. No image model is
          connected in this phase, and no assessment is fabricated.
        </p>
      </section>
    </div>
  );
}
