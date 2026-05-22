import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getConnections,
  createConnection,
  testConnection,
  createJob,
} from '../api/client'
import type { Connection, ConnectionCreate, TestResult } from '../types'
import { PHASE_LABELS } from '../types'

const EMPTY_CONN: ConnectionCreate = {
  name: '',
  drupal_base_url: '',
  drupal_db_host: '',
  drupal_db_port: 3306,
  drupal_db_name: '',
  drupal_db_user: '',
  drupal_db_password: '',
  drupal_api_user: '',
  drupal_api_password: '',
  directus_url: '',
  directus_admin_token: '',
}

type Step = 'connection' | 'phases' | 'confirm'

export default function NewJob() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('connection')

  // Connection state
  const [connections, setConnections] = useState<Connection[]>([])
  const [selectedConnId, setSelectedConnId] = useState<string>('')
  const [showNewConn, setShowNewConn] = useState(false)
  const [newConn, setNewConn] = useState<ConnectionCreate>(EMPTY_CONN)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [savedConnId, setSavedConnId] = useState<string>('')

  // Phase state
  const [selectedPhases, setSelectedPhases] = useState<number[]>([1, 2, 3, 4, 5, 6])
  const [jobLabel, setJobLabel] = useState('')

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getConnections().then(setConnections).catch(() => {})
  }, [])

  const activeConnId = savedConnId || selectedConnId

  async function handleSaveConn() {
    setError('')
    try {
      const conn = await createConnection(newConn)
      setConnections((prev) => [...prev, conn])
      setSavedConnId(conn.id)
      setShowNewConn(false)
    } catch (e) {
      setError(String(e))
    }
  }

  async function handleTest() {
    if (!activeConnId) return
    setTesting(true)
    setTestResult(null)
    try {
      const result = await testConnection(activeConnId)
      setTestResult(result)
    } catch (e) {
      setError(String(e))
    } finally {
      setTesting(false)
    }
  }

  function togglePhase(p: number) {
    setSelectedPhases((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p].sort()
    )
  }

  async function handleSubmit() {
    if (!activeConnId || selectedPhases.length === 0) return
    setSubmitting(true)
    setError('')
    try {
      const job = await createJob({
        connection_id: activeConnId,
        phases: selectedPhases,
        label: jobLabel || undefined,
      })
      navigate(`/jobs/${job.id}`)
    } catch (e) {
      setError(String(e))
      setSubmitting(false)
    }
  }

  const field = (label: string, key: keyof ConnectionCreate, type = 'text') => (
    <div key={key}>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        type={type}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        value={newConn[key] as string}
        onChange={(e) =>
          setNewConn((prev) => ({ ...prev, [key]: key === 'drupal_db_port' ? Number(e.target.value) : e.target.value }))
        }
      />
    </div>
  )

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">New Migration Job</h1>

      {/* Step indicator */}
      <div className="flex gap-2 mb-8 text-sm">
        {(['connection', 'phases', 'confirm'] as Step[]).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${step === s ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-500'}`}>
              {i + 1}
            </span>
            <span className={step === s ? 'font-medium' : 'text-gray-400'}>
              {s === 'connection' ? 'Connection' : s === 'phases' ? 'Phases' : 'Confirm'}
            </span>
            {i < 2 && <span className="text-gray-300">›</span>}
          </div>
        ))}
      </div>

      {error && <p className="text-red-600 text-sm mb-4 p-3 bg-red-50 rounded-lg">{error}</p>}

      {/* ── Step 1: Connection ── */}
      {step === 'connection' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Existing connection</label>
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={selectedConnId}
              onChange={(e) => { setSelectedConnId(e.target.value); setSavedConnId(''); setTestResult(null) }}
            >
              <option value="">— select —</option>
              {connections.map((c) => (
                <option key={c.id} value={c.id}>{c.name} ({c.drupal_base_url} → {c.directus_url})</option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="text-indigo-600 text-sm underline"
            onClick={() => setShowNewConn((v) => !v)}
          >
            {showNewConn ? '− Hide new connection form' : '+ Add new connection'}
          </button>

          {showNewConn && (
            <div className="border border-gray-200 rounded-lg p-4 space-y-3 bg-white">
              <p className="font-medium text-sm text-gray-700">New connection</p>
              {field('Connection name', 'name')}
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide pt-1">Source — Drupal</p>
              {field('Site base URL', 'drupal_base_url')}
              {field('DB host', 'drupal_db_host')}
              {field('DB port', 'drupal_db_port', 'number')}
              {field('DB name', 'drupal_db_name')}
              {field('DB user', 'drupal_db_user')}
              {field('DB password', 'drupal_db_password', 'password')}
              {field('API user', 'drupal_api_user')}
              {field('API password', 'drupal_api_password', 'password')}
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide pt-1">Target — Directus</p>
              {field('Directus URL', 'directus_url')}
              {field('Admin token', 'directus_admin_token', 'password')}
              <button
                className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700"
                onClick={handleSaveConn}
              >
                Save connection
              </button>
            </div>
          )}

          {activeConnId && (
            <div className="flex items-center gap-3 pt-2">
              <button
                className="border border-gray-300 px-4 py-2 rounded-lg text-sm hover:bg-gray-50"
                onClick={handleTest}
                disabled={testing}
              >
                {testing ? 'Testing…' : 'Test connection'}
              </button>
              {testResult && (
                <span className={testResult.drupal_db && testResult.drupal_api && testResult.directus ? 'text-green-600 text-sm' : 'text-red-600 text-sm'}>
                  {testResult.drupal_db && testResult.drupal_api && testResult.directus
                    ? '✓ All systems reachable'
                    : `✗ ${testResult.errors.join('; ')}`}
                </span>
              )}
            </div>
          )}

          <div className="pt-4">
            <button
              className="bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40"
              disabled={!activeConnId}
              onClick={() => setStep('phases')}
            >
              Next →
            </button>
          </div>
        </div>
      )}

      {/* ── Step 2: Phases ── */}
      {step === 'phases' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Job label (optional)</label>
            <input
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. Full site migration 2024-06"
              value={jobLabel}
              onChange={(e) => setJobLabel(e.target.value)}
            />
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Select phases to run</p>
            <div className="space-y-2">
              {Object.entries(PHASE_LABELS).map(([num, label]) => {
                const p = Number(num)
                return (
                  <label key={p} className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedPhases.includes(p)}
                      onChange={() => togglePhase(p)}
                      className="w-4 h-4 accent-indigo-600"
                    />
                    <span className="text-sm">
                      <span className="font-medium">Phase {p}</span>
                      <span className="text-gray-500"> — {label}</span>
                    </span>
                  </label>
                )
              })}
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button className="border border-gray-300 px-4 py-2 rounded-lg text-sm hover:bg-gray-50" onClick={() => setStep('connection')}>
              ← Back
            </button>
            <button
              className="bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40"
              disabled={selectedPhases.length === 0}
              onClick={() => setStep('confirm')}
            >
              Next →
            </button>
          </div>
        </div>
      )}

      {/* ── Step 3: Confirm ── */}
      {step === 'confirm' && (
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-2 text-sm">
            <p><span className="font-medium">Connection:</span> {connections.find(c => c.id === activeConnId)?.name ?? '—'}</p>
            <p><span className="font-medium">Phases:</span> {selectedPhases.map(p => `${p}. ${PHASE_LABELS[p]}`).join(', ')}</p>
            {jobLabel && <p><span className="font-medium">Label:</span> {jobLabel}</p>}
          </div>

          <p className="text-sm text-gray-500">The job will start immediately after confirmation.</p>

          <div className="flex gap-3 pt-2">
            <button className="border border-gray-300 px-4 py-2 rounded-lg text-sm hover:bg-gray-50" onClick={() => setStep('phases')}>
              ← Back
            </button>
            <button
              className="bg-green-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-40"
              disabled={submitting}
              onClick={handleSubmit}
            >
              {submitting ? 'Starting…' : 'Start migration'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
