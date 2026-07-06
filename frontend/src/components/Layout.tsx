import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { LogOut, User as UserIcon, LogIn, Sparkles } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { motion } from 'framer-motion'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <div className="blueprint-page">
      <header className="sticky top-0 z-50 border-b border-[rgba(186,215,247,0.12)] bg-[rgba(5,6,15,0.82)] backdrop-blur-xl">
        <div className="mx-auto max-w-[var(--page-max-width)] px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center space-x-3 group">
              <div className="grid h-9 w-9 place-items-center rounded-md bg-[var(--color-graphite-plate)] shadow-[var(--shadow-subtle)] group-hover:shadow-[var(--shadow-sm)] transition-shadow">
                <Sparkles className="h-5 w-5 text-[var(--color-moonlight)]" />
              </div>
              <span className="blueprint-heading text-xl">
                Тендерный Хакер
              </span>
            </Link>

            <div className="flex items-center gap-6">
              <nav className="flex items-center space-x-2">
                <Link
                  to="/"
                  className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                    isActive('/')
                      ? 'blueprint-button-primary'
                      : 'blueprint-pill'
                  }`}
                >
                  Дашборд
                </Link>
                <Link
                  to="/profile"
                  className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                    isActive('/profile')
                      ? 'blueprint-button-primary'
                      : 'blueprint-pill'
                  }`}
                >
                  Профиль компании
                </Link>
              </nav>

              <div className="flex items-center gap-4 pl-6 border-l border-[rgba(186,215,247,0.12)]">
                {user ? (
                  <>
                    <div className="flex items-center gap-2 px-3 py-2 blueprint-status">
                      <UserIcon className="h-4 w-4 text-[var(--color-fog)]" />
                      <span className="text-sm font-medium text-[var(--color-moonlight)]">{user.full_name || user.email}</span>
                    </div>
                    <button
                      onClick={logout}
                      className="p-2 blueprint-button-ghost"
                      title="Выйти"
                    >
                      <LogOut className="h-5 w-5" />
                    </button>
                  </>
                ) : (
                  <Link
                    to="/login"
                    className="flex items-center gap-2 px-4 py-2 blueprint-button-primary text-sm"
                  >
                    <LogIn className="h-4 w-4" />
                    Войти
                  </Link>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[var(--page-max-width)] px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      <footer className="border-t border-[rgba(186,215,247,0.12)] mt-12 bg-[rgba(5,6,15,0.72)]">
        <div className="mx-auto max-w-[var(--page-max-width)] px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-[var(--color-fog)] text-sm">
            © 2024 Тендерный Хакер. AI-анализ госзакупок.
          </p>
        </div>
      </footer>
    </div>
  )
}

