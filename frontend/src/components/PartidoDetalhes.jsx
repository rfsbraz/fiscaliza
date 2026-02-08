import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, Users, MapPin, User, BarChart3, TrendingUp, UserCheck, Handshake } from 'lucide-react';
import PartyVotingAnalytics from './PartyVotingAnalytics';
import PartyDemographics from './PartyDemographics';
import { apiFetch } from '../config/api';
import { tokens } from '../styles/tokens';
import { LoadingSpinner } from './common';

const PartidoDetalhes = () => {
  const { partidoId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Get active tab from URL hash, default to 'deputados'
  const getActiveTabFromUrl = () => {
    const hash = location.hash.replace('#', '');
    const validTabs = ['deputados', 'analytics', 'demografia'];
    return validTabs.includes(hash) ? hash : 'deputados';
  };

  const [activeTab, setActiveTab] = useState(getActiveTabFromUrl());

  // Sync activeTab with URL hash changes
  useEffect(() => {
    const handleHashChange = () => {
      setActiveTab(getActiveTabFromUrl());
    };

    window.addEventListener('hashchange', handleHashChange);
    setActiveTab(getActiveTabFromUrl());

    return () => {
      window.removeEventListener('hashchange', handleHashChange);
    };
  }, [location.hash]);

  // Handle tab change with URL update
  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    navigate(`#${tabId}`, { replace: true });
  };

  // Set default tab in URL if no hash is present
  useEffect(() => {
    if (!location.hash) {
      navigate('#deputados', { replace: true });
    }
  }, [navigate, location.hash]);

  useEffect(() => {
    const fetchDados = async () => {
      try {
        setLoading(true);
        // Fetch all party deputies from all periods (no legislatura filter)
        const response = await apiFetch(`partidos/${encodeURIComponent(partidoId)}/deputados`);
        if (!response.ok) {
          throw new Error('Erro ao carregar dados do partido');
        }
        const data = await response.json();
        setDados(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (partidoId) {
      fetchDados();
    }
  }, [partidoId]);

  if (loading) {
    return <LoadingSpinner message="A carregar dados do partido" />;
  }

  if (error) {
    return (
      <div
        style={{
          minHeight: '100vh',
          backgroundColor: tokens.colors.bgPrimary,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <p
            style={{
              fontFamily: tokens.fonts.body,
              color: tokens.colors.accent,
              marginBottom: '1rem',
            }}
          >
            Erro: {error}
          </p>
          <Link
            to="/partidos"
            style={{
              fontFamily: tokens.fonts.body,
              color: tokens.colors.primary,
              textDecoration: 'underline',
            }}
          >
            Voltar aos partidos
          </Link>
        </div>
      </div>
    );
  }

  if (!dados) {
    return (
      <div
        style={{
          minHeight: '100vh',
          backgroundColor: tokens.colors.bgPrimary,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <p style={{ fontFamily: tokens.fonts.body, color: tokens.colors.textSecondary }}>
          Partido não encontrado
        </p>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: tokens.colors.bgPrimary }}>
      {/* Header */}
      <div
        style={{
          backgroundColor: tokens.colors.bgSecondary,
          borderBottom: `1px solid ${tokens.colors.border}`,
        }}
      >
        <div
          style={{
            maxWidth: '1280px',
            margin: '0 auto',
            padding: '1rem 1.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <Link
                to="/partidos"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  fontFamily: tokens.fonts.body,
                  color: tokens.colors.textSecondary,
                  textDecoration: 'none',
                  transition: 'color 150ms ease',
                }}
                onMouseEnter={(e) => e.target.style.color = tokens.colors.textPrimary}
                onMouseLeave={(e) => e.target.style.color = tokens.colors.textSecondary}
              >
                <ArrowLeft style={{ width: '20px', height: '20px', marginRight: '0.5rem' }} />
                Voltar aos Partidos
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '2rem 1.5rem' }}>
        {/* Informação do Partido */}
        <div
          style={{
            backgroundColor: tokens.colors.bgSecondary,
            border: `1px solid ${tokens.colors.border}`,
            borderRadius: '4px',
            marginBottom: '2rem',
          }}
        >
          <div style={{ padding: '1.5rem 2rem' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
              <div>
                <h1
                  style={{
                    fontFamily: tokens.fonts.headline,
                    fontSize: '2rem',
                    fontWeight: 700,
                    color: tokens.colors.textPrimary,
                    marginBottom: '0.5rem',
                  }}
                >
                  {dados.partido.sigla}
                </h1>
                <p
                  style={{
                    fontFamily: tokens.fonts.body,
                    fontSize: '1.125rem',
                    color: tokens.colors.textSecondary,
                  }}
                >
                  {dados.partido.nome}
                </p>
                {dados.coligacao && (
                  <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center' }}>
                    <Handshake style={{ width: '16px', height: '16px', marginRight: '0.5rem', color: tokens.colors.purple }} />
                    <span style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', color: tokens.colors.textSecondary }}>
                      Parte da coligação{' '}
                      <Link
                        to={`/coligacoes/${encodeURIComponent(dados.coligacao.sigla)}`}
                        style={{
                          color: tokens.colors.purple,
                          fontWeight: 600,
                          textDecoration: 'underline',
                        }}
                      >
                        {dados.coligacao.sigla}
                      </Link>
                      {dados.coligacao.nome && dados.coligacao.nome !== dados.coligacao.sigla && (
                        <span style={{ color: tokens.colors.textMuted }}> ({dados.coligacao.nome})</span>
                      )}
                    </span>
                  </div>
                )}
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ display: 'flex', alignItems: 'center', color: tokens.colors.textSecondary, marginBottom: '0.5rem' }}>
                  <Users style={{ width: '20px', height: '20px', marginRight: '0.5rem' }} />
                  <span
                    style={{
                      fontFamily: tokens.fonts.mono,
                      fontSize: '1.5rem',
                      fontWeight: 700,
                      color: tokens.colors.primary,
                    }}
                  >
                    {dados.total}
                  </span>
                  <span style={{ fontFamily: tokens.fonts.body, marginLeft: '0.25rem' }}>deputados</span>
                </div>
                <div style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', color: tokens.colors.textMuted }}>
                  {dados.mandatos_ativos} mandatos ativos
                </div>
              </div>
            </div>

            {/* Estatísticas Rápidas */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1.5rem' }}>
              <div
                style={{
                  backgroundColor: '#E8F5E9',
                  borderRadius: '4px',
                  padding: '1rem',
                  border: `1px solid ${tokens.colors.border}`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <Users style={{ width: '32px', height: '32px', color: tokens.colors.primary }} />
                  <div style={{ marginLeft: '0.75rem' }}>
                    <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.75rem', fontWeight: 600, color: tokens.colors.primary, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Total Histórico
                    </p>
                    <p style={{ fontFamily: tokens.fonts.mono, fontSize: '1.5rem', fontWeight: 700, color: tokens.colors.textPrimary }}>
                      {dados.total}
                    </p>
                    <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.75rem', color: tokens.colors.primary }}>
                      todas as legislaturas
                    </p>
                  </div>
                </div>
              </div>

              <div
                style={{
                  backgroundColor: '#E3F2FD',
                  borderRadius: '4px',
                  padding: '1rem',
                  border: `1px solid ${tokens.colors.border}`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <MapPin style={{ width: '32px', height: '32px', color: tokens.colors.blue }} />
                  <div style={{ marginLeft: '0.75rem' }}>
                    <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.75rem', fontWeight: 600, color: tokens.colors.blue, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Círculos Históricos
                    </p>
                    <p style={{ fontFamily: tokens.fonts.mono, fontSize: '1.5rem', fontWeight: 700, color: tokens.colors.textPrimary }}>
                      {dados.historico?.total_circulos || new Set(dados.deputados.map(d => d.circulo)).size}
                    </p>
                    <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.75rem', color: tokens.colors.blue }}>
                      distritos eleitorais
                    </p>
                  </div>
                </div>
              </div>

              <div
                style={{
                  backgroundColor: '#F3E8FF',
                  borderRadius: '4px',
                  padding: '1rem',
                  border: `1px solid ${tokens.colors.border}`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <User style={{ width: '32px', height: '32px', color: tokens.colors.purple }} />
                  <div style={{ marginLeft: '0.75rem' }}>
                    <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.75rem', fontWeight: 600, color: tokens.colors.purple, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Mandatos Ativos
                    </p>
                    <p style={{ fontFamily: tokens.fonts.mono, fontSize: '1.5rem', fontWeight: 700, color: tokens.colors.textPrimary }}>
                      {dados.mandatos_ativos}
                    </p>
                    <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.75rem', color: tokens.colors.purple }}>
                      legislatura atual
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs de Atividade - Editorial-style section navigation */}
        <section style={{
          backgroundColor: tokens.colors.bgWarm || '#F8F6F0',
          border: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
          borderRadius: '4px',
          marginTop: '24px',
          overflow: 'hidden',
        }}>
          {/* Section Header */}
          <header style={{
            padding: '16px 24px',
            borderBottom: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
            backgroundColor: 'rgba(255,255,255,0.5)',
          }}>
            <h3 style={{
              fontFamily: tokens.fonts.headline,
              fontSize: '1.125rem',
              fontWeight: 600,
              color: tokens.colors.textPrimary,
              margin: 0,
            }}>
              Informação do Partido
            </h3>
            <p style={{
              fontSize: '0.8125rem',
              color: tokens.colors.textSecondary,
              marginTop: '4px',
            }}>
              Deputados, demografia e análise política
            </p>
          </header>

          {/* Editorial Tab Navigation */}
          <nav style={{
            display: 'flex',
            gap: '0',
            backgroundColor: tokens.colors.bgWarm || '#F8F6F0',
            borderBottom: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
            overflowX: 'auto',
            scrollbarWidth: 'none',
            msOverflowStyle: 'none',
          }}>
            {[
              { id: 'deputados', label: 'Deputados', icon: Users },
              { id: 'demografia', label: 'Demografia', icon: UserCheck },
              { id: 'analytics', label: 'Análise Política', icon: BarChart3 }
            ].map((tab, index, arr) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '14px 20px',
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.8125rem',
                    fontWeight: isActive ? 600 : 500,
                    letterSpacing: '0.01em',
                    color: isActive ? tokens.colors.primary : tokens.colors.textSecondary,
                    backgroundColor: isActive ? 'white' : 'transparent',
                    border: 'none',
                    borderBottom: isActive ? `2px solid ${tokens.colors.primary}` : '2px solid transparent',
                    borderRight: index < arr.length - 1 ? `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}` : 'none',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.2s ease',
                    position: 'relative',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.6)';
                      e.currentTarget.style.color = tokens.colors.textPrimary;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = 'transparent';
                      e.currentTarget.style.color = tokens.colors.textSecondary;
                    }
                  }}
                >
                  <span style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '28px',
                    height: '28px',
                    borderRadius: '4px',
                    backgroundColor: isActive ? `${tokens.colors.primary}12` : tokens.colors.bgTertiary,
                    transition: 'background-color 0.2s ease',
                  }}>
                    <Icon style={{
                      width: '15px',
                      height: '15px',
                      color: isActive ? tokens.colors.primary : tokens.colors.textMuted,
                    }} />
                  </span>
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Tab Content - White background for readability */}
          <div style={{
            padding: '28px',
            backgroundColor: 'white',
            minHeight: '400px',
          }}>
            {activeTab === 'deputados' && (
              <div>
                {/* Tab Section Header */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '24px',
                  paddingBottom: '20px',
                  borderBottom: `1px solid ${tokens.colors.border}`,
                }}>
                  <div style={{ flex: 1 }}>
                    <h3 style={{
                      fontSize: '1.125rem',
                      fontWeight: 600,
                      color: tokens.colors.textPrimary,
                      fontFamily: tokens.fonts.headline,
                      margin: 0,
                    }}>
                      Deputados do {dados.partido.sigla}
                    </h3>
                    <p style={{
                      fontSize: '0.8125rem',
                      color: tokens.colors.textMuted,
                      marginTop: '6px',
                      fontFamily: tokens.fonts.body,
                    }}>
                      Histórico completo de {dados.total} deputados ao longo de todas as legislaturas
                    </p>
                  </div>
                  <div style={{
                    fontFamily: tokens.fonts.mono,
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: tokens.colors.primary,
                    backgroundColor: `${tokens.colors.primary}10`,
                    padding: '6px 12px',
                    borderRadius: '4px',
                    border: `1px solid ${tokens.colors.primary}25`,
                  }}>
                    {dados.mandatos_ativos} ativos
                  </div>
                </div>

                {/* Historical Summary Bar */}
                {dados.historico && (
                  <div style={{
                    display: 'flex',
                    gap: '24px',
                    padding: '16px 20px',
                    backgroundColor: tokens.colors.bgWarm || '#F8F6F0',
                    border: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
                    borderRadius: '4px',
                    marginBottom: '24px',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: tokens.colors.textMuted,
                        textTransform: 'uppercase',
                        letterSpacing: '0.03em',
                        fontFamily: tokens.fonts.body,
                      }}>Período</span>
                      <span style={{
                        fontSize: '0.875rem',
                        fontWeight: 500,
                        color: tokens.colors.textPrimary,
                        fontFamily: tokens.fonts.mono,
                      }}>{dados.historico.periodo_atividade || 'N/A'}</span>
                    </div>
                    <div style={{ width: '1px', backgroundColor: tokens.colors.borderWarm || '#E8E4DA' }} />
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: tokens.colors.textMuted,
                        textTransform: 'uppercase',
                        letterSpacing: '0.03em',
                        fontFamily: tokens.fonts.body,
                      }}>Legislaturas</span>
                      <span style={{
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: tokens.colors.primary,
                        fontFamily: tokens.fonts.mono,
                      }}>{dados.historico.total_legislaturas || 0}</span>
                    </div>
                    <div style={{ width: '1px', backgroundColor: tokens.colors.borderWarm || '#E8E4DA' }} />
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: tokens.colors.textMuted,
                        textTransform: 'uppercase',
                        letterSpacing: '0.03em',
                        fontFamily: tokens.fonts.body,
                      }}>Círculos</span>
                      <span style={{
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: tokens.colors.primary,
                        fontFamily: tokens.fonts.mono,
                      }}>{dados.historico.total_circulos || 0}</span>
                    </div>
                  </div>
                )}

                <div>
                  {dados.deputados.map((deputado) => (
                    <div
                      key={deputado.id}
                      style={{
                        padding: '1rem 0',
                        borderBottom: `1px solid ${tokens.colors.border}`,
                        transition: 'background-color 150ms ease',
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = tokens.colors.bgPrimary}
                      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <div style={{ flexShrink: 0, position: 'relative' }}>
                              {deputado.picture_url ? (
                                <div style={{ width: '48px', height: '48px', position: 'relative' }}>
                                  <img
                                    src={deputado.picture_url}
                                    alt={deputado.nome}
                                    style={{
                                      width: '48px',
                                      height: '48px',
                                      borderRadius: '50%',
                                      objectFit: 'cover',
                                      backgroundColor: tokens.colors.border,
                                      border: `2px solid ${tokens.colors.bgSecondary}`,
                                    }}
                                    onError={(e) => {
                                      e.target.style.display = 'none';
                                      e.target.nextSibling.style.display = 'flex';
                                    }}
                                  />
                                  <div
                                    style={{
                                      width: '48px',
                                      height: '48px',
                                      borderRadius: '50%',
                                      backgroundColor: '#E8F5E9',
                                      display: 'none',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                      border: `2px solid ${tokens.colors.bgSecondary}`,
                                    }}
                                  >
                                    <User style={{ width: '24px', height: '24px', color: tokens.colors.primary }} />
                                  </div>
                                </div>
                              ) : (
                                <div
                                  style={{
                                    width: '48px',
                                    height: '48px',
                                    borderRadius: '50%',
                                    backgroundColor: '#E8F5E9',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    border: `2px solid ${tokens.colors.bgSecondary}`,
                                  }}
                                >
                                  <User style={{ width: '24px', height: '24px', color: tokens.colors.primary }} />
                                </div>
                              )}
                            </div>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <Link
                                to={`/deputados/${deputado.id_cadastro || deputado.id}`}
                                style={{
                                  fontFamily: tokens.fonts.body,
                                  fontSize: '1rem',
                                  fontWeight: 600,
                                  color: tokens.colors.textPrimary,
                                  textDecoration: 'none',
                                  transition: 'color 150ms ease',
                                }}
                                onMouseEnter={(e) => e.target.style.color = tokens.colors.primary}
                                onMouseLeave={(e) => e.target.style.color = tokens.colors.textPrimary}
                              >
                                {deputado.nome}
                              </Link>
                              {deputado.profissao && (
                                <p
                                  style={{
                                    fontFamily: tokens.fonts.body,
                                    fontSize: '0.875rem',
                                    color: tokens.colors.textSecondary,
                                    marginTop: '0.25rem',
                                  }}
                                >
                                  {deputado.profissao}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.875rem', color: tokens.colors.textMuted }}>
                          <div style={{ display: 'flex', alignItems: 'center' }}>
                            <MapPin style={{ width: '16px', height: '16px', marginRight: '0.25rem' }} />
                            <span style={{ fontFamily: tokens.fonts.body }}>{deputado.circulo}</span>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center' }}>
                            <span style={{ fontFamily: tokens.fonts.body, fontSize: '0.75rem', color: tokens.colors.textMuted }}>
                              {deputado.mandato_ativo ?
                                `Leg. ${deputado.ultima_legislatura} (atual)` :
                                `Última: Leg. ${deputado.ultima_legislatura}`
                              }
                            </span>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center' }}>
                            {deputado.mandato_ativo ? (
                              <span
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  padding: '0.25rem 0.625rem',
                                  borderRadius: '2px',
                                  fontSize: '0.75rem',
                                  fontFamily: tokens.fonts.body,
                                  fontWeight: 600,
                                  backgroundColor: '#E8F5E9',
                                  color: tokens.colors.primary,
                                }}
                              >
                                Ativo
                              </span>
                            ) : (
                              <span
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  padding: '0.25rem 0.625rem',
                                  borderRadius: '2px',
                                  fontSize: '0.75rem',
                                  fontFamily: tokens.fonts.body,
                                  fontWeight: 600,
                                  backgroundColor: '#F5F5F5',
                                  color: tokens.colors.textMuted,
                                }}
                              >
                                Inativo
                              </span>
                            )}
                          </div>

                          <Link
                            to={`/deputados/${deputado.id_cadastro || deputado.id}`}
                            style={{
                              fontFamily: tokens.fonts.body,
                              fontSize: '0.875rem',
                              fontWeight: 600,
                              color: tokens.colors.primary,
                              textDecoration: 'none',
                              transition: 'opacity 150ms ease',
                            }}
                            onMouseEnter={(e) => e.target.style.opacity = '0.8'}
                            onMouseLeave={(e) => e.target.style.opacity = '1'}
                          >
                            Ver Detalhes →
                          </Link>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Resumo por Círculo */}
                <div
                  style={{
                    marginTop: '2rem',
                    backgroundColor: tokens.colors.bgPrimary,
                    borderRadius: '4px',
                    padding: '1.5rem',
                    border: `1px solid ${tokens.colors.border}`,
                  }}
                >
                  <h3
                    style={{
                      fontFamily: tokens.fonts.body,
                      fontSize: '1.125rem',
                      fontWeight: 600,
                      color: tokens.colors.textPrimary,
                      marginBottom: '1rem',
                    }}
                  >
                    Distribuição por Círculo Eleitoral
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
                    {Object.entries(
                      dados.deputados.reduce((acc, deputado) => {
                        acc[deputado.circulo] = (acc[deputado.circulo] || 0) + 1;
                        return acc;
                      }, {})
                    )
                      .sort(([,a], [,b]) => b - a)
                      .map(([circulo, count]) => (
                        <div
                          key={circulo}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '0.75rem',
                            backgroundColor: tokens.colors.bgSecondary,
                            borderRadius: '4px',
                            border: `1px solid ${tokens.colors.border}`,
                          }}
                        >
                          <span style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', fontWeight: 500, color: tokens.colors.textPrimary }}>{circulo}</span>
                          <span style={{ fontFamily: tokens.fonts.mono, fontSize: '0.875rem', fontWeight: 700, color: tokens.colors.primary }}>{count}</span>
                        </div>
                      ))
                    }
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'demografia' && (
              <div>
                {/* Tab Section Header */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '24px',
                  paddingBottom: '20px',
                  borderBottom: `1px solid ${tokens.colors.border}`,
                }}>
                  <div>
                    <h3 style={{
                      fontSize: '1.125rem',
                      fontWeight: 600,
                      color: tokens.colors.textPrimary,
                      fontFamily: tokens.fonts.headline,
                      margin: 0,
                    }}>
                      Demografia do Grupo Parlamentar
                    </h3>
                    <p style={{
                      fontSize: '0.8125rem',
                      color: tokens.colors.textMuted,
                      marginTop: '6px',
                      fontFamily: tokens.fonts.body,
                    }}>
                      Distribuição por género, idade e experiência parlamentar
                    </p>
                  </div>
                </div>
                <PartyDemographics
                  partidoId={partidoId}
                  dadosDemograficos={dados.demografia}
                  partidoInfo={dados.partido}
                />
              </div>
            )}

            {activeTab === 'analytics' && (
              <div>
                {/* Tab Section Header */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '24px',
                  paddingBottom: '20px',
                  borderBottom: `1px solid ${tokens.colors.border}`,
                }}>
                  <div>
                    <h3 style={{
                      fontSize: '1.125rem',
                      fontWeight: 600,
                      color: tokens.colors.textPrimary,
                      fontFamily: tokens.fonts.headline,
                      margin: 0,
                    }}>
                      Análise Política
                    </h3>
                    <p style={{
                      fontSize: '0.8125rem',
                      color: tokens.colors.textMuted,
                      marginTop: '6px',
                      fontFamily: tokens.fonts.body,
                    }}>
                      Padrões de votação, alinhamentos e colaboração cross-party
                    </p>
                  </div>
                </div>
                <PartyVotingAnalytics
                  partidoId={partidoId}
                  legislatura="17"
                />
              </div>
            )}
          </div>
        </section>

      </div>
    </div>
  );
};

export default PartidoDetalhes;
