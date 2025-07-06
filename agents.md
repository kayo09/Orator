# agents.md

Documentation of agents (Celery workers, services) in **Orator**

## Overview

Orator uses asynchronous task processing for scalable text-to-speech (TTS) conversion and antivirus file scanning. These processes are managed via **Celery** workers and supporting services.

---

## Agents / Workers

### 1️⃣ **Celery TTS Worker**

* **Purpose:**
  Handles conversion of text (e.g., extracted from PDF) into audio files using TTS engine (e.g., Coqui TTS).

* **Location:**
  [`Backend/tasks.py`](../Backend/tasks.py)
  [`Backend/celery_config.py`](../Backend/celery_config.py)

* **Main tasks:**

  * `convert_text_to_audio`
  * `test_tts_short`
  * `health_check`

* **Broker:**
  Redis (default: `redis://redis:6379/0`)

* **Example run:**

  ```bash
  celery -A Backend.tasks.celery_app worker --loglevel=info
  ```

---

### 2️⃣ **ClamAV Service**

* **Purpose:**
  Scans uploaded files for viruses/malware before processing.

* **Location:**
  [`clamav/`](../clamav/) (custom Docker setup)

* **Exposed port:**
  `3310` (default ClamAV daemon port)

* **Healthcheck:**
  Docker `HEALTHCHECK` configured to ping ClamAV daemon with:

  ```
  clamdscan /dev/null
  ```

---

### 3️⃣ **Celery Flower (Optional)**

* **Purpose:**
  Provides web-based monitoring for Celery workers.

* **Location:**
  [`flower/Dockerfile`](../flower/Dockerfile)

* **Run example:**

  ```bash
  flower --broker=redis://redis:6379/0 --port=5555
  ```

* **Access URL:**
  [http://localhost:5555](http://localhost:5555)

---

## Deployment Notes

✅ All agents/services are containerized via Docker Compose.

✅ Redis is required as the broker for Celery workers to communicate task events.

✅ Recommended production flags:

```bash
celery -A Backend.tasks.celery_app worker --loglevel=info --concurrency=2
```

(adjust `--concurrency` based on resource limits)

---

## Troubleshooting

🔹 **Worker lost error / OOM**:
Tune concurrency, use smaller models, or allocate more resources.

🔹 **ClamAV unhealthy**:
Check if database updates succeeded and port is exposed.

🔹 **Flower not accessible**:
Ensure port `5555` is mapped and no firewall is blocking.

---

## Related files

* [`docker-compose.yml`](../docker-compose.yml)
* [`Backend/tasks.py`](../Backend/tasks.py)
* [`Backend/celery_config.py`](../Backend/celery_config.py)

