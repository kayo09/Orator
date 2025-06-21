FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    curl \
    libmecab-dev \
    mecab-ipadic-utf8 \
    pkg-config \
    rustc \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install --no-deps TTS==0.22.0
RUN pip install numpy scipy torch torchaudio transformers soundfile gruut gruut-lang-en inflect
RUN pip install --no-cache-dir flower

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
