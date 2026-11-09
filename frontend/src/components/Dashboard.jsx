import { Link } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { tokens, partidoCores } from '../styles/tokens'
import { LoadingSpinner } from './common'
import { formatDecimal, formatNumber, legislatureName } from '../utils/format'
import { partyPath } from '../utils/party';
import HomeComposicao from './HomeComposicao';

/**
 * Dashboard - Data Observatory Style
 *
 * Authoritative, data-journalism aesthetic inspired by ProPublica, FiveThirtyEight, Guardian.
 * Dense information, serif headlines, monospace numbers, minimal decoration.
 */

const Dashboard = ({ stats }) => {
  if (!stats) {
    return <LoadingSpinner message="A carregar dados" />
  }

  const { totais = {}, distribuicao_partidos = [], distribuicao_circulos = [], legislatura = {} } = stats

  // Use seated deputies count if available, otherwise fall back to total
  const seatedDeputados = totais.deputados_em_exercicio || totais.seated_deputies || totais.deputados || 230
  const totalElected = totais.deputados_eleitos || totais.deputados || 230

  // Process party data
  const partidosData = (distribuicao_partidos || []).map(partido => ({
    ...partido,
    cor: partidoCores[partido.sigla] || '#78716C',
    percentagem: formatDecimal((partido.deputados / (totais.deputados || 1)) * 100, 1)
  })).sort((a, b) => b.deputados - a.deputados)

  // Top circles
  const circulosData = (distribuicao_circulos || []).slice(0, 10)

  // The party table's position column (the composition strip reads the groups from the data, #265)
  const governoPartidos = ['PSD', 'CDS-PP']

  // Legislature text
  const getLegislatureText = () => {
    if (!legislatura.numero) return 'XVII Legislatura'
    return legislatureName(legislatura.numero)
  }

  return (
    <div style={{ fontFamily: tokens.fonts.body }}>
      {/* Hero Header */}
      <header style={{ marginBottom: '2rem' }}>
        <h1 style={{
          fontFamily: tokens.fonts.headline,
          fontSize: '2.75rem',
          fontWeight: 700,
          color: tokens.colors.textPrimary,
          marginBottom: '0.75rem',
          lineHeight: 1.15,
        }}>
          Parlamento Português
        </h1>
        <p style={{
          fontSize: '1.125rem',
          color: tokens.colors.textSecondary,
          maxWidth: '640px',
          lineHeight: 1.5,
          marginBottom: '1.5rem',
        }}>
          Análise da composição e dinâmicas parlamentares da {getLegislatureText()}.
          Dados extraídos do Portal de Dados Abertos da Assembleia da República. As datas são as dos
          dados, não a de hoje.
        </p>
      </header>

      <HomeComposicao />
      <p style={{
        margin: '0 0 2.5rem',
        maxWidth: '72ch',
        fontSize: '0.875rem',
        lineHeight: 1.6,
        color: tokens.colors.textSecondary,
      }}>
        {formatNumber(seatedDeputados)} deputados em exercício na data dos dados.{' '}
        {formatNumber(totalElected)} pessoas tiveram lugar em algum momento da legislatura, substitutos incluídos.
        {totais.deputados_listados != null && (
          <>
            {' '}{formatNumber(totais.deputados_listados)} estão nas listas da legislatura em{' '}
            <Link to="/deputados" style={{ color: 'inherit', textDecoration: 'underline' }}>Deputados</Link>, contando
            quem suspendeu o mandato antes de tomar lugar.
          </>
        )}{' '}
        <Link to="/metodologia" style={{ color: 'inherit', textDecoration: 'underline' }}>Como contamos</Link>
      </p>

      {/* Regional Distribution */}
      <section style={{
        backgroundColor: tokens.colors.bgSecondary,
        border: `1px solid ${tokens.colors.border}`,
        borderRadius: '4px',
        marginBottom: '2.5rem',
      }}>
        <div style={{
          padding: '1.25rem 1.5rem',
          borderBottom: `1px solid ${tokens.colors.border}`,
        }}>
          <h2 style={{
            fontFamily: tokens.fonts.headline,
            fontSize: '1.125rem',
            fontWeight: 700,
            color: tokens.colors.textPrimary,
            margin: 0,
          }}>
            Distribuição Territorial
          </h2>
          <p style={{
            fontSize: '0.8125rem',
            color: tokens.colors.textMuted,
            margin: '0.25rem 0 0',
          }}>
            Deputados por círculo eleitoral (top 10)
          </p>
        </div>
        <div style={{ padding: '1.5rem' }}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={circulosData} margin={{ top: 10, right: 10, left: 10, bottom: 60 }}>
              <XAxis
                dataKey="circulo"
                angle={-45}
                textAnchor="end"
                height={60}
                tick={{ fontSize: 11, fill: tokens.colors.textMuted }}
                axisLine={{ stroke: tokens.colors.border }}
                tickLine={{ stroke: tokens.colors.border }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: tokens.colors.textMuted }}
                axisLine={{ stroke: tokens.colors.border }}
                tickLine={{ stroke: tokens.colors.border }}
              />
              <Tooltip
                formatter={(value) => [`${value} deputados`, '']}
                contentStyle={{
                  backgroundColor: tokens.colors.bgSecondary,
                  border: `1px solid ${tokens.colors.border}`,
                  borderRadius: '4px',
                  fontFamily: tokens.fonts.body,
                  fontSize: '0.875rem',
                }}
              />
              <Bar
                dataKey="deputados"
                fill={tokens.colors.primary}
                radius={[2, 2, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Party Details Table */}
      <section style={{
        backgroundColor: tokens.colors.bgSecondary,
        border: `1px solid ${tokens.colors.border}`,
        borderRadius: '4px',
      }}>
        <div style={{
          padding: '1.25rem 1.5rem',
          borderBottom: `1px solid ${tokens.colors.border}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div>
            <h2 style={{
              fontFamily: tokens.fonts.headline,
              fontSize: '1.125rem',
              fontWeight: 700,
              color: tokens.colors.textPrimary,
              margin: 0,
            }}>
              Partidos com Representação Parlamentar
            </h2>
            <p style={{
              fontSize: '0.8125rem',
              color: tokens.colors.textMuted,
              margin: '0.25rem 0 0',
            }}>
              Força parlamentar ordenada por número de mandatos
            </p>
          </div>
          <span style={{
            fontFamily: tokens.fonts.mono,
            fontSize: '0.8125rem',
            color: tokens.colors.textMuted,
          }}>
            {partidosData.length} partidos
          </span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '0.875rem',
          }}>
            <thead>
              <tr style={{ backgroundColor: tokens.colors.bgTertiary }}>
                <th style={{
                  padding: '0.75rem 1.5rem',
                  textAlign: 'left',
                  fontWeight: 600,
                  fontSize: '0.6875rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: tokens.colors.textMuted,
                  borderBottom: `2px solid ${tokens.colors.borderStrong}`,
                }}>Partido</th>
                <th style={{
                  padding: '0.75rem 1rem',
                  textAlign: 'right',
                  fontWeight: 600,
                  fontSize: '0.6875rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: tokens.colors.textMuted,
                  borderBottom: `2px solid ${tokens.colors.borderStrong}`,
                }}>Deputados</th>
                <th style={{
                  padding: '0.75rem 1rem',
                  textAlign: 'right',
                  fontWeight: 600,
                  fontSize: '0.6875rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: tokens.colors.textMuted,
                  borderBottom: `2px solid ${tokens.colors.borderStrong}`,
                }}>% Parlamento</th>
                <th style={{
                  padding: '0.75rem 1rem',
                  textAlign: 'center',
                  fontWeight: 600,
                  fontSize: '0.6875rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: tokens.colors.textMuted,
                  borderBottom: `2px solid ${tokens.colors.borderStrong}`,
                }}>Posição</th>
                <th style={{
                  padding: '0.75rem 1.5rem',
                  textAlign: 'left',
                  fontWeight: 600,
                  fontSize: '0.6875rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: tokens.colors.textMuted,
                  borderBottom: `2px solid ${tokens.colors.borderStrong}`,
                  width: '30%',
                }}>Força Relativa</th>
              </tr>
            </thead>
            <tbody>
              {partidosData.map((partido, index) => {
                const isGoverno = governoPartidos.includes(partido.sigla)
                const maxDeputados = Math.max(...partidosData.map(p => p.deputados))
                return (
                  <tr
                    key={partido.sigla}
                    style={{
                      borderBottom: `1px solid ${tokens.colors.border}`,
                      transition: 'background-color 150ms ease',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = tokens.colors.bgTertiary}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <td style={{ padding: '1rem 1.5rem' }}>
                      <Link
                        to={partyPath(partido.id)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.75rem',
                          textDecoration: 'none',
                          color: 'inherit',
                        }}
                      >
                        <span style={{
                          width: '12px',
                          height: '12px',
                          borderRadius: '2px',
                          backgroundColor: partido.cor,
                          flexShrink: 0,
                        }} />
                        <div>
                          <div style={{
                            fontWeight: 600,
                            color: tokens.colors.textPrimary,
                          }}>{partido.sigla}</div>
                          <div style={{
                            fontSize: '0.75rem',
                            color: tokens.colors.textMuted,
                            maxWidth: '200px',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}>{partido.nome}</div>
                        </div>
                      </Link>
                    </td>
                    <td style={{
                      padding: '1rem',
                      textAlign: 'right',
                      fontFamily: tokens.fonts.mono,
                      fontWeight: 600,
                      fontSize: '1rem',
                      color: tokens.colors.textPrimary,
                    }}>{partido.deputados}</td>
                    <td style={{
                      padding: '1rem',
                      textAlign: 'right',
                      fontFamily: tokens.fonts.mono,
                      color: tokens.colors.textSecondary,
                    }}>{partido.percentagem}%</td>
                    <td style={{
                      padding: '1rem',
                      textAlign: 'center',
                    }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '0.25rem 0.5rem',
                        backgroundColor: isGoverno ? '#F0FDF4' : '#EFF6FF',
                        border: `1px solid ${isGoverno ? '#86EFAC' : '#BFDBFE'}`,
                        borderRadius: '2px',
                        fontSize: '0.6875rem',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        letterSpacing: '0.03em',
                        color: isGoverno ? tokens.colors.success : '#2563EB',
                      }}>
                        {isGoverno ? 'Governo' : 'Oposição'}
                      </span>
                    </td>
                    <td style={{ padding: '1rem 1.5rem' }}>
                      <div style={{
                        height: '8px',
                        backgroundColor: tokens.colors.bgTertiary,
                        borderRadius: '2px',
                        overflow: 'hidden',
                      }}>
                        <div style={{
                          height: '100%',
                          width: `${(partido.deputados / maxDeputados) * 100}%`,
                          backgroundColor: partido.cor,
                          transition: 'width 300ms ease',
                        }} />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Responsive styles */}
      <style>{`
        @media (max-width: 1024px) {
          section[style*="grid-template-columns: 1fr 1fr"] {
            grid-template-columns: 1fr !important;
          }
        }
        @media (max-width: 768px) {
          section[style*="grid-template-columns: repeat(4, 1fr)"] {
            grid-template-columns: repeat(2, 1fr) !important;
          }
        }
        @media (max-width: 480px) {
          section[style*="grid-template-columns: repeat(2, 1fr)"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  )
}

export default Dashboard
