import { useEffect, useRef, useState } from 'react'

interface Props {
  jobId: string
  active: boolean
}

export default function LogStream({ jobId, active }: Props) {
  const [lines, setLines] = useState<string[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!active) return
    const es = new EventSource(`/api/jobs/${jobId}/logs`)

    es.onmessage = (e) => {
      setLines((prev) => [...prev, e.data])
    }

    es.addEventListener('done', () => es.close())
    es.onerror = () => es.close()

    return () => es.close()
  }, [jobId, active])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  return (
    <div className="bg-gray-900 text-green-300 rounded-lg p-4 font-mono text-xs overflow-y-auto h-96">
      {lines.length === 0 ? (
        <span className="text-gray-500">Waiting for output…</span>
      ) : (
        lines.map((line, i) => (
          <div key={i} className="whitespace-pre-wrap break-all leading-5">
            {line}
          </div>
        ))
      )}
      <div ref={bottomRef} />
    </div>
  )
}
