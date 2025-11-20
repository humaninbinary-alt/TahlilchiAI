"""Application metrics collection using Prometheus."""

from prometheus_client import Counter, Gauge, Histogram, Info

from app.config import settings

# Request metrics
requests_total = Counter(
    "tahlilchi_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

request_duration_seconds = Histogram(
    "tahlilchi_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
)

active_requests = Gauge(
    "tahlilchi_active_requests",
    "Number of active HTTP requests",
)

# RAG metrics
rag_queries_total = Counter(
    "tahlilchi_rag_queries_total",
    "Total RAG queries",
    ["retrieval_mode", "tenant_id"],
)

rag_retrieval_duration_seconds = Histogram(
    "tahlilchi_rag_retrieval_duration_seconds",
    "RAG retrieval duration in seconds",
    ["retrieval_mode"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
)

rag_generation_duration_seconds = Histogram(
    "tahlilchi_rag_generation_duration_seconds",
    "RAG answer generation duration in seconds",
    buckets=(1.0, 5.0, 10.0, 20.0, 30.0, 60.0),
)

rag_contexts_retrieved = Histogram(
    "tahlilchi_rag_contexts_retrieved",
    "Number of contexts retrieved per query",
    buckets=(0, 1, 3, 5, 10, 20, 50),
)

rag_answer_confidence = Histogram(
    "tahlilchi_rag_answer_confidence",
    "Answer confidence distribution",
    ["confidence_level"],
    buckets=(0.1, 0.3, 0.5, 0.7, 0.9, 1.0),
)

# Document metrics
documents_uploaded_total = Counter(
    "tahlilchi_documents_uploaded_total",
    "Total documents uploaded",
    ["tenant_id", "file_type"],
)

documents_processed_total = Counter(
    "tahlilchi_documents_processed_total",
    "Total documents processed",
    ["tenant_id", "status"],
)

document_processing_duration_seconds = Histogram(
    "tahlilchi_document_processing_duration_seconds",
    "Document processing duration in seconds",
    buckets=(10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

documents_indexed_total = Counter(
    "tahlilchi_documents_indexed_total",
    "Total documents indexed",
    ["tenant_id"],
)

# Background job metrics
jobs_queued_total = Counter(
    "tahlilchi_jobs_queued_total",
    "Total jobs queued",
    ["task_name"],
)

jobs_running = Gauge(
    "tahlilchi_jobs_running",
    "Number of currently running jobs",
    ["task_name"],
)

jobs_completed_total = Counter(
    "tahlilchi_jobs_completed_total",
    "Total jobs completed",
    ["task_name", "status"],
)

job_duration_seconds = Histogram(
    "tahlilchi_job_duration_seconds",
    "Job execution duration in seconds",
    ["task_name"],
    buckets=(10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

# System metrics
database_connections = Gauge(
    "tahlilchi_database_connections",
    "Number of active database connections",
)

redis_connections = Gauge(
    "tahlilchi_redis_connections",
    "Number of active Redis connections",
)

celery_workers_active = Gauge(
    "tahlilchi_celery_workers_active",
    "Number of active Celery workers",
)

# Business metrics
active_users = Gauge(
    "tahlilchi_active_users",
    "Number of active users",
    ["tenant_id"],
)

active_tenants = Gauge(
    "tahlilchi_active_tenants",
    "Number of active tenants",
)

conversations_created_total = Counter(
    "tahlilchi_conversations_created_total",
    "Total conversations created",
    ["tenant_id"],
)

messages_sent_total = Counter(
    "tahlilchi_messages_sent_total",
    "Total messages sent",
    ["tenant_id"],
)

citations_generated_total = Counter(
    "tahlilchi_citations_generated_total",
    "Total citations generated",
)

# Application info
app_info = Info("tahlilchi_app", "Application information")
app_info.info({"version": settings.VERSION, "environment": settings.ENVIRONMENT})
