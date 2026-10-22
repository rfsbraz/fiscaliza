import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Clock, MapPin, Users, FileText, Vote, Activity, AlertCircle } from 'lucide-react';
import { apiFetch } from '../config/api';
import { tokens } from '../styles/tokens';
import { LoadingSpinner, Section } from './common';
import { formatNumber, formatPercent } from '../utils/format';

const PainelIndisponivel = ({ titulo, mensagem }) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0.75rem',
      padding: '1.5rem',
      border: `1px dashed ${tokens.colors.border}`,
      borderRadius: '4px',
    }}
  >
    <AlertCircle size={18} style={{ color: tokens.colors.textMuted, flexShrink: 0, marginTop: '0.125rem' }} />
    <div>
      <h3
        style={{
          fontFamily: tokens.fonts.body,
          fontSize: '0.875rem',
          fontWeight: 600,
          color: tokens.colors.textPrimary,
          marginBottom: '0.25rem',
        }}
      >
        {titulo}
      </h3>
      <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.8125rem', color: tokens.colors.textSecondary }}>
        {mensagem}
      </p>
    </div>
  </div>
);

const AgendaPage = () => {
  const [agendaHoje, setAgendaHoje] = useState(null);
  const [agendaSemana, setAgendaSemana] = useState(null);
  const [votacoesRecentes, setVotacoesRecentes] = useState(null);
  const [estatisticas, setEstatisticas] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('hoje');

  useEffect(() => {
    fetchDados();
  }, []);

  // Each panel loads and fails on its own. Today and the week still come from the old
  // agenda code until the agenda mart lands, so a failed request there must not take the
  // votes and the stats down with it.
  const fetchDados = async () => {
    setLoading(true);
    const pedidos = [
      ['agenda/hoje', () => apiFetch('agenda/hoje'), setAgendaHoje],
      ['agenda/semana', () => apiFetch('agenda/semana'), setAgendaSemana],
      ['votacoes/recentes', () => apiFetch('votacoes/recentes?limite=5'), setVotacoesRecentes],
      ['estatisticas/atividade', () => apiFetch('estatisticas/atividade'), setEstatisticas],
    ];
    const resultados = await Promise.allSettled(
      pedidos.map(([, pedido]) => pedido().then((res) => res.json()))
    );
    resultados.forEach((resultado, i) => {
      const [nome, , setter] = pedidos[i];
      if (resultado.status === 'fulfilled') {
        setter(resultado.value);
      } else {
        console.error(`Erro ao carregar ${nome}:`, resultado.reason);
      }
    });
    setLoading(false);
  };

  const formatarHora = (hora) => {
    return hora || '--:--';
  };

  const getEstadoStyles = (estado) => {
    switch (estado) {
      case 'em_curso':
        return { color: tokens.colors.primary, backgroundColor: '#F0F7F4' };
      case 'concluido':
        return { color: tokens.colors.textMuted, backgroundColor: '#F5F5F5' };
      case 'cancelado':
        return { color: tokens.colors.accent, backgroundColor: '#FEF2F2' };
      default:
        return { color: '#2563EB', backgroundColor: '#EFF6FF' };
    }
  };

  const getTipoIcon = (tipo) => {
    switch (tipo) {
      case 'plenario': return Users;
      case 'comissao': return FileText;
      case 'votacao': return Vote;
      default: return Activity;
    }
  };

  if (loading) {
    return <LoadingSpinner message="A carregar agenda parlamentar" />;
  }

  const tabs = [
    { id: 'hoje', label: 'Hoje', icon: Calendar },
    { id: 'semana', label: 'Esta Semana', icon: Activity },
    { id: 'votacoes', label: 'Votações', icon: Vote }
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
            marginBottom: '0.5rem',
          }}
        >
          Agenda Parlamentar
        </h1>
        <p
          style={{
            fontFamily: tokens.fonts.body,
            fontSize: '1rem',
            color: tokens.colors.textSecondary,
            maxWidth: '40rem',
            margin: '0 auto',
          }}
        >
          Acompanhe as atividades diárias do Parlamento Português
        </p>
      </motion.div>

      {/* Estatísticas Rápidas */}
      {estatisticas && estatisticas.estatisticas && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '1rem',
          }}
        >
          {[
            { icon: Users, label: 'SESSÕES PLENÁRIAS', value: formatNumber(estatisticas.estatisticas.sessoes_plenarias?.total_ano), sublabel: 'este ano', color: tokens.colors.primary },
            { icon: Vote, label: 'VOTAÇÕES', value: formatNumber(estatisticas.estatisticas.votacoes?.total_ano), sublabel: estatisticas.estatisticas.votacoes?.taxa_aprovacao != null ? `${formatPercent(estatisticas.estatisticas.votacoes.taxa_aprovacao)} aprovadas` : 'em plenário', color: tokens.colors.primary },
            { icon: FileText, label: 'INICIATIVAS', value: formatNumber(estatisticas.estatisticas.iniciativas?.apresentadas), sublabel: 'apresentadas', color: '#7C3AED' },
            ...(estatisticas.estatisticas.assiduidade?.media_presencas != null ? [{ icon: Activity, label: 'ASSIDUIDADE', value: formatPercent(estatisticas.estatisticas.assiduidade.media_presencas), sublabel: 'média', color: '#D97706' }] : []),
          ].map((stat) => (
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
                  <p
                    style={{
                      fontFamily: tokens.fonts.body,
                      fontSize: '0.6875rem',
                      color: tokens.colors.textMuted,
                    }}
                  >
                    {stat.sublabel}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </motion.div>
      )}

      {/* Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        style={{
          backgroundColor: tokens.colors.bgSecondary,
          border: `1px solid ${tokens.colors.border}`,
          borderRadius: '4px',
          overflow: 'hidden',
        }}
      >
        {/* Tab Headers */}
        <div style={{ borderBottom: `1px solid ${tokens.colors.border}` }}>
          <nav style={{ display: 'flex', padding: '0 1.5rem' }}>
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '1rem 1.25rem',
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.875rem',
                    fontWeight: isActive ? 600 : 500,
                    color: isActive ? tokens.colors.primary : tokens.colors.textSecondary,
                    backgroundColor: 'transparent',
                    border: 'none',
                    borderBottom: isActive ? `2px solid ${tokens.colors.primary}` : '2px solid transparent',
                    cursor: 'pointer',
                    transition: 'all 150ms ease',
                    marginBottom: '-1px',
                  }}
                >
                  <Icon size={16} />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Tab Content */}
        <div style={{ padding: '1.5rem' }}>
          {activeTab === 'hoje' && !agendaHoje && <PainelIndisponivel titulo="Agenda de hoje indisponível" mensagem="A agenda do Parlamento ainda não está disponível nos dados abertos que usamos. Vai aparecer aqui quando for publicada." />}

          {activeTab === 'hoje' && agendaHoje && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                <h3
                  style={{
                    fontFamily: tokens.fonts.headline,
                    fontSize: '1.25rem',
                    fontWeight: 700,
                    color: tokens.colors.textPrimary,
                  }}
                >
                  Agenda de Hoje
                </h3>
                <span
                  style={{
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.8125rem',
                    color: tokens.colors.textMuted,
                  }}
                >
                  {new Date(agendaHoje.data).toLocaleDateString('pt-PT', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  })}
                </span>
              </div>

              {agendaHoje.eventos.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {(agendaHoje.eventos || []).map((evento) => {
                    const Icon = getTipoIcon(evento.tipo);
                    const estadoStyles = getEstadoStyles(evento.estado);
                    return (
                      <div
                        key={evento.id}
                        style={{
                          border: `1px solid ${tokens.colors.border}`,
                          borderRadius: '4px',
                          padding: '1rem',
                          transition: 'border-color 150ms ease',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.borderColor = tokens.colors.borderStrong}
                        onMouseLeave={(e) => e.currentTarget.style.borderColor = tokens.colors.border}
                      >
                        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', flex: 1 }}>
                            <Icon size={20} style={{ color: tokens.colors.primary, marginTop: '0.125rem' }} />
                            <div style={{ flex: 1 }}>
                              <h4
                                style={{
                                  fontFamily: tokens.fonts.body,
                                  fontSize: '1rem',
                                  fontWeight: 600,
                                  color: tokens.colors.textPrimary,
                                  marginBottom: '0.375rem',
                                }}
                              >
                                {evento.titulo}
                              </h4>
                              {evento.descricao && (
                                <p
                                  style={{
                                    fontFamily: tokens.fonts.body,
                                    fontSize: '0.875rem',
                                    color: tokens.colors.textSecondary,
                                    marginBottom: '0.75rem',
                                    whiteSpace: 'pre-line',
                                    lineHeight: 1.5,
                                    maxHeight: '4.5em',
                                    overflow: 'hidden',
                                    display: '-webkit-box',
                                    WebkitLineClamp: 3,
                                    WebkitBoxOrient: 'vertical',
                                  }}
                                >
                                  {evento.descricao}
                                </p>
                              )}
                              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                  <Clock size={14} style={{ color: tokens.colors.textMuted }} />
                                  <span
                                    style={{
                                      fontFamily: tokens.fonts.mono,
                                      fontSize: '0.75rem',
                                      color: tokens.colors.textSecondary,
                                    }}
                                  >
                                    {formatarHora(evento.hora_inicio)}
                                    {evento.hora_fim && ` – ${formatarHora(evento.hora_fim)}`}
                                  </span>
                                </div>
                                {evento.local && (
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                    <MapPin size={14} style={{ color: tokens.colors.textMuted }} />
                                    <span
                                      style={{
                                        fontFamily: tokens.fonts.body,
                                        fontSize: '0.75rem',
                                        color: tokens.colors.textSecondary,
                                      }}
                                    >
                                      {evento.local}
                                    </span>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                          <span
                            style={{
                              padding: '0.25rem 0.625rem',
                              fontFamily: tokens.fonts.body,
                              fontSize: '0.6875rem',
                              fontWeight: 600,
                              textTransform: 'uppercase',
                              letterSpacing: '0.03em',
                              borderRadius: '2px',
                              ...estadoStyles,
                            }}
                          >
                            {evento.estado === 'em_curso' && '● '}
                            {evento.estado.replace('_', ' ')}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '3rem 0' }}>
                  <Calendar size={40} style={{ color: tokens.colors.textMuted, marginBottom: '1rem' }} />
                  <p
                    style={{
                      fontFamily: tokens.fonts.body,
                      fontSize: '0.875rem',
                      color: tokens.colors.textMuted,
                    }}
                  >
                    Nenhuma atividade agendada para hoje
                  </p>
                </div>
              )}

              {/* Resumo do dia */}
              {agendaHoje.resumo && (
                <div
                  style={{
                    marginTop: '1.5rem',
                    padding: '1rem',
                    backgroundColor: '#F0F7F4',
                    borderRadius: '4px',
                    borderLeft: `3px solid ${tokens.colors.primary}`,
                  }}
                >
                  <h4
                    style={{
                      fontFamily: tokens.fonts.body,
                      fontSize: '0.8125rem',
                      fontWeight: 600,
                      color: tokens.colors.primary,
                      marginBottom: '0.5rem',
                      textTransform: 'uppercase',
                      letterSpacing: '0.03em',
                    }}
                  >
                    Resumo do Dia
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
                    <div>
                      <span
                        style={{
                          fontFamily: tokens.fonts.mono,
                          fontSize: '1.125rem',
                          fontWeight: 600,
                          color: tokens.colors.primary,
                        }}
                      >
                        {agendaHoje.resumo.sessoes_plenarias}
                      </span>
                      <span
                        style={{
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.8125rem',
                          color: tokens.colors.textSecondary,
                          marginLeft: '0.375rem',
                        }}
                      >
                        sessões plenárias
                      </span>
                    </div>
                    <div>
                      <span
                        style={{
                          fontFamily: tokens.fonts.mono,
                          fontSize: '1.125rem',
                          fontWeight: 600,
                          color: tokens.colors.primary,
                        }}
                      >
                        {agendaHoje.resumo.reunioes_comissao}
                      </span>
                      <span
                        style={{
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.8125rem',
                          color: tokens.colors.textSecondary,
                          marginLeft: '0.375rem',
                        }}
                      >
                        reuniões de comissão
                      </span>
                    </div>
                    <div>
                      <span
                        style={{
                          fontFamily: tokens.fonts.mono,
                          fontSize: '1.125rem',
                          fontWeight: 600,
                          color: tokens.colors.primary,
                        }}
                      >
                        {agendaHoje.resumo.outros_eventos}
                      </span>
                      <span
                        style={{
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.8125rem',
                          color: tokens.colors.textSecondary,
                          marginLeft: '0.375rem',
                        }}
                      >
                        outros eventos
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'semana' && !agendaSemana && <PainelIndisponivel titulo="Agenda da semana indisponível" mensagem="A agenda do Parlamento ainda não está disponível nos dados abertos que usamos. Vai aparecer aqui quando for publicada." />}

          {activeTab === 'semana' && agendaSemana && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                <h3
                  style={{
                    fontFamily: tokens.fonts.headline,
                    fontSize: '1.25rem',
                    fontWeight: 700,
                    color: tokens.colors.textPrimary,
                  }}
                >
                  Agenda da Semana
                </h3>
                <span
                  style={{
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.8125rem',
                    color: tokens.colors.textMuted,
                  }}
                >
                  {new Date(agendaSemana.periodo.inicio).toLocaleDateString('pt-PT')} – {new Date(agendaSemana.periodo.fim).toLocaleDateString('pt-PT')}
                </span>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                  gap: '1rem',
                }}
              >
                {(agendaSemana.agenda || []).map((dia) => (
                  <div
                    key={dia.data}
                    style={{
                      border: `1px solid ${tokens.colors.border}`,
                      borderRadius: '4px',
                      padding: '1rem',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                      <h4
                        style={{
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.9375rem',
                          fontWeight: 600,
                          color: tokens.colors.textPrimary,
                          textTransform: 'capitalize',
                        }}
                      >
                        {new Date(dia.data).toLocaleDateString('pt-PT', { weekday: 'long' })}
                      </h4>
                      <span
                        style={{
                          fontFamily: tokens.fonts.mono,
                          fontSize: '0.75rem',
                          color: tokens.colors.textMuted,
                        }}
                      >
                        {new Date(dia.data).toLocaleDateString('pt-PT', { day: 'numeric', month: 'short' })}
                      </span>
                    </div>

                    {dia.eventos.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {(dia.eventos || []).map((evento) => {
                          const estadoStyles = getEstadoStyles(evento.estado);
                          return (
                            <div
                              key={evento.id}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                padding: '0.5rem',
                                backgroundColor: '#FAFAFA',
                                borderRadius: '2px',
                              }}
                            >
                              <span
                                style={{
                                  fontFamily: tokens.fonts.body,
                                  fontSize: '0.8125rem',
                                  color: tokens.colors.textSecondary,
                                  flex: 1,
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                              >
                                {evento.titulo}
                              </span>
                              <span
                                style={{
                                  padding: '0.125rem 0.375rem',
                                  fontFamily: tokens.fonts.mono,
                                  fontSize: '0.6875rem',
                                  borderRadius: '2px',
                                  marginLeft: '0.5rem',
                                  ...estadoStyles,
                                }}
                              >
                                {evento.hora_inicio}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <p
                        style={{
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.8125rem',
                          fontStyle: 'italic',
                          color: tokens.colors.textMuted,
                        }}
                      >
                        Sem atividades
                      </p>
                    )}
                  </div>
                ))}
              </div>

              {/* Resumo da semana */}
              {agendaSemana.resumo && (
                <div
                  style={{
                    marginTop: '1.5rem',
                    padding: '1rem',
                    backgroundColor: '#F0F7F4',
                    borderRadius: '4px',
                    borderLeft: `3px solid ${tokens.colors.primary}`,
                  }}
                >
                  <h4
                    style={{
                      fontFamily: tokens.fonts.body,
                      fontSize: '0.8125rem',
                      fontWeight: 600,
                      color: tokens.colors.primary,
                      marginBottom: '0.5rem',
                      textTransform: 'uppercase',
                      letterSpacing: '0.03em',
                    }}
                  >
                    Resumo da Semana
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                    <div>
                      <span
                        style={{
                          fontFamily: tokens.fonts.mono,
                          fontSize: '1.125rem',
                          fontWeight: 600,
                          color: tokens.colors.primary,
                        }}
                      >
                        {agendaSemana.resumo.total_eventos}
                      </span>
                      <span
                        style={{
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.8125rem',
                          color: tokens.colors.textSecondary,
                          marginLeft: '0.375rem',
                        }}
                      >
                        eventos totais
                      </span>
                    </div>
                    <div>
                      <span
                        style={{
                          fontFamily: tokens.fonts.mono,
                          fontSize: '1.125rem',
                          fontWeight: 600,
                          color: tokens.colors.primary,
                        }}
                      >
                        {agendaSemana.resumo.dias_com_atividade}
                      </span>
                      <span
                        style={{
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.8125rem',
                          color: tokens.colors.textSecondary,
                          marginLeft: '0.375rem',
                        }}
                      >
                        dias com atividade
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'votacoes' && !votacoesRecentes && <PainelIndisponivel titulo="Votações indisponíveis" mensagem="Não foi possível carregar as votações recentes. Tente novamente mais tarde." />}

          {activeTab === 'votacoes' && votacoesRecentes && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                <h3
                  style={{
                    fontFamily: tokens.fonts.headline,
                    fontSize: '1.25rem',
                    fontWeight: 700,
                    color: tokens.colors.textPrimary,
                  }}
                >
                  Votações Recentes
                </h3>
                <span
                  style={{
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.8125rem',
                    color: tokens.colors.textMuted,
                  }}
                >
                  {votacoesRecentes.resumo.periodo}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {(votacoesRecentes.votacoes || []).map((votacao) => (
                  <div
                    key={votacao.id}
                    style={{
                      border: `1px solid ${tokens.colors.border}`,
                      borderRadius: '4px',
                      padding: '1rem',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                      <div style={{ flex: 1 }}>
                        <h4
                          style={{
                            fontFamily: tokens.fonts.body,
                            fontSize: '1rem',
                            fontWeight: 600,
                            color: tokens.colors.textPrimary,
                            marginBottom: '0.25rem',
                          }}
                        >
                          {votacao.titulo}
                        </h4>
                        {votacao.descricao && (
                          <p
                            style={{
                              fontFamily: tokens.fonts.body,
                              fontSize: '0.8125rem',
                              color: tokens.colors.textSecondary,
                              marginBottom: '0.375rem',
                              whiteSpace: 'pre-line',
                              lineHeight: 1.5,
                              maxHeight: '3em',
                              overflow: 'hidden',
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                            }}
                          >
                            {votacao.descricao}
                          </p>
                        )}
                        <span
                          style={{
                            fontFamily: tokens.fonts.mono,
                            fontSize: '0.6875rem',
                            color: tokens.colors.textMuted,
                          }}
                        >
                          {new Date(votacao.data).toLocaleDateString('pt-PT')}
                          {votacao.unanime && ' · unanimidade'}
                        </span>
                      </div>
                      <span
                        style={{
                          padding: '0.25rem 0.625rem',
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          borderRadius: '2px',
                          textTransform: 'uppercase',
                          color: votacao.resultado?.toLowerCase().startsWith('aprovad') ? tokens.colors.primary : tokens.colors.accent,
                          backgroundColor: votacao.resultado?.toLowerCase().startsWith('aprovad') ? '#F0F7F4' : '#FEF2F2',
                        }}
                      >
                        {votacao.resultado}
                      </span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', textAlign: 'center' }}>
                      <div>
                        <div
                          style={{
                            fontFamily: tokens.fonts.mono,
                            fontSize: '0.8125rem',
                            fontWeight: 600,
                            color: tokens.colors.primary,
                          }}
                        >
                          {votacao.favor.join(', ') || '-'}
                        </div>
                        <div
                          style={{
                            fontFamily: tokens.fonts.body,
                            fontSize: '0.6875rem',
                            color: tokens.colors.textMuted,
                            textTransform: 'uppercase',
                          }}
                        >
                          A favor
                        </div>
                      </div>
                      <div>
                        <div
                          style={{
                            fontFamily: tokens.fonts.mono,
                            fontSize: '0.8125rem',
                            fontWeight: 600,
                            color: tokens.colors.accent,
                          }}
                        >
                          {votacao.contra.join(', ') || '-'}
                        </div>
                        <div
                          style={{
                            fontFamily: tokens.fonts.body,
                            fontSize: '0.6875rem',
                            color: tokens.colors.textMuted,
                            textTransform: 'uppercase',
                          }}
                        >
                          Contra
                        </div>
                      </div>
                      <div>
                        <div
                          style={{
                            fontFamily: tokens.fonts.mono,
                            fontSize: '0.8125rem',
                            fontWeight: 600,
                            color: '#D97706',
                          }}
                        >
                          {votacao.abstencao.join(', ') || '-'}
                        </div>
                        <div
                          style={{
                            fontFamily: tokens.fonts.body,
                            fontSize: '0.6875rem',
                            color: tokens.colors.textMuted,
                            textTransform: 'uppercase',
                          }}
                        >
                          Abstenção
                        </div>
                      </div>
                      <div>
                        <div
                          style={{
                            fontFamily: tokens.fonts.mono,
                            fontSize: '0.8125rem',
                            fontWeight: 600,
                            color: tokens.colors.textMuted,
                          }}
                        >
                          {votacao.ausentes.join(', ') || '-'}
                        </div>
                        <div
                          style={{
                            fontFamily: tokens.fonts.body,
                            fontSize: '0.6875rem',
                            color: tokens.colors.textMuted,
                            textTransform: 'uppercase',
                          }}
                        >
                          Ausentes
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Resumo das votações */}
              {votacoesRecentes.resumo && (
                <div
                  style={{
                    marginTop: '1.5rem',
                    padding: '1rem',
                    backgroundColor: '#F5F3FF',
                    borderRadius: '4px',
                    borderLeft: '3px solid #7C3AED',
                  }}
                >
                  <h4
                    style={{
                      fontFamily: tokens.fonts.body,
                      fontSize: '0.8125rem',
                      fontWeight: 600,
                      color: '#7C3AED',
                      marginBottom: '0.5rem',
                      textTransform: 'uppercase',
                      letterSpacing: '0.03em',
                    }}
                  >
                    Resumo das Votações
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                    <div>
                      <span
                        style={{
                          fontFamily: tokens.fonts.mono,
                          fontSize: '1.125rem',
                          fontWeight: 600,
                          color: tokens.colors.primary,
                        }}
                      >
                        {votacoesRecentes.resumo.aprovadas}
                      </span>
                      <span
                        style={{
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.8125rem',
                          color: tokens.colors.textSecondary,
                          marginLeft: '0.375rem',
                        }}
                      >
                        aprovadas
                      </span>
                    </div>
                    <div>
                      <span
                        style={{
                          fontFamily: tokens.fonts.mono,
                          fontSize: '1.125rem',
                          fontWeight: 600,
                          color: tokens.colors.accent,
                        }}
                      >
                        {votacoesRecentes.resumo.rejeitadas}
                      </span>
                      <span
                        style={{
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.8125rem',
                          color: tokens.colors.textSecondary,
                          marginLeft: '0.375rem',
                        }}
                      >
                        rejeitadas
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default AgendaPage;
