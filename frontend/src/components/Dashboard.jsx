import { Link } from 'react-router-dom'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { tokens, partidoCores } from '../styles/tokens'
import { LoadingSpinner } from './common'

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
    percentagem: ((partido.deputados / (totais.deputados || 1)) * 100).toFixed(1)
  })).sort((a, b) => b.deputados - a.deputados)

  // Top circles
  const circulosData = (distribuicao_circulos || []).slice(0, 10)

  // Political calculations
  const calcularFragmentacao = () => {
    const total = totais.deputados || 1
    const enp = 1 / partidosData.reduce((sum, p) => sum + Math.pow(p.deputados / total, 2), 0)
    return enp.toFixed(1)
  }

  const governoPartidos = ['PSD', 'CDS-PP']
  const governoDeputados = partidosData.filter(p => governoPartidos.includes(p.sigla)).reduce((sum, p) => sum + p.deputados, 0)
  const oposicaoDeputados = partidosData.filter(p => !governoPartidos.includes(p.sigla)).reduce((sum, p) => sum + p.deputados, 0)
  // Majority is based on seated deputies (those who can vote)
  const maioriaAbsoluta = Math.floor(seatedDeputados / 2) + 1
  const temMaioria = governoDeputados >= maioriaAbsoluta

  // Legislature text
  const getLegislatureText = () => {
    if (!legislatura.numero) return 'XVII Legislatura'
    return `${legislatura.numero} Legislatura`
  }

  return (
    <div style={{ fontFamily: tokens.fonts.body }}>
      {/* Hero Header */}
      <header style={{ marginBottom: '3rem' }}>
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
          Dados extraídos do Portal de Dados Abertos da Assembleia da República.
        </p>

        {/* Key indicators strip */}
        <div style={{
          display: 'flex',
          gap: '0.5rem',
          flexWrap: 'wrap',
        }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.375rem 0.75rem',
            backgroundColor: tokens.colors.bgTertiary,
            border: `1px solid ${tokens.colors.border}`,
            borderRadius: '2px',
            fontSize: '0.8125rem',
            color: tokens.colors.textSecondary,
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              backgroundColor: tokens.colors.primary,
              borderRadius: '50%',
            }} />
            {getLegislatureText()}
          </span>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.375rem 0.75rem',
            backgroundColor: temMaioria ? '#DCFCE7' : '#FEF3C7',
            border: `1px solid ${temMaioria ? '#86EFAC' : '#FCD34D'}`,
            borderRadius: '2px',
            fontSize: '0.8125rem',
            fontWeight: 600,
            color: temMaioria ? tokens.colors.success : tokens.colors.warning,
          }}>
            {temMaioria ? 'Maioria Absoluta' : 'Governo Minoritário'}
          </span>
        </div>
      </header>

      {/* Metrics Strip */}
      <section style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '1px',
        backgroundColor: tokens.colors.border,
        border: `1px solid ${tokens.colors.border}`,
        borderRadius: '4px',
        marginBottom: '2.5rem',
        overflow: 'hidden',
      }}>
        <MetricCard
          value={seatedDeputados}
          label="Em Exercício"
          sublabel={`de ${totalElected} eleitos · ${totais.partidos || 0} partidos`}
        />
        <MetricCard
          value={governoDeputados}
          label="Governo"
          sublabel={`${((governoDeputados / seatedDeputados) * 100).toFixed(0)}% dos assentos`}
          accent="primary"
        />
        <MetricCard
          value={oposicaoDeputados}
          label="Oposição"
          sublabel={`${((oposicaoDeputados / seatedDeputados) * 100).toFixed(0)}% dos assentos`}
          accent="accent"
        />
        <MetricCard
          value={calcularFragmentacao()}
          label="Fragmentação"
          sublabel="Partidos efetivos"
        />
      </section>

      {/* Main Content Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '1.5rem',
        marginBottom: '2.5rem',
      }}>
        {/* Party Composition */}
        <section style={{
          backgroundColor: tokens.colors.bgSecondary,
          border: `1px solid ${tokens.colors.border}`,
          borderRadius: '4px',
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
              Composição Partidária
            </h2>
            <p style={{
              fontSize: '0.8125rem',
              color: tokens.colors.textMuted,
              margin: '0.25rem 0 0',
            }}>
              Distribuição dos {seatedDeputados} assentos em exercício
            </p>
          </div>
          <div style={{ padding: '1.5rem' }}>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={partidosData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={90}
                  dataKey="deputados"
                  stroke="#FFFFFF"
                  strokeWidth={2}
                >
                  {partidosData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.cor} />
                  ))}
                </Pie>
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
                <Legend
                  formatter={(value, entry) => (
                    <span style={{ color: tokens.colors.textSecondary, fontSize: '0.75rem' }}>
                      {value}
                    </span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Government Stability */}
        <section style={{
          backgroundColor: tokens.colors.bgSecondary,
          border: `1px solid ${tokens.colors.border}`,
          borderRadius: '4px',
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
              Balanço Parlamentar
            </h2>
            <p style={{
              fontSize: '0.8125rem',
              color: tokens.colors.textMuted,
              margin: '0.25rem 0 0',
            }}>
              Correlação de forças Governo vs. Oposição
            </p>
          </div>
          <div style={{ padding: '1.5rem' }}>
            {/* Government bar */}
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: '0.5rem',
              }}>
                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: tokens.colors.textMuted,
                }}>Governo</span>
                <span style={{
                  fontFamily: tokens.fonts.mono,
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: tokens.colors.primary,
                }}>{governoDeputados}</span>
              </div>
              <div style={{
                height: '24px',
                backgroundColor: tokens.colors.bgTertiary,
                borderRadius: '2px',
                overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%',
                  width: `${(governoDeputados / seatedDeputados) * 100}%`,
                  backgroundColor: tokens.colors.primary,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                  paddingRight: '0.5rem',
                }}>
                  <span style={{
                    fontFamily: tokens.fonts.mono,
                    fontSize: '0.6875rem',
                    fontWeight: 600,
                    color: '#FFFFFF',
                  }}>
                    {((governoDeputados / seatedDeputados) * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Opposition bar */}
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: '0.5rem',
              }}>
                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: tokens.colors.textMuted,
                }}>Oposição</span>
                <span style={{
                  fontFamily: tokens.fonts.mono,
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: tokens.colors.accent,
                }}>{oposicaoDeputados}</span>
              </div>
              <div style={{
                height: '24px',
                backgroundColor: tokens.colors.bgTertiary,
                borderRadius: '2px',
                overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%',
                  width: `${(oposicaoDeputados / seatedDeputados) * 100}%`,
                  backgroundColor: tokens.colors.accent,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                  paddingRight: '0.5rem',
                }}>
                  <span style={{
                    fontFamily: tokens.fonts.mono,
                    fontSize: '0.6875rem',
                    fontWeight: 600,
                    color: '#FFFFFF',
                  }}>
                    {((oposicaoDeputados / seatedDeputados) * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Majority line */}
            <div style={{
              paddingTop: '1rem',
              borderTop: `1px solid ${tokens.colors.border}`,
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '0.75rem',
              }}>
                <span style={{
                  fontSize: '0.8125rem',
                  color: tokens.colors.textSecondary,
                }}>Maioria absoluta necessária</span>
                <span style={{
                  fontFamily: tokens.fonts.mono,
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: tokens.colors.textPrimary,
                }}>{maioriaAbsoluta}</span>
              </div>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.75rem 1rem',
                backgroundColor: temMaioria ? '#F0FDF4' : '#FFFBEB',
                border: `1px solid ${temMaioria ? '#86EFAC' : '#FCD34D'}`,
                borderRadius: '4px',
              }}>
                <span style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: temMaioria ? tokens.colors.success : tokens.colors.warning,
                }} />
                <span style={{
                  fontSize: '0.8125rem',
                  fontWeight: 500,
                  color: temMaioria ? tokens.colors.success : tokens.colors.warning,
                }}>
                  {temMaioria
                    ? `Governo com maioria (+${governoDeputados - maioriaAbsoluta})`
                    : `Faltam ${maioriaAbsoluta - governoDeputados} para maioria`}
                </span>
              </div>
            </div>
          </div>
        </section>
      </div>

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
                        to={`/partidos/${encodeURIComponent(partido.id)}`}
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

// Metric Card Component
const MetricCard = ({ value, label, sublabel, accent }) => (
  <div style={{
    backgroundColor: tokens.colors.bgSecondary,
    padding: '1.25rem 1.5rem',
    textAlign: 'center',
    borderLeft: accent === 'primary' ? `3px solid ${tokens.colors.primary}` :
               accent === 'accent' ? `3px solid ${tokens.colors.accent}` : 'none',
  }}>
    <div style={{
      fontFamily: tokens.fonts.mono,
      fontSize: '2rem',
      fontWeight: 700,
      color: accent === 'primary' ? tokens.colors.primary :
             accent === 'accent' ? tokens.colors.accent : tokens.colors.textPrimary,
      lineHeight: 1,
      marginBottom: '0.5rem',
    }}>
      {value}
    </div>
    <div style={{
      fontSize: '0.6875rem',
      fontWeight: 600,
      textTransform: 'uppercase',
      letterSpacing: '0.08em',
      color: tokens.colors.textMuted,
      marginBottom: '0.125rem',
    }}>
      {label}
    </div>
    {sublabel && (
      <div style={{
        fontSize: '0.75rem',
        color: tokens.colors.textMuted,
      }}>
        {sublabel}
      </div>
    )}
  </div>
)

export default Dashboard
