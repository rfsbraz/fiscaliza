import React, { useState, useEffect } from 'react';
import { Calendar, TrendingUp, Users, Target, Scale, PieChart, Activity, Shield, BookOpen } from 'lucide-react';
import { apiFetch } from '../config/api';
import { tokens } from '../styles/tokens';
import { formatDecimal } from '../utils/format';

const ABSENCE_NOTE =
  'O registo das votações só indica ausências quando as nomeia, por isso a maioria das faltas não aparece aqui. ' +
  'A presença em plenário está no separador de presenças.';

const VotingAnalytics = ({ deputadoId, legislatura }) => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeChart, setActiveChart] = useState('overview');

  useEffect(() => {
    const fetchVotingAnalytics = async () => {
      try {
        setLoading(true);
        const response = await apiFetch(
          `deputados/${deputadoId}/voting-analytics?legislatura=${encodeURIComponent(legislatura || '')}`
        );
        if (!response.ok) {
          throw new Error('Erro ao carregar análises de votação');
        }
        const data = await response.json();
        setAnalytics(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (deputadoId) {
      fetchVotingAnalytics();
    }
  }, [deputadoId, legislatura]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">A carregar análises de votação...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">Erro: {error}</div>
        <p className="text-gray-500">Não foi possível carregar as análises de votação</p>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Dados de votação não disponíveis</p>
      </div>
    );
  }

  const charts = [
    { id: 'overview', label: 'Visão Geral', icon: Activity },
    { id: 'collaboration', label: 'Alinhamento com Outros Grupos', icon: Users },
    { id: 'dissent', label: 'Votos Diferentes do Grupo', icon: Target },
    { id: 'close', label: 'Votações Renhidas', icon: Scale }
  ];

  // Alignment with the deputy's own group, by month
  const PartyDisciplineChart = () => {
    const { party_discipline } = analytics || {};

    if (!party_discipline || !party_discipline.monthly || party_discipline.overall_alignment == null) {
      return (
        <div className="text-center py-8 text-gray-500">
          <Shield className="h-12 w-12 text-gray-400 mx-auto mb-3" />
          <p>Sem votações com sentido de voto conhecido do deputado e do grupo</p>
        </div>
      );
    }

    const alignment = formatDecimal(party_discipline.overall_alignment * 100, 1);

    return (
      <div className="space-y-6">
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-lg font-semibold text-gray-900 flex items-center">
              <Shield className="h-5 w-5 text-blue-600 mr-2" />
              Alinhamento com o Grupo Parlamentar
            </h4>
            <div className="text-right">
              <div className="text-2xl font-bold text-blue-600">{alignment}%</div>
              <div className="text-sm text-gray-600">
                {party_discipline.aligned_votes} de {party_discipline.total_votes} votações
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
            {party_discipline.monthly.map((month) => (
              <div key={month.month} className="relative">
                <div className="text-xs text-gray-600 mb-1">{month.month}</div>
                <div
                  className="h-8 rounded flex items-center justify-center text-xs font-medium bg-blue-100 text-blue-900"
                  title={`${month.month}: ${month.aligned_votes}/${month.total_votes} votações com o mesmo sentido do grupo`}
                >
                  {month.aligned_votes}/{month.total_votes}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 text-sm text-gray-600">
            Conta as votações em que o deputado e o seu grupo votaram (a favor, contra ou abstenção).
            Ausências não contam.
          </div>
        </div>
      </div>
    );
  };

  // Voting Pattern Distribution Chart
  const VoteDistributionChart = () => {
    const { vote_distribution } = analytics || {};
    
    // Check if vote_distribution data exists
    if (!vote_distribution) {
      return (
        <div className="text-center py-8 text-gray-500">
          <PieChart className="h-12 w-12 text-gray-400 mx-auto mb-3" />
          <p>Dados de distribuição de votos não disponíveis</p>
        </div>
      );
    }
    
    const total = Object.values(vote_distribution).reduce((sum, count) => sum + count, 0);
    
    const voteTypes = [
      { key: 'favor', label: 'A Favor', color: 'bg-green-500', textColor: 'text-green-800' },
      { key: 'contra', label: 'Contra', color: 'bg-red-500', textColor: 'text-red-800' },
      { key: 'abstencao', label: 'Abstenção', color: 'bg-yellow-500', textColor: 'text-yellow-800' },
      { key: 'ausente', label: 'Ausência registada', color: 'bg-gray-400', textColor: 'text-gray-800' }
    ];

    return (
      <div className="space-y-6">
        
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {voteTypes.map(type => {
            const count = vote_distribution[type.key] || 0;
            const percentage = formatDecimal(total > 0 ? (count / total) * 100 : 0, 1);
            
            return (
              <div key={type.key} className="bg-white border rounded-lg p-4 text-center">
                <div className={`w-12 h-12 ${type.color} rounded-full mx-auto mb-3 flex items-center justify-center`}>
                  <span className="text-white font-bold text-lg">{percentage}%</span>
                </div>
                <div className="text-sm font-medium text-gray-900">{type.label}</div>
                <div className="text-2xl font-bold text-gray-700">{count}</div>
                <div className="text-xs text-gray-500">votações</div>
              </div>
            );
          })}
        </div>
        
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm font-medium text-gray-700 mb-2">Total: {total} votações</div>
          <div className="flex rounded-lg overflow-hidden h-4">
            {voteTypes.map(type => {
              const count = vote_distribution[type.key] || 0;
              const width = total > 0 ? (count / total * 100) : 0;
              return (
                <div
                  key={type.key}
                  className={type.color}
                  style={{ width: `${width}%` }}
                  title={`${type.label}: ${count} (${formatDecimal(width, 1)}%)`}
                />
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  // Participation Timeline Chart
  const ParticipationTimelineChart = () => {
    const { participation_timeline } = analytics || {};
    
    // Check if participation_timeline data exists
    if (!participation_timeline || participation_timeline.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500">
          <Calendar className="h-12 w-12 text-gray-400 mx-auto mb-3" />
          <p>Dados de linha do tempo não disponíveis</p>
        </div>
      );
    }
    
    return (
      <div className="space-y-6">
        
        <div className="space-y-3">
          {participation_timeline.slice(-10).map((day, index) => (
            <div key={day.date} className="bg-white border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-medium text-gray-900">
                  {new Date(day.date).toLocaleDateString('pt-PT', { 
                    weekday: 'short', 
                    year: 'numeric', 
                    month: 'short', 
                    day: 'numeric' 
                  })}
                </div>
                <div className="text-sm text-gray-600">
                  {day.participated}/{day.total_votes} votações ({formatDecimal(day.participation_rate * 100, 0)}%)
                </div>
              </div>
              
              <div className="flex items-center space-x-4 text-xs">
                <div className="flex items-center">
                  <div className="w-3 h-3 bg-green-500 rounded mr-1"></div>
                  <span>A Favor: {day.favor_votes}</span>
                </div>
                <div className="flex items-center">
                  <div className="w-3 h-3 bg-red-500 rounded mr-1"></div>
                  <span>Contra: {day.contra_votes}</span>
                </div>
                <div className="flex items-center">
                  <div className="w-3 h-3 bg-yellow-500 rounded mr-1"></div>
                  <span>Abstenção: {day.abstention_votes}</span>
                </div>
              </div>
              
              <div className="mt-2 bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${day.participation_rate * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Cross-Party Collaboration Chart
  const CollaborationChart = () => {
    const { cross_party_collaboration } = analytics || {};
    
    if (!cross_party_collaboration || !cross_party_collaboration.length) {
      return (
        <div className="text-center py-8">
          <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Dados de alinhamento com outros grupos não disponíveis</p>
        </div>
      );
    }
    
    return (
      <div className="space-y-6">
        <h4 className="text-lg font-semibold text-gray-900 flex items-center">
          <Users className="h-5 w-5 text-indigo-600 mr-2" />
          Alinhamento com Outros Grupos
        </h4>
        <p className="text-sm text-gray-600">
          Votações em que o deputado e o grupo votaram, e em quantas o sentido foi o mesmo.
        </p>
        
        <div className="space-y-3">
          {cross_party_collaboration.map((party, index) => (
            <div key={party.party} className="bg-white border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-medium text-gray-900">{party.party}</div>
                <div className="text-sm text-gray-600">
                  {formatDecimal(party.alignment_rate * 100, 1)}% alinhamento
                </div>
              </div>
              
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs text-gray-500">
                  {party.aligned_votes}/{party.total_votes} votações com o mesmo sentido
                </div>
              </div>
              
              <div className="bg-gray-200 rounded-full h-2">
                <div
                  className="h-2 rounded-full transition-all duration-300 bg-blue-500"
                  style={{ width: `${party.alignment_rate * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const voteLabels = {
    favor: 'A Favor',
    contra: 'Contra',
    abstencao: 'Abstenção',
    ausente: 'Ausência registada'
  };

  const voteColors = {
    favor: 'text-green-600',
    contra: 'text-red-600',
    abstencao: 'text-yellow-600',
    ausente: 'text-gray-500'
  };

  const resultLabels = {
    aprovada: 'Aprovada',
    rejeitada: 'Rejeitada',
    prejudicada: 'Prejudicada',
    retirada: 'Retirada'
  };

  // One vote in the dissent or close lists
  const VoteItem = ({ vote, close }) => (
    <div className="bg-white border rounded-lg p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="text-sm font-medium text-gray-900 line-clamp-3 leading-relaxed mb-2">
            {vote.objeto}
          </div>
          <div className="flex items-center gap-3 flex-wrap text-xs text-gray-500">
            <span>{vote.data ? new Date(vote.data).toLocaleDateString('pt-PT') : 'Data não disponível'}</span>
            {close && (
              <span className="bg-gray-100 px-2 py-1 rounded">
                {vote.votos_favor} a favor, {vote.votos_contra} contra, {vote.abstencoes} abstenções (estimativa)
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`text-sm font-medium ${voteColors[vote.voto] || 'text-gray-600'}`}>
            {voteLabels[vote.voto] || vote.voto}
          </span>
          {vote.voto_grupo && (
            <span className="text-xs text-gray-500">Grupo: {voteLabels[vote.voto_grupo] || vote.voto_grupo}</span>
          )}
          <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-800">
            {resultLabels[vote.resultado] || vote.resultado}
          </span>
        </div>
      </div>

      {vote.vote_breakdown && Object.keys(vote.vote_breakdown).length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <div className="text-xs text-gray-600 mb-2">Sentido de voto dos grupos:</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-1 text-xs">
            {Object.entries(vote.vote_breakdown).map(([party, position]) => (
              <div key={party} className="flex items-center justify-between bg-gray-50 px-2 py-1 rounded">
                <span className="font-medium">{party}</span>
                <span className={voteColors[position] || 'text-gray-500'}>{voteLabels[position] || position}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  // Votes where the deputy is named voting differently from their group
  const DissentVotesChart = () => {
    const { dissent_votes } = analytics || {};

    return (
      <div className="space-y-6">
        <div>
          <h4 className="text-lg font-semibold text-gray-900 flex items-center mb-2">
            <Target className="h-5 w-5 text-gray-600 mr-2" />
            Votos Diferentes do Grupo
          </h4>
          <p className="text-sm text-gray-600">
            Votações em plenário em que o registo da votação nomeia o deputado com um sentido de voto
            diferente do seu grupo parlamentar. Mais recentes primeiro.
          </p>
        </div>
        {!dissent_votes || dissent_votes.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>Nenhuma votação nesta legislatura</p>
          </div>
        ) : (
          <div className="space-y-3">
            {dissent_votes.slice(0, 15).map((vote) => (
              <VoteItem key={vote.vote_id} vote={vote} />
            ))}
            {dissent_votes.length > 15 && (
              <p className="text-xs text-gray-500">A mostrar 15 de {dissent_votes.length} votações.</p>
            )}
          </div>
        )}
      </div>
    );
  };

  // Recent plenary votes decided by a small margin
  const CloseVotesChart = () => {
    const { close_votes, data_sources } = analytics || {};
    const margin = data_sources?.close_margin ?? 10;

    return (
      <div className="space-y-6">
        <div>
          <h4 className="text-lg font-semibold text-gray-900 flex items-center mb-2">
            <Scale className="h-5 w-5 text-gray-600 mr-2" />
            Votações Renhidas
          </h4>
          <p className="text-sm text-gray-600">
            Votações em plenário decididas por {margin} votos ou menos, estimados a partir do sentido de voto
            de cada grupo e dos deputados que tinham lugar nesse dia. Mais recentes primeiro.
          </p>
        </div>
        {!close_votes || close_votes.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>Nenhuma votação nesta legislatura</p>
          </div>
        ) : (
          <div className="space-y-3">
            {close_votes.slice(0, 15).map((vote) => (
              <VoteItem key={vote.vote_id} vote={vote} close />
            ))}
            {close_votes.length > 15 && (
              <p className="text-xs text-gray-500">A mostrar 15 de {close_votes.length} votações.</p>
            )}
          </div>
        )}
      </div>
    );
  };

  // Combined Overview Component
  const OverviewChart = () => {
    return (
      <div className="space-y-8">
        {/* Party Discipline Section */}
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Shield className="h-5 w-5 text-blue-600 mr-2" />
            Alinhamento com o Grupo
          </h4>
          <PartyDisciplineChart />
        </div>

        {/* Vote Distribution Section */}
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <PieChart className="h-5 w-5 text-purple-600 mr-2" />
            Padrão de Votação
          </h4>
          <VoteDistributionChart />
        </div>

        {/* Participation Timeline Section */}
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Activity className="h-5 w-5 text-green-600 mr-2" />
            Votações por Dia
          </h4>
          <ParticipationTimelineChart />
          <p className="text-xs text-gray-500 mt-3">{ABSENCE_NOTE}</p>
        </div>
      </div>
    );
  };

  const renderChart = () => {
    switch (activeChart) {
      case 'overview':
        return <OverviewChart />;
      case 'collaboration':
        return <CollaborationChart />;
      case 'dissent':
        return <DissentVotesChart />;
      case 'close':
        return <CloseVotesChart />;
      default:
        return <OverviewChart />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Educational Context Panel - Per Political Analyst Recommendations */}
      <div style={{
        backgroundColor: tokens.colors.contextEducationalBg,
        borderLeft: `4px solid ${tokens.colors.contextEducationalBorder}`,
        borderRadius: '2px',
        padding: '16px 20px',
        marginBottom: '16px',
        fontFamily: tokens.fonts.body,
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
        }}>
          <BookOpen
            size={18}
            style={{ color: tokens.colors.primary, marginTop: '2px', flexShrink: 0 }}
          />
          <div>
            <h4 style={{
              fontFamily: tokens.fonts.body,
              fontSize: '0.875rem',
              fontWeight: 600,
              color: tokens.colors.textPrimary,
              margin: '0 0 8px 0',
            }}>
              Como interpretar os dados de votação
            </h4>
            <p style={{
              fontFamily: tokens.fonts.body,
              fontSize: '0.875rem',
              lineHeight: 1.6,
              color: tokens.colors.textSecondary,
              margin: '0 0 8px 0',
            }}>
              Portugal opera um sistema de <strong>representação proporcional por lista partidária</strong>.
              Os cidadãos votam em partidos e programas, não em candidatos individuais.
              A <strong>disciplina de voto</strong> é uma característica normal e esperada do sistema parlamentar português.
            </p>
            <p style={{
              fontFamily: tokens.fonts.body,
              fontSize: '0.875rem',
              lineHeight: 1.6,
              color: tokens.colors.textSecondary,
              margin: 0,
            }}>
              <strong>Nota:</strong> Divergências pontuais do grupo parlamentar podem ocorrer em questões de consciência
              ou interesse regional, mas devem ser interpretadas no seu contexto específico.
            </p>
          </div>
        </div>
      </div>

      {/* Chart Navigation */}
      <div style={{
        borderBottom: `1px solid ${tokens.colors.border}`,
        backgroundColor: tokens.colors.bgWarm || '#F8F6F0',
        margin: '0 -28px',
        padding: '0 28px',
      }}>
        <nav style={{
          display: 'flex',
          gap: '0',
          overflowX: 'auto',
        }}>
          {charts.map((chart, index) => {
            const Icon = chart.icon;
            const isActive = activeChart === chart.id;
            return (
              <button
                key={chart.id}
                onClick={() => setActiveChart(chart.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '12px 16px',
                  fontFamily: tokens.fonts.body,
                  fontSize: '0.8125rem',
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? tokens.colors.primary : tokens.colors.textSecondary,
                  backgroundColor: isActive ? 'white' : 'transparent',
                  border: 'none',
                  borderBottom: isActive ? `2px solid ${tokens.colors.primary}` : '2px solid transparent',
                  borderRight: index < charts.length - 1 ? `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}` : 'none',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.2s ease',
                }}
              >
                <Icon style={{ width: '14px', height: '14px' }} />
                {chart.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Chart Content */}
      <div className="min-h-96">
        {renderChart()}
      </div>

      {/* Summary Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <TrendingUp className="h-5 w-5 text-blue-600 mt-0.5 mr-3" />
          <div>
            <h5 className="text-sm font-medium text-blue-900">
              Como estes números são calculados
            </h5>
            <p className="text-sm text-blue-700 mt-1">
              Votações em plenário da legislatura {analytics.legislatura} em que o deputado
              {analytics.deputy_info?.party && ` (${analytics.deputy_info.party.sigla})`} tinha lugar. O sentido
              de voto de cada deputado é o do seu grupo, exceto quando o registo da votação o nomeia.
            </p>
            {analytics.data_sources && (
              <div className="mt-3 pt-3 border-t border-blue-200">
                <p className="text-xs text-blue-600">
                  <strong>Fontes:</strong> {analytics.data_sources.votes_counted} votações em plenário com sentido de
                  voto conhecido, dados abertos da Assembleia da República
                </p>
                <p className="text-xs text-blue-500 mt-1 italic">{ABSENCE_NOTE}</p>
                {analytics.data_sources.note && (
                  <p className="text-xs text-blue-500 mt-1 italic">
                    {analytics.data_sources.note}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VotingAnalytics;