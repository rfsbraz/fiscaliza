import { useState, useEffect, useLayoutEffect, useRef, lazy, Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ExternalLink } from 'lucide-react'
import Navigation from './components/Navigation'
import DataAttribution from './components/DataAttribution'

const Dashboard = lazy(() => import('./components/Dashboard'))
const DeputadosPage = lazy(() => import('./components/DeputadosPage'))
const DeputadoDetalhes = lazy(() => import('./components/DeputadoDetalhes'))
const PartidosPage = lazy(() => import('./components/PartidosPage'))
const PartidoDetalhes = lazy(() => import('./components/PartidoDetalhes'))
const ColigacaoDetalhes = lazy(() => import('./components/ColigacaoDetalhes'))
const AgendaPage = lazy(() => import('./components/AgendaPage'))
const PerguntasPage = lazy(() => import('./components/PerguntasPage'))
const NotFound = lazy(() => import('./components/NotFound'))
const Metodologia = lazy(() => import('./components/Metodologia'))
import { apiFetch } from './config/api'
import { routeTitle } from './utils/routeTitle'
import './App.css'

const AppContent = () => {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const { pathname } = useLocation()
  const landing = useRef({ path: pathname, title: document.title })

  // A layout effect runs before the pages' own effects, so a page that sets its title still wins.
  useLayoutEffect(() => {
    document.title = routeTitle(landing.current, pathname)
  }, [pathname])

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
            <Route path="/perguntas" element={<PerguntasPage />} />
            <Route path="/perguntas/:legislatura" element={<PerguntasPage />} />
            <Route path="/metodologia" element={<Metodologia />} />
            <Route path="*" element={<NotFound />} />
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

          <DataAttribution />

          <p style={{ textAlign: 'center', margin: '0.75rem 0 0 0' }}>
            <Link
              to="/metodologia"
              style={{
                fontFamily: "'Source Sans 3', sans-serif",
                fontSize: '0.875rem',
                fontWeight: 600,
                color: '#1B4332',
                textDecoration: 'underline',
              }}
            >
              Metodologia e fontes
            </Link>
          </p>

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
        {/* Main site routes */}
        <Route path="/*" element={<AppContent />} />
      </Routes>
    </Router>
  )
}

export default App

