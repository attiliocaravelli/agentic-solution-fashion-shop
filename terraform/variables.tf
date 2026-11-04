variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
  default     = "qwiklabs-gcp-01-11c2bfff0128" # Default id or override via tfvars
}

variable "region" {
  description = "GCP region per le risorse di produzione"
  type        = string
  default     = "europe-west1"
}

variable "zone" {
  description = "GCP zone primaria"
  type        = string
  default     = "europe-west1-b"
}

variable "environment" {
  description = "Environment identifier (es. prod, staging)"
  type        = string
  default     = "prod"
}

variable "app_name" {
  description = "Nome applicazione per naming convention"
  type        = string
  default     = "fashop-genrec"
}

variable "redis_memory_size_gb" {
  description = "Capacita in GB per Cloud Memorystore Redis (Cache Capsule)"
  type        = number
  default     = 1
}

variable "cloud_run_min_instances" {
  description = "Istanze minime Cloud Run per azzerare il cold-start di front-end"
  type        = number
  default     = 1
}

variable "cloud_run_max_instances" {
  description = "Istanze massime Cloud Run per autoscaling"
  type        = number
  default     = 10
}

variable "batch_cron_schedule" {
  description = "Schedulazione cron per il job batch notturno (UTC)"
  type        = string
  default     = "0 3 * * *" # Ogni notte alle 03:00 UTC
}

variable "batch_time_zone" {
  description = "Timezone per Cloud Scheduler"
  type        = string
  default     = "Europe/Rome"
}

