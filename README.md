# Dienstencatalogus Personalized Search – Proof of Concept

This repository contains a Proof-of-Concept (PoC) for a **personalized search engine** over the Dienstencatalogus dataset from the Vlaamse Overheid.

## 🎯 Goal

The PoC demonstrates how to search for public services relevant to specific types of **verenigingen** (e.g., youth organizations, sports clubs), while:
- Respecting standard filters like `type`, `overheid`, and `thema`
- Ranking results based on profile relevance (e.g., `doelgroep`, `regio`, `sector`)
- Supporting sorting by `relevance` or `last updated`

## 🧱 Architecture

- `FastAPI` backend for querying
- `Typer` CLI for ingestion and indexing
- `Elasticsearch` as the search engine
- `Docker Compose` to orchestrate services including Elasticsearch
- `DevContainer` support for full reproducible environments

## 📦 Components

### 1. **CLI (`cli.py`)**
- Downloads and normalizes Dienstencatalogus data
- Cleans HTML fields
- Infers target audiences (`doelgroepen`) using regex or LLMs
- Indexes documents into Elasticsearch

### 2. **API (`api.py`)**
- `/search` endpoint accepts:
  - keyword query
  - UI filters (e.g. type, thema, overheid)
  - sort mode (`relevance` or `date`)
  - Vereniging profile (`regio`, `doelgroep`, `sector`)
- Constructs hybrid query in Elasticsearch with filtering and profile-based boosting

### 3. **Elasticsearch**
- Runs as a service using Docker Compose
- Index includes cleaned and enriched Dienstencatalogus data
- Dutch analyzer enabled for better search quality

### 4. **DevContainer Support**
- Includes Dockerfile and Docker Compose config
- Automatically spins up a development-ready environment with Elasticsearch and the app container

## ✅ Usage

- Start the DevContainer (`Reopen in Container` in VSCode)
- Run the CLI to index data:
  ```bash
  dci index --help
  ```
- Run the FastAPI app:
  ```bash
  uv run uvicorn api.main:app --reload
  ```
- Query the API at: `http://localhost:8000/docs`