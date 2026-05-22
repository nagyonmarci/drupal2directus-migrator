import { Link, Outlet, useLocation } from 'react-router-dom'

export default function Layout() {
  const { pathname } = useLocation()

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-indigo-700 text-white shadow">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/jobs" className="text-lg font-semibold tracking-tight">
            Drupal → Directus Migrator
          </Link>
          <nav className="flex gap-4 text-sm">
            <Link
              to="/jobs"
              className={pathname === '/jobs' ? 'underline underline-offset-4' : 'opacity-80 hover:opacity-100'}
            >
              Jobs
            </Link>
            <Link
              to="/jobs/new"
              className={pathname === '/jobs/new' ? 'underline underline-offset-4' : 'opacity-80 hover:opacity-100'}
            >
              + New Job
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-8">
        <Outlet />
      </main>

      <footer className="text-center text-xs text-gray-400 py-4">
        drupal2directus-migrator
      </footer>
    </div>
  )
}
