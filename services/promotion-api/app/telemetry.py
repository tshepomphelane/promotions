import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

def configure_telemetry(app, service_name: str, engine) -> None:
    # Configure traces with bounded, configurable sampling rate
    sample_ratio = float(os.getenv("OTEL_TRACE_SAMPLE_RATIO", "0.1"))

    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name}),
        sampler=ParentBased(TraceIdRatioBased(sample_ratio)),
    )

    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=os.getenv(
                    "OTEL_EXPORTER_OTLP_ENDPOINT",
                    "otel-collector:4317",
                ),
                insecure=True,
            )
        )
    )

    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(engine=engine)