FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    clamav-daemon \
    clamav-freshclam \
    ca-certificates \
    netcat-openbsd \
 && rm -rf /var/lib/apt/lists/*
COPY clamd.conf /etc/clamav/clamd.conf
COPY freshclam.conf /etc/clamav/freshclam.conf

RUN freshclam --verbose

EXPOSE 3310

CMD ["clamd"]
