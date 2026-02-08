import { useState, useEffect, lazy, Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ExternalLink, AlertTriangle, X, Shield } from 'lucide-react'
import Navigation from './components/Navigation'
import { Database, AlertTriangle as AlertIcon, Activity, Layers, HardDrive, FileText, Cpu, Settings } from 'lucide-react'

const Dashboard = lazy(() => import('./components/Dashboard'))
const DeputadosPage = lazy(() => import('./components/DeputadosPage'))
const DeputadoDetalhes = lazy(() => import('./components/DeputadoDetalhes'))
const PartidosPage = lazy(() => import('./components/PartidosPage'))
const PartidoDetalhes = lazy(() => import('./components/PartidoDetalhes'))
const ColigacaoDetalhes = lazy(() => import('./components/ColigacaoDetalhes'))
const AgendaPage = lazy(() => import('./components/AgendaPage'))
const TransparenciaPage = lazy(() => import('./components/TransparenciaPage'))
const AdminLayout = lazy(() => import('./components/admin').then(m => ({ default: m.AdminLayout })))
const AdminDashboard = lazy(() => import('./components/admin').then(m => ({ default: m.AdminDashboard })))
const AdminPlaceholder = lazy(() => import('./components/admin').then(m => ({ default: m.AdminPlaceholder })))
import { apiFetch } from './config/api'
import './App.css'

// Localhost-only wrapper for admin routes
const LocalhostOnly = ({ children }) => {
  const isLocalhost = window.location.hostname === 'localhost' ||
                      window.location.hostname === '127.0.0.1' ||
                      window.location.hostname === '::1'

  if (!isLocalhost) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{
          backgroundColor: '#030708',
          fontFamily: "'IBM Plex Mono', monospace"
        }}
      >
        <div className="text-center p-8">
          <div
            className="w-20 h-20 rounded-lg mx-auto mb-6 flex items-center justify-center"
            style={{
              backgroundColor: 'rgba(255, 51, 102, 0.1)',
              border: '1px solid rgba(255, 51, 102, 0.3)'
            }}
          >
            <Shield className="h-10 w-10" style={{ color: '#ff3366' }} />
          </div>
          <h1
            className="text-xl font-medium mb-2"
            style={{ color: '#e0f0e8' }}
          >
            ACCESS_DENIED
          </h1>
          <p
            className="text-sm max-w-sm"
            style={{ color: '#4a5f55' }}
          >
            Admin interface restricted to localhost connections only.
            Connect from 127.0.0.1 to access.
          </p>
          <div
            className="mt-6 text-xs"
            style={{ color: '#7a8f85' }}
          >
            Remote IP detected: {window.location.hostname}
          </div>
        </div>
      </div>
    )
  }

  return children
}

