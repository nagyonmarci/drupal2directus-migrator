export interface Connection {
  id: string
  name: string
  drupal_base_url: string
  drupal_db_host: string
  drupal_db_port: number
  drupal_db_name: string
  drupal_db_user: string
  drupal_api_user: string
  directus_url: string
  created_at: string
}

export interface ConnectionCreate {
  name: string
  drupal_base_url: string
  drupal_db_host: string
  drupal_db_port: number
  drupal_db_name: string
  drupal_db_user: string
  drupal_db_password: string
  drupal_api_user: string
  drupal_api_password: string
  directus_url: string
  directus_admin_token: string
}

export interface TestResult {
  drupal_db: boolean
  drupal_api: boolean
  directus: boolean
  errors: string[]
}

export type JobStatus = 'pending' | 'running' | 'done' | 'failed' | 'cancelled'

export interface Job {
  id: string
  connection_id: string
  connection_name: string
  phases: number[]
  label: string
  status: JobStatus
  created_at: string
  started_at: string | null
  finished_at: string | null
  current_phase: number | null
  error: string | null
  log_path: string
}

export const PHASE_LABELS: Record<number, string> = {
  1: 'Preflight Verification',
  2: 'Schema Migration',
  3: 'Users & Roles',
  4: 'Files & Media',
  5: 'Content',
  6: 'Blocks & Views',
}
