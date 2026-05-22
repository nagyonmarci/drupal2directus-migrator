import type { Connection, ConnectionCreate, Job, TestResult } from '../types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`HTTP ${res.status}: ${body}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

// Connections
export const getConnections = (): Promise<Connection[]> =>
  request('/connections')

export const createConnection = (data: ConnectionCreate): Promise<Connection> =>
  request('/connections', { method: 'POST', body: JSON.stringify(data) })

export const deleteConnection = (id: string): Promise<void> =>
  request(`/connections/${id}`, { method: 'DELETE' })

export const testConnection = (id: string): Promise<TestResult> =>
  request(`/connections/${id}/test`, { method: 'POST' })

// Jobs
export const getJobs = (): Promise<Job[]> => request('/jobs')

export const getJob = (id: string): Promise<Job> => request(`/jobs/${id}`)

export const createJob = (data: {
  connection_id: string
  phases: number[]
  label?: string
}): Promise<Job> =>
  request('/jobs', { method: 'POST', body: JSON.stringify(data) })

export const cancelJob = (id: string): Promise<void> =>
  request(`/jobs/${id}`, { method: 'DELETE' })
