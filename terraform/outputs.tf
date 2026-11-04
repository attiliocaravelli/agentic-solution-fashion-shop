output "project_id" {
  description = "GCP Project ID in cui e distribuita l'infrastruttura"
  value       = var.project_id
}

output "online_api_url" {
  description = "URL pubblico del microservizio Cloud Run Online Serving (<5ms)"
  value       = google_cloud_run_v2_service.online_api.uri
}

output "redis_private_ip" {
  description = "Indirizzo IP privato della cache Redis per il cluster"
  value       = google_redis_instance.capsule_cache.host
}

output "gcs_data_lake_bucket" {
  description = "Nome del Bucket GCS contenente i dataset Parquet e gli armadi compatti"
  value       = google_storage_bucket.data_lake.name
}

output "batch_job_name" {
  description = "Nome del Cloud Run Job per l'esecuzione della pipeline agentica notturna"
  value       = google_cloud_run_v2_job.batch_nightly_job.name
}

output "cloud_scheduler_name" {
  description = "Nome del job Cloud Scheduler che innesca la generazione ogni notte alle 03:00"
  value       = google_cloud_scheduler_job.nightly_trigger.name
}

output "service_account_email" {
  description = "Email del Service Account IAM con privilegi minimi"
  value       = google_service_account.fashop_sa.email
}

