FROM prom/prometheus:v2.54.1

# keep monitoring self-contained config
COPY prometheus.yml /etc/prometheus/prometheus.yml
COPY generated/ /etc/prometheus/rules/