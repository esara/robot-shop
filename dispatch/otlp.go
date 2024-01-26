package main

import (
	"context"
	"log"
	"os"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.27.0"
)

func initOTLP() func() {
	ctx := context.Background()

	res, err := resource.New(ctx,
		resource.WithAttributes(
			// the service name used to display traces in backends
			semconv.ServiceNameKey.String(os.Getenv("OTEL_SERVICE_NAME")),
			semconv.ServiceNamespaceKey.String(os.Getenv("OTEL_SERVICE_NAMESPACE"))),
		resource.WithContainer(),
		resource.WithProcess(),
	)

	if err != nil {
		log.Println("failed to create resource", err)
		return func() {}
	}

	// Set up a trace exporter using OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_INSECURE, OTEL_EXPORTER_OTLP_HEADERS
	traceExporter, err := otlptracegrpc.New(context.Background())
	if err != nil {
		log.Println("failed to create tracer", err)
		return func() {}
	}

	// Register the trace exporter with a TracerProvider,
	// using a batch span processor to aggregate spans before export.
	batchSpanProcessor := sdktrace.NewBatchSpanProcessor(traceExporter)
	tracerProvider := sdktrace.NewTracerProvider(
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
		sdktrace.WithResource(res),
		sdktrace.WithSpanProcessor(batchSpanProcessor),
	)
	otel.SetTracerProvider(tracerProvider)

	// set global propagator to tracecontext (the default is no-op).
	otel.SetTextMapPropagator(propagation.TraceContext{})

	return func() {
		err := tracerProvider.Shutdown(ctx)
		if err != nil {
			log.Println("failed to shutdown", err)
		}
	}
}
