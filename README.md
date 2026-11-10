## Promotion Service 
### Overview

This project demonstrates a reusable SRE golden path for onboarding product services into a production-ready operating model.

The example service is a promotion eligibility API owned by a fictional CRM product team.

#### The implementation demonstrates:

- HTTP API and PostgreSQL integration
- Dependency resilience and failure injection
- Automated testing
- OpenTelemetry instrumentation
- Service Level Indicators and Objectives
- Multi-window error-budget burn-rate alerting
- Reusable CI/CD pipeline
- Containerised local development

### Architecture

The environment runs locally using Docker Compose.

Core components:

Promotion Eligibility API
Fake Customer Profile API
PostgreSQL
Prometheus
Grafana
OpenTelemetry Collector
Jaeger
k6 load testing

### Getting started

Instructions will be added as the implementation progresses.

## Golden path adoption

The golden-path/ directory contains reusable templates and configuration intended for adoption by other product teams.

## Documentation
- DECISIONS.md - Architecture decisions, assumptions and trade-offs.
- docs/ - Operational documentation and demonstrations.
- golden-path/runbooks/ - Reusable operational runbook template.