import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Users, TrendingUp, ArrowRight, Building, Handshake } from 'lucide-react';
import { apiFetch } from '../config/api';
import { tokens } from '../styles/tokens';
import { LoadingSpinner, PageHeader } from './common';

const PartidosPage = () => {
  const [partidos, setPartidos] = useState([]);
  const [coligacoes, setColigacoes] = useState([]);
  const [legislaturaInfo, setLegislaturaInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState('all');
  const [showInactiveCoalitions, setShowInactiveCoalitions] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    fetchData();
  }, [showInactiveCoalitions]);

  const fetchData = async () => {
    try {
      const partidosResponse = await apiFetch('partidos');
      const partidosData = await partidosResponse.json();
      setPartidos(partidosData.partidos || []);

      const coligacoesResponse = await apiFetch(`coligacoes?include_inactive=${showInactiveCoalitions}`);
      const coligacoesData = await coligacoesResponse.json();
      setColigacoes(coligacoesData.coligacoes || []);

      const legislaturasResponse = await apiFetch('legislaturas');
      const legislaturasData = await legislaturasResponse.json();

      const currentLegislature = legislaturasData.legislaturas?.find(leg => leg.data_fim === null);
      if (currentLegislature) {
        setLegislaturaInfo(currentLegislature);
      }
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  };

  // Keep original party colors for visual identification
  const partidoCores = {
    'PSD': '#FF6B35',
    'CH': '#1E3A8A',
    'PS': '#EF4444',
    'IL': '#06B6D4',
    'L': '#10B981',
    'PCP': '#DC2626',
    'CDS-PP': '#F59E0B',
    'BE': '#8B5CF6',
    'PAN': '#22C55E',
    'JPP': '#6366F1'
  };

  const spectrumColors = {
    'esquerda': '#DC2626',
    'centro-esquerda': '#F59E0B',
    'centro': '#6B7280',
    'centro-direita': '#3B82F6',
    'direita': '#1E40AF'
  };

  const getLegislatureDisplayText = () => {
    if (!legislaturaInfo) return 'XVII Legislatura (2025-presente)';

    const numero = legislaturaInfo.numero;
    const dataInicio = legislaturaInfo.data_inicio ? new Date(legislaturaInfo.data_inicio).getFullYear() : null;
    const dataFim = legislaturaInfo.data_fim ? new Date(legislaturaInfo.data_fim).getFullYear() : null;

    if (dataInicio && dataFim) {
      return `${numero} Legislatura (${dataInicio}-${dataFim})`;
    } else if (dataInicio) {
      return `${numero} Legislatura (${dataInicio}-presente)`;
    } else {
      return `${numero} Legislatura`;
    }
  };

  if (loading) {
    return <LoadingSpinner message="A carregar partidos" />;
  }

  const totalDeputados = partidos.reduce((sum, partido) => sum + partido.num_deputados, 0);
  const activeColigacoes = coligacoes.filter(c => c.ativa);

  const tabs = [
    { id: 'all', label: 'Todos' },
    { id: 'partidos', label: `Partidos (${partidos.length})` },
    { id: 'coligacoes', label: `Coligações (${coligacoes.length})` },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ textAlign: 'center' }}
      >
        <h1
          style={{
            fontFamily: tokens.fonts.headline,
            fontSize: '2.25rem',
            fontWeight: 700,
            color: tokens.colors.textPrimary,
            marginBottom: '0.75rem',
          }}
        >
          Partidos e Coligações
        </h1>
        <div style={{ marginBottom: '0.75rem' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '0.25rem 0.75rem',
              fontFamily: tokens.fonts.body,
              fontSize: '0.8125rem',
              fontWeight: 500,
              color: tokens.colors.primary,
              backgroundColor: '#F0F7F4',
              borderRadius: '2px',
            }}
          >
            {getLegislatureDisplayText()}
          </span>
        </div>
        <p
          style={{
            fontFamily: tokens.fonts.body,
            fontSize: '1rem',
            color: tokens.colors.textSecondary,
            maxWidth: '48rem',
            margin: '0 auto',
          }}
        >
          Panorama completo dos partidos políticos e coligações no Parlamento Português
        </p>
      </motion.div>

      {/* Statistics */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '1rem',
        }}
      >
        {[
          { icon: Building, label: 'PARTIDOS', value: partidos.length, color: tokens.colors.primary },
          { icon: Handshake, label: 'COLIGAÇÕES', value: coligacoes.length, color: '#7C3AED' },
          { icon: Users, label: 'DEPUTADOS', value: totalDeputados, color: tokens.colors.primary },
          { icon: TrendingUp, label: 'COLIGAÇÕES ATIVAS', value: activeColigacoes.length, color: '#D97706' },
        ].map((stat, index) => (
          <div
            key={stat.label}
            style={{
              backgroundColor: tokens.colors.bgSecondary,
              border: `1px solid ${tokens.colors.border}`,
              borderRadius: '4px',
              padding: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <stat.icon size={24} style={{ color: stat.color }} />
              <div>
                <p
                  style={{
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.6875rem',
                    fontWeight: 600,
                    color: tokens.colors.textMuted,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: '0.125rem',
                  }}
                >
                  {stat.label}
                </p>
                <p
                  style={{
                    fontFamily: tokens.fonts.mono,
                    fontSize: '1.5rem',
                    fontWeight: 700,
                    color: tokens.colors.textPrimary,
                  }}
                >
                  {stat.value}
                </p>
              </div>
            </div>
          </div>
        ))}
      </motion.div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
        <div
          style={{
            display: 'flex',
            gap: '0.25rem',
            padding: '0.25rem',
            backgroundColor: tokens.colors.bgSecondary,
            border: `1px solid ${tokens.colors.border}`,
            borderRadius: '4px',
          }}
        >
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveView(tab.id)}
              style={{
                padding: '0.5rem 1.25rem',
                fontFamily: tokens.fonts.body,
                fontSize: '0.875rem',
                fontWeight: activeView === tab.id ? 600 : 500,
                color: activeView === tab.id ? tokens.colors.bgSecondary : tokens.colors.textSecondary,
                backgroundColor: activeView === tab.id ? tokens.colors.primary : 'transparent',
                border: 'none',
                borderRadius: '2px',
                cursor: 'pointer',
                transition: 'all 150ms ease',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {(activeView === 'all' || activeView === 'coligacoes') && (
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontFamily: tokens.fonts.body,
              fontSize: '0.8125rem',
              color: tokens.colors.textSecondary,
              cursor: 'pointer',
            }}
          >
            <input
              type="checkbox"
              checked={showInactiveCoalitions}
              onChange={(e) => setShowInactiveCoalitions(e.target.checked)}
              style={{
                width: '16px',
                height: '16px',
                accentColor: tokens.colors.primary,
              }}
            />
            Mostrar coligações inativas
          </label>
        )}
      </div>

      {/* Parties Section */}
      {(activeView === 'all' || activeView === 'partidos') && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <h2
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontFamily: tokens.fonts.headline,
              fontSize: '1.375rem',
              fontWeight: 700,
              color: tokens.colors.textPrimary,
              marginBottom: '1.25rem',
            }}
          >
            <Building size={20} style={{ color: tokens.colors.primary }} />
            Partidos Individuais
          </h2>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
              gap: '1rem',
            }}
          >
            {(partidos || []).map((partido, index) => {
              const partyColor = partidoCores[partido.sigla] || '#6B7280';
              return (
                <motion.div
                  key={partido.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.03 * index }}
                >
                  <div
                    style={{
                      backgroundColor: tokens.colors.bgSecondary,
                      border: `1px solid ${tokens.colors.border}`,
                      borderRadius: '4px',
                      overflow: 'hidden',
                      transition: 'border-color 150ms ease',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.borderColor = tokens.colors.borderStrong}
                    onMouseLeave={(e) => e.currentTarget.style.borderColor = tokens.colors.border}
                  >
                    {/* Party color bar */}
                    <div style={{ height: '3px', backgroundColor: partyColor }} />

                    <div style={{ padding: '1.25rem' }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <div>
                          <h3
                            style={{
                              fontFamily: tokens.fonts.body,
                              fontSize: '1.5rem',
                              fontWeight: 700,
                              color: tokens.colors.textPrimary,
                              marginBottom: '0.25rem',
                            }}
                          >
                            {partido.sigla}
                          </h3>
                          <p
                            style={{
                              fontFamily: tokens.fonts.body,
                              fontSize: '0.8125rem',
                              color: tokens.colors.textSecondary,
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                            }}
                          >
                            {partido.nome}
                          </p>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div
                            style={{
                              fontFamily: tokens.fonts.mono,
                              fontSize: '1.75rem',
                              fontWeight: 700,
                              color: partyColor,
                            }}
                          >
                            {partido.num_deputados}
                          </div>
                          <div
                            style={{
                              fontFamily: tokens.fonts.body,
                              fontSize: '0.6875rem',
                              color: tokens.colors.textMuted,
                              textTransform: 'uppercase',
                              letterSpacing: '0.03em',
                            }}
                          >
                            deputados
                          </div>
                        </div>
                      </div>

                      {/* Progress bar */}
                      <div style={{ marginBottom: '1rem' }}>
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            fontFamily: tokens.fonts.body,
                            fontSize: '0.75rem',
                            color: tokens.colors.textMuted,
                            marginBottom: '0.375rem',
                          }}
                        >
                          <span>Representação</span>
                          <span style={{ fontFamily: tokens.fonts.mono }}>
                            {((partido.num_deputados / 230) * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div
                          style={{
                            width: '100%',
                            height: '4px',
                            backgroundColor: '#F5F5F5',
                            borderRadius: '2px',
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              height: '100%',
                              width: `${(partido.num_deputados / 230) * 100}%`,
                              backgroundColor: partyColor,
                              transition: 'width 500ms ease',
                            }}
                          />
                        </div>
                      </div>

                      <Link
                        to={`/partidos/${partido.sigla}`}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.375rem',
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.8125rem',
                          fontWeight: 600,
                          color: tokens.colors.primary,
                          textDecoration: 'none',
                          transition: 'opacity 150ms ease',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'}
                        onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                      >
                        Ver detalhes
                        <ArrowRight size={14} />
                      </Link>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* Coalitions Section */}
      {(activeView === 'all' || activeView === 'coligacoes') && coligacoes.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: activeView === 'all' ? 0.3 : 0.2 }}
        >
          <h2
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontFamily: tokens.fonts.headline,
              fontSize: '1.375rem',
              fontWeight: 700,
              color: tokens.colors.textPrimary,
              marginBottom: '1.25rem',
            }}
          >
            <Handshake size={20} style={{ color: '#7C3AED' }} />
            Coligações
          </h2>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
              gap: '1rem',
            }}
          >
            {coligacoes.map((coligacao, index) => {
              const spectrumColor = spectrumColors[coligacao.espectro_politico] || '#6B7280';
              return (
                <motion.div
                  key={coligacao.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.03 * index }}
                >
                  <div
                    style={{
                      backgroundColor: tokens.colors.bgSecondary,
                      border: `1px solid ${tokens.colors.border}`,
                      borderRadius: '4px',
                      overflow: 'hidden',
                      transition: 'border-color 150ms ease',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.borderColor = tokens.colors.borderStrong}
                    onMouseLeave={(e) => e.currentTarget.style.borderColor = tokens.colors.border}
                  >
                    {/* Coalition color bar */}
                    <div style={{ height: '4px', backgroundColor: spectrumColor }} />

                    <div style={{ padding: '1.25rem' }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.375rem' }}>
                            <h3
                              style={{
                                fontFamily: tokens.fonts.body,
                                fontSize: '1.5rem',
                                fontWeight: 700,
                                color: tokens.colors.textPrimary,
                              }}
                            >
                              {coligacao.sigla}
                            </h3>
                            <Handshake size={16} style={{ color: '#7C3AED' }} />
                            {coligacao.ativa && (
                              <span
                                style={{
                                  padding: '0.125rem 0.5rem',
                                  fontFamily: tokens.fonts.body,
                                  fontSize: '0.625rem',
                                  fontWeight: 600,
                                  textTransform: 'uppercase',
                                  letterSpacing: '0.03em',
                                  color: tokens.colors.primary,
                                  backgroundColor: '#F0F7F4',
                                  borderRadius: '2px',
                                }}
                              >
                                Ativa
                              </span>
                            )}
                          </div>
                          <p
                            style={{
                              fontFamily: tokens.fonts.body,
                              fontSize: '0.8125rem',
                              color: tokens.colors.textSecondary,
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                            }}
                          >
                            {coligacao.nome}
                          </p>
                          {coligacao.espectro_politico && (
                            <span
                              style={{
                                display: 'inline-block',
                                marginTop: '0.5rem',
                                padding: '0.125rem 0.5rem',
                                fontFamily: tokens.fonts.body,
                                fontSize: '0.6875rem',
                                color: tokens.colors.textMuted,
                                backgroundColor: '#F5F5F5',
                                borderRadius: '2px',
                              }}
                            >
                              {coligacao.espectro_politico}
                            </span>
                          )}
                        </div>
                        <div style={{ textAlign: 'right', marginLeft: '1rem' }}>
                          <div
                            style={{
                              fontFamily: tokens.fonts.mono,
                              fontSize: '1.75rem',
                              fontWeight: 700,
                              color: '#7C3AED',
                            }}
                          >
                            {coligacao.deputy_count || 0}
                          </div>
                          <div
                            style={{
                              fontFamily: tokens.fonts.body,
                              fontSize: '0.6875rem',
                              color: tokens.colors.textMuted,
                              textTransform: 'uppercase',
                              letterSpacing: '0.03em',
                            }}
                          >
                            deputados
                          </div>
                        </div>
                      </div>

                      {/* Component parties preview */}
                      {coligacao.component_parties && coligacao.component_parties.length > 0 && (
                        <div style={{ marginBottom: '0.75rem' }}>
                          <p
                            style={{
                              fontFamily: tokens.fonts.body,
                              fontSize: '0.6875rem',
                              color: tokens.colors.textMuted,
                              textTransform: 'uppercase',
                              letterSpacing: '0.03em',
                              marginBottom: '0.375rem',
                            }}
                          >
                            Partidos componentes
                          </p>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                            {coligacao.component_parties.slice(0, 3).map(party => (
                              <span
                                key={party.sigla}
                                style={{
                                  padding: '0.125rem 0.5rem',
                                  fontFamily: tokens.fonts.body,
                                  fontSize: '0.75rem',
                                  fontWeight: 500,
                                  color: tokens.colors.primary,
                                  backgroundColor: '#F0F7F4',
                                  borderRadius: '2px',
                                }}
                              >
                                {party.sigla}
                              </span>
                            ))}
                            {coligacao.component_parties.length > 3 && (
                              <span
                                style={{
                                  padding: '0.125rem 0.5rem',
                                  fontFamily: tokens.fonts.body,
                                  fontSize: '0.75rem',
                                  color: tokens.colors.textMuted,
                                  backgroundColor: '#F5F5F5',
                                  borderRadius: '2px',
                                }}
                              >
                                +{coligacao.component_parties.length - 3}
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Dates */}
                      {(coligacao.data_formacao || coligacao.data_dissolucao) && (
                        <div
                          style={{
                            fontFamily: tokens.fonts.body,
                            fontSize: '0.75rem',
                            color: tokens.colors.textMuted,
                            marginBottom: '0.75rem',
                          }}
                        >
                          {coligacao.data_formacao && (
                            <p>Formada: {new Date(coligacao.data_formacao).getFullYear()}</p>
                          )}
                          {coligacao.data_dissolucao && (
                            <p>Dissolvida: {new Date(coligacao.data_dissolucao).getFullYear()}</p>
                          )}
                        </div>
                      )}

                      <Link
                        to={`/coligacoes/${encodeURIComponent(coligacao.sigla)}`}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.375rem',
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.8125rem',
                          fontWeight: 600,
                          color: '#7C3AED',
                          textDecoration: 'none',
                          transition: 'opacity 150ms ease',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'}
                        onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                      >
                        Ver detalhes
                        <ArrowRight size={14} />
                      </Link>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default PartidosPage;
