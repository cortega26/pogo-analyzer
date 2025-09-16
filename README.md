# Pokémon Analyzer

Simple library and CLI for Pokémon GO stat analysis.

## Usage

```bash
python -m pogo_analyzer.cli --species Bulbasaur --iv 0 15 15 --level 20
```

This prints PvE breakpoints and PvP league recommendations.

## REST API

The project ships with an optional FastAPI application that exposes the
`scan_screenshot` helper over HTTP.

```bash
uvicorn pogo_analyzer.api:app --reload
```

Send a `multipart/form-data` request containing an image file to analyse it:

```bash
curl -F "file=@/path/to/screenshot.png" http://localhost:8000/scan
```

If FastAPI is not installed, install it first:

```bash
pip install fastapi uvicorn
```

## Mobile capture screen

A React Native capture and review screen lives in `mobile/src/screens/CaptureScreen.tsx`.
It lets you capture or pick screenshots, sends them to the REST API, and caches the most
recent analyses (via AsyncStorage) for offline review. See `mobile/README.md` for setup
instructions.

## Error taxonomy and logging guidelines

The project now standardises error handling and observability. All user-facing errors
descend from `pogo_analyzer.errors.PogoAnalyzerError` and provide:

- `category` – a stable machine-readable code (e.g. `input_error`,
  `payload_too_large`, `processing_error`, `dependency_error`).
- `message` – a concise, actionable description of the failure.
- `remediation` – optional guidance to resolve the failure.
- `context` – sanitised debugging details (never containing PII).

Mapping to HTTP status codes follows the taxonomy:

| Exception class | Category            | HTTP status |
|-----------------|---------------------|-------------|
| `InputValidationError` | `input_error`       | 400 |
| `PayloadTooLargeError` | `payload_too_large` | 413 |
| `ProcessingError` | `processing_error` | 422 |
| `DependencyError` | `dependency_error` | 503 |
| `NotReadyError`/`OperationalError` | `not_ready` / `operational_error` | 503 / 500 |

### Logging

- Always obtain loggers via `pogo_analyzer.observability.get_logger(__name__)`.
- Include a descriptive `event` attribute in every log call to ease searching.
- Add contextual fields rather than string interpolation; sensitive keys (such as
  `username`, `email`, or `token`) are automatically redacted.
- Avoid logging raw file paths or user-supplied text that might contain PII. Prefer
  summarised context (e.g. file extension, counters).
- When raising `PogoAnalyzerError`, populate `context` with machine-oriented values to aid
  diagnostics. The API will surface the sanitised payload along with an `X-Trace-Id`
  header so incidents can be correlated with logs and metrics.

### Observability

- Structured logs are emitted in JSON format with timestamps and trace identifiers.
- Metrics are available via the `/metrics` endpoint in Prometheus exposition format. Use
  the global `metrics` registry from `pogo_analyzer.observability` to capture new
  counters, gauges, or summaries.
- The `/health` endpoint returns dependency readiness, cache status, and a metrics
  snapshot to support liveness probes and dashboards.
