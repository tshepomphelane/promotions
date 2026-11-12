FROM prom/prometheus:v2.54.1

# keep monitoring self-contained config
COPY prometheus.yml /etc/prometheus/prometheus.yml
COPY generated/ /etc/prometheus/rules/

# Cost control, bounded retention - time and size
CMD [ "--config.file=/etc/prometheus/prometheus.yml", \
      "--storage.tsdb.path=/prometheus", \
      "--storage.tsdb.retention.time=7d", \
      "--storage.tsdb.retention.size=2GB", \
      "--web.console.libraries=/usr/share/prometheus/console_libraries", \
      "--web.console.templates=/usr/share/prometheus/consoles" ]