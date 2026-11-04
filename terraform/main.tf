terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

resource "random_id" "suffix" {
  byte_length = 4
}

# ==============================================================================
# 1. ABILITAZIONE DELLE API GCP CORE
# ==============================================================================
locals {
  services = [
    "run.googleapis.com",              # Cloud Run (Service & Jobs)
    "aiplatform.googleapis.com",       # Vertex AI Gemini 2.5
    "storage.googleapis.com",          # Google Cloud Storage (Data Lake)
    "redis.googleapis.com",            # Cloud Memorystore Redis
    "vpcaccess.googleapis.com",        # Serverless VPC Access per Redis
    "cloudscheduler.googleapis.com",   # Cloud Scheduler per cron batch
    "artifactregistry.googleapis.com", # Docker Container Registry
    "compute.googleapis.com",          # Networking & VPC
    "iam.googleapis.com"               # IAM & Service Accounts
  ]
}

resource "google_project_service" "enabled_apis" {
  for_each                   = toset(locals.services)
  project                    = var.project_id
  service                    = each.key
  disable_dependent_services = false
  disable_on_destroy         = false
}

# ==============================================================================
# 2. NETWORKING & SERVERLESS VPC ACCESS
# ==============================================================================
resource "google_compute_network" "fashop_vpc" {
  name                    = "${var.app_name}-vpc-${var.environment}"
  auto_create_subnetworks = true
  depends_on              = [google_project_service.enabled_apis]
}

# Connector Serverless per consentire a Cloud Run di interrogare Redis su IP privato
resource "google_vpc_access_connector" "serverless_connector" {
  name          = "vpc-conn-${var.environment}"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.fashop_vpc.name

  min_instances = 2
  max_instances = 3

  depends_on = [
    google_project_service.enabled_apis,
    google_compute_network.fashop_vpc
  ]
}

# ==============================================================================
# 3. STORAGE LAYER (GCS DATA LAKE & CLOUD MEMORYSTORE REDIS)
# ==============================================================================

# GCS Bucket per i dataset Parquet (transazioni storiche H&M e articoli)
resource "google_storage_bucket" "data_lake" {
  name                        = "${var.app_name}-datalake-${var.environment}-${random_id.suffix.hex}"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  depends_on = [google_project_service.enabled_apis]
}

# Cloud Memorystore Redis (Serving capsule con latenza sub-5ms)
resource "google_redis_instance" "capsule_cache" {
  name               = "${var.app_name}-cache-${var.environment}"
  tier               = "BASIC" # o STANDARD_HA per High Availability multi-zona
  memory_size_gb     = var.redis_memory_size_gb
  region             = var.region
  authorized_network = google_compute_network.fashop_vpc.id

  redis_version     = "REDIS_7_0"
  display_name      = "Fashop Smart Capsule Fast Cache"

  depends_on = [
    google_project_service.enabled_apis,
    google_compute_network.fashop_vpc
  ]
}

# ==============================================================================
# 4. ARTIFACT REGISTRY & IAM SERVICE ACCOUNT
# ==============================================================================
resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = "${var.app_name}-repo"
  description   = "Docker repository per container Fashop Multi-Agent"
  format        = "DOCKER"

  depends_on = [google_project_service.enabled_apis]
}

resource "google_service_account" "fashop_sa" {
  account_id   = "sa-${var.app_name}-${var.environment}"
  display_name = "Service Account per Fashop Agentic Platform"
  depends_on   = [google_project_service.enabled_apis]
}

# Ruoli di sicurezza IAM minimi (Principio del Minimo Privilegio)
locals {
  sa_roles = [
    "roles/aiplatform.user",       # Accesso a Vertex AI Gemini 2.5
    "roles/storage.objectViewer",   # Lettura Parquet da GCS
    "roles/redis.editor",          # Lettura/Scrittura su Redis Memorystore
    "roles/logging.logWriter",     # Scrittura log applicativi su Cloud Logging
    "roles/run.invoker"            # Invocazione endpoint Cloud Run
  ]
}

resource "google_project_iam_member" "sa_bindings" {
  for_each = toset(locals.sa_roles)
  project  = var.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.fashop_sa.email}"
}

# ==============================================================================
# 5. COMPUTE LAYER: CLOUD RUN SERVICE (ONLINE SERVING API < 5ms)
# ==============================================================================
resource "google_cloud_run_v2_service" "online_api" {
  name     = "${var.app_name}-api-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.fashop_sa.email

    scaling {
      min_instance_count = var.cloud_run_min_instances # 1 istanza sempre calda = zero cold start
      max_instance_count = var.cloud_run_max_instances
    }

    vpc_access {
      connector = google_vpc_access_connector.serverless_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/fashop-api:latest"

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.capsule_cache.host
      }
      env {
        name  = "REDIS_PORT"
        value = tostring(google_redis_instance.capsule_cache.port)
      }
      env {
        name  = "DATA_BUCKET"
        value = google_storage_bucket.data_lake.name
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.enabled_apis,
    google_vpc_access_connector.serverless_connector,
    google_redis_instance.capsule_cache
  ]
}

# Consentire l'accesso pubblico non autenticato all'API o proteggerlo via IAM / API Gateway
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.online_api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ==============================================================================
# 6. BATCH PIPELINE: CLOUD RUN JOB (GENERAZIONE MULTI-AGENTE OFFLINE)
# ==============================================================================
resource "google_cloud_run_v2_job" "batch_nightly_job" {
  name     = "${var.app_name}-batch-job-${var.environment}"
  location = var.region

  template {
    template {
      service_account = google_service_account.fashop_sa.email
      timeout         = "3600s" # 1 ora per batch

      vpc_access {
        connector = google_vpc_access_connector.serverless_connector.id
        egress    = "PRIVATE_RANGES_ONLY"
      }

      containers {
        image   = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/fashop-batch:latest"
        command = ["python", "scripts/batch_evaluation_report.py"]
        args    = ["--sample-size", "1000"]

        resources {
          limits = {
            cpu    = "4"
            memory = "8Gi"
          }
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        env {
          name  = "GCP_PROJECT"
          value = var.project_id
        }
        env {
          name  = "GCP_REGION"
          value = var.region
        }
        env {
          name  = "REDIS_HOST"
          value = google_redis_instance.capsule_cache.host
        }
        env {
          name  = "REDIS_PORT"
          value = tostring(google_redis_instance.capsule_cache.port)
        }
        env {
          name  = "DATA_BUCKET"
          value = google_storage_bucket.data_lake.name
        }
      }
    }
  }

  depends_on = [
    google_project_service.enabled_apis,
    google_vpc_access_connector.serverless_connector,
    google_redis_instance.capsule_cache
  ]
}

# ==============================================================================
# 7. AUTOMATION: CLOUD SCHEDULER (SCHEDULAZIONE NOTTURNA ORE 03:00)
# ==============================================================================
resource "google_cloud_scheduler_job" "nightly_trigger" {
  name             = "${var.app_name}-nightly-trigger-${var.environment}"
  description      = "Trigger automatico per la pipeline batch notturna Smart Capsule"
  schedule         = var.batch_cron_schedule
  time_zone        = var.batch_time_zone
  attempt_deadline = "320s"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.batch_nightly_job.name}:run"

    oauth_token {
      service_account_email = google_service_account.fashop_sa.email
    }
  }

  depends_on = [
    google_project_service.enabled_apis,
    google_cloud_run_v2_job.batch_nightly_job
  ]
}

