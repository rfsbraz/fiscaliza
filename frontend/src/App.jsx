import { useState, useEffect, lazy, Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ExternalLink, AlertTriangle, X } from 'lucide-react'
import Navigation from './components/Navigation'
import DataAttribution from './components/DataAttribution'

const Dashboard = lazy(() => import('./components/Dashboard'))
const DeputadosPage = lazy(() => import('./components/DeputadosPage'))
const DeputadoDetalhes = lazy(() => import('./components/DeputadoDetalhes'))
const PartidosPage = lazy(() => import('./components/PartidosPage'))
const PartidoDetalhes = lazy(() => import('./components/PartidoDetalhes'))
const ColigacaoDetalhes = lazy(() => import('./components/ColigacaoDetalhes'))
const AgendaPage = lazy(() => import('./components/AgendaPage'))
import { apiFetch } from './config/api'
import './App.css'

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

