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
