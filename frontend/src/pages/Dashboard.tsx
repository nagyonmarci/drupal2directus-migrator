import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getJobs } from '../api/client'
import type { Job } from '../types'
import { PHASE_LABELS } from '../types'
import StatusBadge from '../components/StatusBadge'

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [error, setError] = useState('')

  const load = () =>
    getJobs()
      .then((j) => setJobs(j.sort((a, b) => b.created_at.localeCompare(a.created_at))))
      .catch((e) => setError(String(e)))

  useEffect(() => {
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Migration Jobs</h1>
        <Link
          to="/jobs/new"
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          + New Job
        </Link>
      </div>

      {error && <p className="text-red-600 mb-4">{error}</p>}

      {jobs.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <p className="text-lg">No jobs yet.</p>
          <Link to="/jobs/new" className="text-indigo-600 underline mt-2 inline-block">
            Create your first migration job
          </Link>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Label</th>
                <th className="px-4 py-3">Connection</th>
                <th className="px-4 py-3">Phases</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{job.label}</td>
                  <td className="px-4 py-3 text-gray-600">{job.connection_name}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {job.phases.map((p) => PHASE_LABELS[p]).join(', ')}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={job.status} />
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(job.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link to={`/jobs/${job.id}`} className="text-indigo-600 hover:underline">
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
