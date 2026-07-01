from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Span

from app.config import Settings

TRACER_NAME = "production_ai_platform.api"

_configured = False


def configure_tracing(app: FastAPI, settings: Settings) -> None:
    global _configured

    app.state.tracing_enabled = settings.otel_tracing_enabled
    if _configured or not settings.otel_tracing_enabled:
        return

    resource = Resource.create(
        {
            SERVICE_NAME: settings.otel_service_name,
            DEPLOYMENT_ENVIRONMENT: settings.environment,
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(_span_exporter(settings)))
    trace.set_tracer_provider(provider)
    _configured = True


def get_tracer():
    return trace.get_tracer(TRACER_NAME)


def set_span_attributes(span: Span, attributes: Mapping[str, Any]) -> None:
    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, value)


def _span_exporter(settings: Settings):
    if settings.otel_traces_exporter == "otlp":
        kwargs = {}
        if settings.otel_exporter_otlp_endpoint:
            kwargs["endpoint"] = settings.otel_exporter_otlp_endpoint
        return OTLPSpanExporter(**kwargs)
    return ConsoleSpanExporter()