const AppContent = () => {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showBanner, setShowBanner] = useState(true)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      // Get overall statistics instead of per-legislatura
      const response = await apiFetch('estatisticas')
      const data = await response.json()
      setStats(data)
    } catch (error) {
      console.error('Erro ao carregar estatísticas:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          backgroundColor: '#FAFAFA',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          style={{
            width: '48px',
            height: '48px',
            border: '3px solid #E5E5E5',
            borderTopColor: '#1B4332',
            borderRadius: '50%',
          }}
        />
      </div>
    )
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#FAFAFA',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Navigation />

      {/* Editorial Notice Banner */}
      {showBanner && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          style={{
            backgroundColor: '#FFFFFF',
            borderBottom: '1px solid #E5E5E5',
          }}
        >
          <div
            style={{
              maxWidth: '1280px',
              margin: '0 auto',
              padding: '0.75rem 1.5rem',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '1rem',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.75rem',
                }}
              >
                <div
                  style={{
                    width: '3px',
                    height: '100%',
                    minHeight: '2.5rem',
                    backgroundColor: '#9B2335',
                    borderRadius: '2px',
                    flexShrink: 0,
                  }}
                />
                <div>
                  <p
                    style={{
                      fontFamily: "'Source Sans 3', sans-serif",
                      fontSize: '0.8125rem',
                      fontWeight: 600,
                      color: '#1A1A1A',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      marginBottom: '0.125rem',
                    }}
                  >
                    Nota Editorial
                  </p>
                  <p
                    style={{
                      fontFamily: "'Source Sans 3', sans-serif",
                      fontSize: '0.875rem',
                      color: '#4A4A4A',
                      lineHeight: 1.5,
                    }}
                  >
                    Este portal encontra-se em fase de desenvolvimento. Os dados apresentados são demonstrativos e não devem ser considerados oficiais.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowBanner(false)}
                style={{
                  padding: '0.375rem',
                  background: 'none',
                  border: '1px solid #E5E5E5',
                  borderRadius: '2px',
                  cursor: 'pointer',
                  color: '#6B6B6B',
                  flexShrink: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 150ms ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#1B4332';
                  e.currentTarget.style.color = '#1B4332';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#E5E5E5';
                  e.currentTarget.style.color = '#6B6B6B';
                }}
                aria-label="Fechar aviso"
              >
                <X size={14} />
              </button>
            </div>
          </div>
        </motion.div>
      )}

      <main
        style={{
          flex: 1,
          maxWidth: '1280px',
          margin: '0 auto',
          padding: '2rem 1.5rem',
          width: '100%',
        }}
      >
        <Suspense fallback={
          <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              style={{ width: '32px', height: '32px', border: '3px solid #E5E5E5', borderTopColor: '#1B4332', borderRadius: '50%' }}
            />
          </div>
        }>
          <Routes>
            <Route path="/" element={<Dashboard stats={stats} />} />
            <Route path="/deputados" element={<DeputadosPage />} />
            <Route path="/deputados/:cadId" element={<DeputadoDetalhes />} />
            <Route path="/partidos" element={<PartidosPage />} />
            <Route path="/partidos/:partidoId" element={<PartidoDetalhes />} />
            <Route path="/coligacoes/:coligacaoId" element={<ColigacaoDetalhes />} />
            <Route path="/agenda" element={<AgendaPage />} />
            <Route path="/transparencia" element={<TransparenciaPage />} />
          </Routes>
        </Suspense>
      </main>

      {/* Editorial Footer */}
      <footer
        style={{
          backgroundColor: '#FFFFFF',
          borderTop: '1px solid #E5E5E5',
          marginTop: 'auto',
        }}
      >
        <div
          style={{
            maxWidth: '1280px',
            margin: '0 auto',
            padding: '1.5rem',
          }}
        >
          {/* Top section with sources */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '1rem',
              paddingBottom: '1.25rem',
              borderBottom: '1px solid #E5E5E5',
            }}
          >
            <p
              style={{
                fontFamily: "'Source Sans 3', sans-serif",
                fontSize: '0.75rem',
                fontWeight: 600,
                color: '#6B6B6B',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
              }}
            >
              Fontes de Dados
            </p>
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '1.5rem',
              }}
            >
              <a
                href="https://www.parlamento.pt/Cidadania/paginas/dadosabertos.aspx"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.375rem',
                  fontFamily: "'Source Sans 3', sans-serif",
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  color: '#1B4332',
                  textDecoration: 'none',
                  transition: 'opacity 150ms ease',
                }}
                onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'}
                onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
              >
                <ExternalLink size={14} />
                Dados Abertos do Parlamento
              </a>
              <span style={{ color: '#D4D4D4' }}>|</span>
              <a
                href="https://av.parlamento.pt/"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.375rem',
                  fontFamily: "'Source Sans 3', sans-serif",
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  color: '#1B4332',
                  textDecoration: 'none',
                  transition: 'opacity 150ms ease',
                }}
                onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'}
                onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
              >
                <ExternalLink size={14} />
                Canal Parlamento
              </a>
            </div>
          </div>

          {/* Bottom section with branding */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '0.5rem',
              paddingTop: '1.25rem',
            }}
          >
            <p
              style={{
                fontFamily: "'Libre Baskerville', Georgia, serif",
                fontSize: '1rem',
                fontWeight: 700,
                color: '#1A1A1A',
              }}
            >
              Fiscaliza
            </p>
            <p
              style={{
                fontFamily: "'Source Sans 3', sans-serif",
                fontSize: '0.75rem',
                color: '#6B6B6B',
              }}
            >
              Transparência parlamentar ao serviço dos cidadãos
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

function App() {
  return (
    <Router>
      <Routes>
        {/* Admin routes - completely separate layout, localhost only */}
        <Route path="/admin" element={
          <LocalhostOnly>
            <Suspense fallback={<div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>}>
              <AdminLayout />
            </Suspense>
          </LocalhostOnly>
        }>
          <Route index element={<AdminDashboard />} />
          <Route path="imports" element={
            <AdminPlaceholder
              title="Import Manager"
              description="Detailed view of all imports with filtering, bulk actions, and manual retry capabilities."
              icon={Database}
            />
          } />
          <Route path="errors" element={
            <AdminPlaceholder
              title="Error Analytics"
              description="Deep dive into import errors with pattern detection, categorization, and resolution tracking."
              icon={AlertIcon}
            />
          } />
          <Route path="pipeline" element={
            <AdminPlaceholder
              title="Pipeline Control"
              description="Start, stop, and monitor the data import pipeline with real-time progress tracking."
              icon={Activity}
            />
          } />
          <Route path="queue" element={
            <AdminPlaceholder
              title="Queue Manager"
              description="View and manage the import queue with priority adjustment and scheduling options."
              icon={Layers}
            />
          } />
          <Route path="database" element={
            <AdminPlaceholder
              title="Database Stats"
              description="Database health metrics, table sizes, query performance, and connection pool status."
              icon={HardDrive}
            />
          } />
          <Route path="logs" element={
            <AdminPlaceholder
              title="Log Viewer"
              description="Real-time log streaming with filtering, search, and export capabilities."
              icon={FileText}
            />
          } />
          <Route path="performance" element={
            <AdminPlaceholder
              title="Performance Monitor"
              description="System resource usage, API response times, and performance bottleneck analysis."
              icon={Cpu}
            />
          } />
          <Route path="settings" element={
            <AdminPlaceholder
              title="Admin Settings"
              description="Configure import parameters, notification preferences, and system behavior."
              icon={Settings}
            />
          } />
        </Route>

        {/* Main site routes */}
        <Route path="/*" element={<AppContent />} />
      </Routes>
    </Router>
  )
}

export default App

