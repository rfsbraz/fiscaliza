import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, Users, Building, Calendar, TrendingUp, Handshake, History, MapPin, Award, Target, Activity } from 'lucide-react';
import { motion } from 'framer-motion';
import { apiFetch } from '../config/api';
import { tokens } from '../styles/tokens';
import { LoadingSpinner } from './common';

// Coalition colors based on political spectrum
const spectrumColors = {
  'esquerda': '#DC2626',
  'centro-esquerda': '#F59E0B',
  'centro': '#6B7280',
  'centro-direita': '#3B82F6',
  'direita': '#1E40AF'
};

const ColigacaoDetalhes = () => {
  const { coligacaoId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [dados, setDados] = useState(null);
  const [deputados, setDeputados] = useState([]);
  const [partidos, setPartidos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Get active tab from URL hash
  const getActiveTabFromUrl = () => {
    const hash = location.hash.replace('#', '');
    const validTabs = ['overview', 'deputados', 'partidos', 'timeline', 'performance'];
    return validTabs.includes(hash) ? hash : 'overview';
  };

  const [activeTab, setActiveTab] = useState(getActiveTabFromUrl());

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

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    navigate(`#${tabId}`, { replace: true });
  };

  useEffect(() => {
    if (!location.hash) {
      navigate('#overview', { replace: true });
    }
  }, [navigate, location.hash]);

  useEffect(() => {
    const fetchDados = async () => {
      try {
        setLoading(true);

        // Fetch coalition details
        const coligacaoResponse = await apiFetch(`coligacoes/${encodeURIComponent(coligacaoId)}`);
        if (!coligacaoResponse.ok) {
          throw new Error('Erro ao carregar dados da coligação');
        }
        const coligacaoData = await coligacaoResponse.json();
        setDados(coligacaoData);

        // Fetch coalition deputies
        const deputadosResponse = await apiFetch(`coligacoes/${encodeURIComponent(coligacaoId)}/deputados`);
        if (deputadosResponse.ok) {
          const deputadosData = await deputadosResponse.json();
          setDeputados(deputadosData.deputados || []);
        }

        // Fetch component parties
        const partidosResponse = await apiFetch(`coligacoes/${encodeURIComponent(coligacaoId)}/partidos`);
        if (partidosResponse.ok) {
          const partidosData = await partidosResponse.json();
          setPartidos(partidosData.partidos || []);
        }

      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (coligacaoId) {
      fetchDados();
    }
  }, [coligacaoId]);

  if (loading) {
    return <LoadingSpinner message="A carregar dados da coligação" />;
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
          <p style={{ fontFamily: tokens.fonts.body, color: tokens.colors.accent, marginBottom: '1rem' }}>
            Erro: {error}
          </p>
          <Link
            to="/partidos"
            style={{ fontFamily: tokens.fonts.body, color: tokens.colors.primary, textDecoration: 'underline' }}
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
          Coligação não encontrada
        </p>
      </div>
    );
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-PT', { year: 'numeric', month: 'long', day: 'numeric' });
  };

  // Coalition timeline data
  const timelineEvents = [
    dados.data_formacao && {
      date: dados.data_formacao,
      title: 'Formação da Coligação',
      description: `Criação da ${dados.nome}`,
      type: 'formation'
    },
    dados.data_dissolucao && {
      date: dados.data_dissolucao,
      title: 'Dissolução',
      description: 'Fim da coligação',
      type: 'dissolution'
    }
  ].filter(Boolean);

  const tabs = [
    { id: 'overview', label: 'Visão Geral', icon: Target },
    { id: 'partidos', label: 'Partidos Componentes', icon: Building },
    { id: 'deputados', label: `Deputados (${deputados.length})`, icon: Users },
    { id: 'timeline', label: 'Linha do Tempo', icon: History },
    { id: 'performance', label: 'Desempenho Eleitoral', icon: Activity },
  ];

  return (
    <div style={{ minHeight: '100vh', backgroundColor: tokens.colors.bgPrimary }}>
      {/* Header */}
      <div
        style={{
          backgroundColor: tokens.colors.bgSecondary,
          borderBottom: `1px solid ${tokens.colors.border}`,
        }}
      >
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '1rem 1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
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
              onMouseEnter={(e) => e.currentTarget.style.color = tokens.colors.textPrimary}
              onMouseLeave={(e) => e.currentTarget.style.color = tokens.colors.textSecondary}
            >
              <ArrowLeft style={{ width: '20px', height: '20px', marginRight: '0.5rem' }} />
              Voltar aos Partidos
            </Link>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Handshake style={{ width: '20px', height: '20px', color: tokens.colors.primary }} />
              <span style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', fontWeight: 600, color: tokens.colors.textSecondary }}>
                Coligação
              </span>
            </div>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '2rem 1.5rem' }}>
        {/* Coalition Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            backgroundColor: tokens.colors.bgSecondary,
            border: `1px solid ${tokens.colors.border}`,
            borderRadius: '4px',
            marginBottom: '2rem',
          }}
        >
          <div style={{ padding: '1.5rem 2rem' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                  <h1
                    style={{
                      fontFamily: tokens.fonts.headline,
                      fontSize: '2rem',
                      fontWeight: 700,
                      color: tokens.colors.textPrimary,
                      margin: 0,
                    }}
                  >
                    {dados.sigla}
                  </h1>
                  <span
                    style={{
                      padding: '0.25rem 0.75rem',
                      borderRadius: '2px',
                      fontSize: '0.75rem',
                      fontFamily: tokens.fonts.body,
                      fontWeight: 600,
                      color: '#FFFFFF',
                      backgroundColor: spectrumColors[dados.espectro_politico] || '#6B7280',
                    }}
                  >
                    {dados.espectro_politico || 'N/A'}
                  </span>
                  {dados.ativa && (
                    <span
                      style={{
                        padding: '0.25rem 0.75rem',
                        borderRadius: '2px',
                        fontSize: '0.75rem',
                        fontFamily: tokens.fonts.body,
                        fontWeight: 600,
                        backgroundColor: '#E8F5E9',
                        color: tokens.colors.primary,
                      }}
                    >
                      Ativa
                    </span>
                  )}
                </div>
                <p
                  style={{
                    fontFamily: tokens.fonts.body,
                    fontSize: '1.125rem',
                    color: tokens.colors.textSecondary,
                    marginBottom: '1rem',
                  }}
                >
                  {dados.nome}
                </p>

                {/* Key Information */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginTop: '1.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', color: tokens.colors.textSecondary }}>
                    <Calendar style={{ width: '20px', height: '20px', marginRight: '0.5rem', color: tokens.colors.textMuted }} />
                    <div>
                      <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.75rem', color: tokens.colors.textMuted }}>Formação</p>
                      <p style={{ fontFamily: tokens.fonts.body, fontWeight: 600 }}>{formatDate(dados.data_formacao)}</p>
                    </div>
                  </div>

                  {dados.data_dissolucao && (
                    <div style={{ display: 'flex', alignItems: 'center', color: tokens.colors.textSecondary }}>
                      <Calendar style={{ width: '20px', height: '20px', marginRight: '0.5rem', color: tokens.colors.textMuted }} />
                      <div>
                        <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.75rem', color: tokens.colors.textMuted }}>Dissolução</p>
                        <p style={{ fontFamily: tokens.fonts.body, fontWeight: 600 }}>{formatDate(dados.data_dissolucao)}</p>
                      </div>
                    </div>
                  )}

                  <div style={{ display: 'flex', alignItems: 'center', color: tokens.colors.textSecondary }}>
                    <Building style={{ width: '20px', height: '20px', marginRight: '0.5rem', color: tokens.colors.textMuted }} />
                    <div>
                      <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.75rem', color: tokens.colors.textMuted }}>Tipo</p>
                      <p style={{ fontFamily: tokens.fonts.body, fontWeight: 600, textTransform: 'capitalize' }}>{dados.tipo_coligacao || 'Eleitoral'}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ textAlign: 'right', marginLeft: '1.5rem' }}>
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
                    {dados.deputy_count || deputados.length}
                  </span>
                  <span style={{ fontFamily: tokens.fonts.body, marginLeft: '0.25rem' }}>deputados</span>
                </div>
                <div style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', color: tokens.colors.textMuted }}>
                  {partidos.length} partidos componentes
                </div>
              </div>
            </div>

            {/* Observations */}
            {dados.observacoes && (
              <div
                style={{
                  marginTop: '1.5rem',
                  padding: '1rem',
                  backgroundColor: tokens.colors.bgPrimary,
                  borderRadius: '4px',
                  border: `1px solid ${tokens.colors.border}`,
                }}
              >
                <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', color: tokens.colors.textSecondary }}>
                  {dados.observacoes}
                </p>
              </div>
            )}
          </div>
        </motion.div>

        {/* Tabs */}
        <div
          style={{
            backgroundColor: tokens.colors.bgSecondary,
            border: `1px solid ${tokens.colors.border}`,
            borderRadius: '4px',
            marginBottom: '2rem',
          }}
        >
          <div style={{ borderBottom: `1px solid ${tokens.colors.border}` }}>
            <nav style={{ display: 'flex', overflowX: 'auto' }}>
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => handleTabChange(tab.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '1rem 1.5rem',
                      fontFamily: tokens.fonts.body,
                      fontSize: '0.875rem',
                      fontWeight: isActive ? 600 : 500,
                      color: isActive ? tokens.colors.primary : tokens.colors.textMuted,
                      background: 'none',
                      border: 'none',
                      borderBottom: isActive ? `2px solid ${tokens.colors.primary}` : '2px solid transparent',
                      cursor: 'pointer',
                      transition: 'all 150ms ease',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    <Icon style={{ width: '16px', height: '16px', marginRight: '0.5rem' }} />
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          </div>

          <div style={{ padding: '1.5rem' }}>
            {/* Overview Tab */}
            {activeTab === 'overview' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                {/* Historical Context */}
                <div
                  style={{
                    backgroundColor: tokens.colors.bgSecondary,
                    border: `1px solid ${tokens.colors.border}`,
                    borderRadius: '4px',
                  }}
                >
                  <div style={{ padding: '1rem 1.25rem', borderBottom: `1px solid ${tokens.colors.border}` }}>
                    <h3 style={{ fontFamily: tokens.fonts.body, fontSize: '1rem', fontWeight: 600, color: tokens.colors.textPrimary, margin: 0 }}>
                      Contexto Histórico
                    </h3>
                  </div>
                  <div style={{ padding: '1.25rem' }}>
                    <div style={{ fontFamily: tokens.fonts.body, fontSize: '0.9375rem', color: tokens.colors.textSecondary, lineHeight: 1.7 }}>
                      {dados.sigla === 'AD' && (
                        <>
                          <p>A Aliança Democrática foi uma coligação política de centro-direita formada em 1979,
                          unindo o PSD (então PPD/PSD), o CDS e o PPM. Foi a primeira coligação governamental estável
                          após o 25 de Abril, marcando a consolidação democrática portuguesa.</p>
                          <p style={{ marginTop: '0.75rem' }}>Sob a liderança de Francisco Sá Carneiro, a AD venceu as eleições de 1979 e 1980,
                          estabelecendo um modelo de governação de centro-direita que seria referência para futuras coligações.</p>
                        </>
                      )}
                      {dados.sigla === 'CDU' && (
                        <>
                          <p>A Coligação Democrática Unitária representa a mais duradoura aliança política
                          na democracia portuguesa, unindo desde 1987 o Partido Comunista Português e o
                          Partido Ecologista "Os Verdes".</p>
                          <p style={{ marginTop: '0.75rem' }}>Com forte implantação no Alentejo e cintura industrial de Lisboa,
                          a CDU mantém uma linha política consistente de esquerda, defendendo os direitos
                          dos trabalhadores e uma visão crítica da integração europeia.</p>
                        </>
                      )}
                      {dados.sigla === 'PAF' && (
                        <>
                          <p>Portugal à Frente foi a designação adotada pela coligação PSD/CDS-PP para
                          as eleições legislativas de 2015, representando uma renovação da tradicional
                          aliança de centro-direita.</p>
                          <p style={{ marginTop: '0.75rem' }}>Apesar de ter obtido a maioria relativa, a PàF não conseguiu
                          formar governo, marcando uma mudança significativa no panorama político português
                          com a formação da "geringonça" à esquerda.</p>
                        </>
                      )}
                      {!['AD', 'CDU', 'PAF'].includes(dados.sigla) && (
                        <p>Coligação política portuguesa formada para maximizar a representação eleitoral
                        dos partidos componentes através de uma estratégia unificada.</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Key Achievements */}
                <div
                  style={{
                    backgroundColor: tokens.colors.bgSecondary,
                    border: `1px solid ${tokens.colors.border}`,
                    borderRadius: '4px',
                  }}
                >
                  <div style={{ padding: '1rem 1.25rem', borderBottom: `1px solid ${tokens.colors.border}` }}>
                    <h3 style={{ fontFamily: tokens.fonts.body, fontSize: '1rem', fontWeight: 600, color: tokens.colors.textPrimary, margin: 0 }}>
                      Momentos Chave
                    </h3>
                  </div>
                  <div style={{ padding: '1.25rem' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      {dados.sigla === 'AD' && (
                        <>
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                            <Award style={{ width: '20px', height: '20px', color: tokens.colors.primary, flexShrink: 0, marginTop: '0.125rem' }} />
                            <div>
                              <p style={{ fontFamily: tokens.fonts.body, fontWeight: 600, color: tokens.colors.textPrimary }}>Vitória Eleitoral 1979</p>
                              <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', color: tokens.colors.textSecondary }}>42.5% dos votos, primeiro governo de coligação estável</p>
                            </div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                            <Award style={{ width: '20px', height: '20px', color: tokens.colors.primary, flexShrink: 0, marginTop: '0.125rem' }} />
                            <div>
                              <p style={{ fontFamily: tokens.fonts.body, fontWeight: 600, color: tokens.colors.textPrimary }}>Maioria Absoluta 1980</p>
                              <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', color: tokens.colors.textSecondary }}>44.9% dos votos, consolidação do projeto político</p>
                            </div>
                          </div>
                        </>
                      )}
                      {dados.sigla === 'CDU' && (
                        <>
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                            <Award style={{ width: '20px', height: '20px', color: tokens.colors.primary, flexShrink: 0, marginTop: '0.125rem' }} />
                            <div>
                              <p style={{ fontFamily: tokens.fonts.body, fontWeight: 600, color: tokens.colors.textPrimary }}>Consistência Eleitoral</p>
                              <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', color: tokens.colors.textSecondary }}>Presença parlamentar ininterrupta desde 1987</p>
                            </div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                            <Award style={{ width: '20px', height: '20px', color: tokens.colors.primary, flexShrink: 0, marginTop: '0.125rem' }} />
                            <div>
                              <p style={{ fontFamily: tokens.fonts.body, fontWeight: 600, color: tokens.colors.textPrimary }}>Força Regional</p>
                              <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', color: tokens.colors.textSecondary }}>Liderança consistente no Alentejo</p>
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Component Parties Tab */}
            {activeTab === 'partidos' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {partidos.map((partido, index) => (
                  <motion.div
                    key={partido.sigla}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    style={{
                      backgroundColor: tokens.colors.bgPrimary,
                      borderRadius: '4px',
                      padding: '1rem',
                      border: `1px solid ${tokens.colors.border}`,
                      transition: 'background-color 150ms ease',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#F0F0F0'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = tokens.colors.bgPrimary}
                  >
                    <Link
                      to={`/partidos/${partido.sigla}`}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        textDecoration: 'none',
                      }}
                    >
                      <div>
                        <h3
                          style={{
                            fontFamily: tokens.fonts.body,
                            fontSize: '1.125rem',
                            fontWeight: 600,
                            color: tokens.colors.textPrimary,
                            margin: 0,
                          }}
                        >
                          {partido.sigla}
                        </h3>
                        <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', color: tokens.colors.textSecondary }}>
                          {partido.nome}
                        </p>
                        {partido.papel_coligacao && (
                          <span
                            style={{
                              display: 'inline-block',
                              marginTop: '0.5rem',
                              padding: '0.25rem 0.5rem',
                              backgroundColor: '#E8F5E9',
                              color: tokens.colors.primary,
                              fontSize: '0.75rem',
                              fontFamily: tokens.fonts.body,
                              borderRadius: '2px',
                            }}
                          >
                            {partido.papel_coligacao}
                          </span>
                        )}
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        {partido.data_adesao && (
                          <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', color: tokens.colors.textMuted }}>
                            Desde {new Date(partido.data_adesao).getFullYear()}
                          </p>
                        )}
                      </div>
                    </Link>
                  </motion.div>
                ))}
              </div>
            )}

            {/* Deputies Tab */}
            {activeTab === 'deputados' && (
              <div>
                {deputados.length === 0 ? (
                  <p style={{ fontFamily: tokens.fonts.body, color: tokens.colors.textMuted, textAlign: 'center', padding: '2rem 0' }}>
                    Nenhum deputado encontrado para esta coligação
                  </p>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                    {deputados.map((deputado, index) => (
                      <motion.div
                        key={deputado.id}
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: index * 0.05 }}
                        style={{
                          backgroundColor: tokens.colors.bgSecondary,
                          border: `1px solid ${tokens.colors.border}`,
                          borderRadius: '4px',
                          padding: '1rem',
                          transition: 'border-color 150ms ease',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.borderColor = tokens.colors.primary}
                        onMouseLeave={(e) => e.currentTarget.style.borderColor = tokens.colors.border}
                      >
                        <Link
                          to={`/deputados/${deputado.id_cadastro || deputado.id}`}
                          style={{ textDecoration: 'none' }}
                        >
                          <h4
                            style={{
                              fontFamily: tokens.fonts.body,
                              fontWeight: 600,
                              color: tokens.colors.textPrimary,
                              margin: 0,
                              transition: 'color 150ms ease',
                            }}
                            onMouseEnter={(e) => e.target.style.color = tokens.colors.primary}
                            onMouseLeave={(e) => e.target.style.color = tokens.colors.textPrimary}
                          >
                            {deputado.nome}
                          </h4>
                          <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', color: tokens.colors.textSecondary, marginTop: '0.25rem' }}>
                            {deputado.partido_sigla}
                          </p>
                          <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.75rem', color: tokens.colors.textMuted, marginTop: '0.5rem' }}>
                            {deputado.circulo}
                          </p>
                        </Link>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Timeline Tab */}
            {activeTab === 'timeline' && (
              <div style={{ position: 'relative' }}>
                <div
                  style={{
                    position: 'absolute',
                    left: '32px',
                    top: 0,
                    bottom: 0,
                    width: '2px',
                    backgroundColor: tokens.colors.border,
                  }}
                />
                {timelineEvents.map((event, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.2 }}
                    style={{
                      position: 'relative',
                      display: 'flex',
                      alignItems: 'flex-start',
                      marginBottom: '2rem',
                    }}
                  >
                    <div
                      style={{
                        zIndex: 10,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '64px',
                        height: '64px',
                        borderRadius: '50%',
                        backgroundColor: event.type === 'formation' ? '#E8F5E9' : '#FFEBEE',
                        flexShrink: 0,
                      }}
                    >
                      <Calendar
                        style={{
                          width: '24px',
                          height: '24px',
                          color: event.type === 'formation' ? tokens.colors.primary : tokens.colors.accent,
                        }}
                      />
                    </div>
                    <div style={{ marginLeft: '1.5rem' }}>
                      <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', color: tokens.colors.textMuted }}>
                        {formatDate(event.date)}
                      </p>
                      <h3
                        style={{
                          fontFamily: tokens.fonts.body,
                          fontSize: '1.125rem',
                          fontWeight: 600,
                          color: tokens.colors.textPrimary,
                          marginTop: '0.25rem',
                        }}
                      >
                        {event.title}
                      </h3>
                      <p style={{ fontFamily: tokens.fonts.body, color: tokens.colors.textSecondary, marginTop: '0.25rem' }}>
                        {event.description}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}

            {/* Performance Tab */}
            {activeTab === 'performance' && (
              <div
                style={{
                  backgroundColor: tokens.colors.bgSecondary,
                  border: `1px solid ${tokens.colors.border}`,
                  borderRadius: '4px',
                }}
              >
                <div style={{ padding: '1rem 1.25rem', borderBottom: `1px solid ${tokens.colors.border}` }}>
                  <h3 style={{ fontFamily: tokens.fonts.body, fontSize: '1rem', fontWeight: 600, color: tokens.colors.textPrimary, margin: 0 }}>
                    Desempenho Eleitoral
                  </h3>
                  <p style={{ fontFamily: tokens.fonts.body, fontSize: '0.875rem', color: tokens.colors.textMuted, marginTop: '0.25rem' }}>
                    Evolução dos resultados eleitorais da coligação
                  </p>
                </div>
                <div style={{ padding: '2rem 1.25rem' }}>
                  <p style={{ fontFamily: tokens.fonts.body, color: tokens.colors.textMuted, textAlign: 'center' }}>
                    Dados de desempenho eleitoral em desenvolvimento
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ColigacaoDetalhes;
