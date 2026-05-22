import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getJob, cancelJob } from '../api/client'
import type { Job } from '../types'
import { PHASE_LABELS } from '../types'
import StatusBadge from '../components/StatusBadge'
import LogStream from '../components/LogStream'

export default function JobDetail() {
  const { id } = useParams<{ id: string }>()
  const [job, setJob] = useState<Job | null>(null)
  const [error, setError] = useState('')
  const [cancelling, setCancelling] = useState(false)

  useEffect(() => {
    if (!id) return
    const load = () =>
      getJob(id)
        .then(setJob)
        .catch((e) => setError(String(e)))

    load()
    const interval = setInterval(() => {
      getJob(id)
        .then((j) => {
          setJob(j)
          if (['done', 'failed', 'cancelled'].includes(j.status)) {
            clearInterval(interval)
          }
        })
        .catch(() => {})
    }, 3000)
    return () => clearInterval(interval)
  }, [id])

  async function handleCancel() {
    if (!id) return
    setCancelling(true)
    try {
      await cancelJob(id)
      setJob((prev) => prev ? { ...prev, status: 'cancelled' } : prev)
    } catch (e) {
      setError(String(e))
    } finally {
      setCancelling(false)
    }
  }

  if (error) return <p className="text-red-600">{error}</p>
  if (!job) return <p className="text-gray-400">Loading…</p>

  const isActive = job.status === 'running' || job.status === 'pending'
  const duration = job.started_at && job.finished_at
    ? Math.round((new Date(job.finished_at).getTime() - new Date(job.started_at).getTime()) / 1000)
    : null

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <Link to="/jobs" className="text-indigo-600 text-sm hover:underline">← Back to jobs</Link>
          <h1 className="text-2xl font-bold mt-1">{job.label}</h1>
          <p className="text-sm text-gray-500 mt-0.5">Connection: {job.connection_name}</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={job.status} />
          {isActive && (
            <button
              className="border border-red-300 text-red-600 px-3 py-1.5 rounded-lg text-sm hover:bg-red-50 disabled:opacity-40"
              onClick={handleCancel}
              disabled={cancelling}
            >
              {cancelling ? 'Cancelling…' : 'Cancel'}
            </button>
          )}
        </div>
      </div>

      {/* Meta */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
        <div className="bg-white border border-gray-200 rounded-lg p-3">
          <p className="text-gray-400 text-xs">Created</p>
          <p className="font-medium">{new Date(job.created_at).toLocaleString()}</p>
        </div>
        {job.started_at && (
          <div className="bg-white border border-gray-200 rounded-lg p-3">
            <p className="text-gray-400 text-xs">Started</p>
            <p className="font-medium">{new Date(job.started_at).toLocaleString()}</p>
          </div>
        )}
        {duration !== null && (
          <div className="bg-white border border-gray-200 rounded-lg p-3">
            <p className="text-gray-400 text-xs">Duration</p>
            <p className="font-medium">{duration}s</p>
          </div>
        )}
        {job.error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 col-span-2">
            <p className="text-red-400 text-xs">Error</p>
            <p className="text-red-700 font-medium">{job.error}</p>
          </div>
        )}
      </div>

      {/* Phases */}
      <div>
        <p className="text-sm font-medium text-gray-700 mb-2">Phases</p>
        <div className="flex flex-wrap gap-2">
          {job.phases.map((p) => (
            <span key={p} className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium">
              {p}. {PHASE_LABELS[p]}
            </span>
          ))}
        </div>
      </div>

      {/* Log */}
      <div>
        <p className="text-sm font-medium text-gray-700 mb-2">Live output</p>
        <LogStream jobId={job.id} active={isActive || job.status === 'done' || job.status === 'failed'} />
      </div>
    </div>
  )
}
