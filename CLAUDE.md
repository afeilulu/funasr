# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Environment Setup**: The project uses `uv` for dependency management.
  ```bash
  uv venv
  source .venv/bin/activate
  uv pip install -U funasr
  uv pip install -U cos-python-sdk-v5
  uv sync
  ```
- **Run API Server**:
  ```bash
  # Requires ALIBABA_CLOUD_ACCESS_KEY_ID and ALIBABA_CLOUD_ACCESS_KEY_SECRET environment variables
  python api_server.py [dev|prod]
  ```
- **Run Worker**:
  ```bash
  # Requires MODELSCOPE_CACHE environment variable
  python worker.py
  # Run worker and download models first
  python worker.py --download
  ```

## High-Level Architecture

This project provides an Asynchronous Automatic Speech Recognition (ASR) service, primarily built around the `funasr` library and Alibaba Cloud Dashscope ASR.

The system is split into two main components:
1.  **API Server (`api_server.py`)**: A FastAPI application that receives requests, registers tasks in Redis, and provides endpoints to check task status and retrieve results. It also integrates with Consul for service discovery.
2.  **Worker (`worker.py`)**: A Typer-based background process that continuously polls Redis for new tasks (`asr_tasks` queue). It processes audio files (either locally using `funasr` models or via `dashscope.audio.asr.Transcription`), performs speaker diarization, segments the text, uploads results to Tencent Cloud COS, and updates the task status in Redis. It also includes an `analyze` function that uses the Dify API to analyze the transcribed conversation.

### Key Technologies
- **Web Framework**: FastAPI
- **Task Queue/State Storage**: Redis
- **ASR Engine**: FunASR / DashScope
- **Cloud Storage**: Tencent Cloud COS (via `cos-python-sdk-v5`)
- **Service Discovery**: Consul
- **LLM Integration**: Dify (for conversation analysis)
- **Dependency Management**: `uv`

### Environment Variables
The application relies heavily on `.env` files (`.env.dev`, `.env.prod`). Critical environment variables include:
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASS`
- `COS_SECRETID`, `COS_SECRETKEY`, `COS_BUCKETNAME`, `COS_REGIONNAME`
- `DASHSCOPE_API_KEY`
- `CONSUL_HOST`, `CONSUL_PORT`, `CONSUL_TOKEN`
- `MODELSCOPE_CACHE` (Required by `worker.py`)
- `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET` (Required by `api_server.py`)