import React, { useState, useEffect } from 'react';
import { Target, TrendingUp, Users, BarChart3, Zap, Network, Activity, Shield } from 'lucide-react';
import { apiFetch } from '../config/api';

const PartyVotingAnalytics = ({ partidoId, legislatura }) => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeChart, setActiveChart] = useState('overview');

  useEffect(() => {
    const fetchPartyAnalytics = async () => {
      try {
        setLoading(true);
        const response = await apiFetch(`partidos/${encodeURIComponent(partidoId)}/voting-analytics?legislatura=${legislatura}`);
        if (!response.ok) {
          throw new Error('Erro ao carregar análises do partido');
        }
        const data = await response.json();
        setAnalytics(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (partidoId) {
      fetchPartyAnalytics();
    }
  }, [partidoId, legislatura]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Carregando análises do partido...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">Erro: {error}</div>
        <p className="text-gray-500">Não foi possível carregar as análises do partido</p>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Dados de análise não disponíveis</p>
      </div>
    );
  }

  const charts = [
    { id: 'overview', label: 'Visão Geral', icon: Activity },
    { id: 'positioning', label: 'Posicionamento Ideológico', icon: Target },
    { id: 'coalitions', label: 'Padrões de Coligação', icon: Network },
    { id: 'effectiveness', label: 'Eficácia Legislativa', icon: Zap }
  ];

  // Party Cohesion by Theme Component
  const CohesionByThemeChart = () => {
    const { cohesion_by_theme } = analytics || {};
    
    if (!cohesion_by_theme || !cohesion_by_theme.length) {
      return (
        <div className="text-center py-8">
          <Shield className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Dados de coesão partidária não disponíveis</p>
        </div>
      );
    }
    
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cohesion_by_theme.map((theme, index) => (
            <div key={theme.tema} className="bg-white border rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h5 className="text-sm font-medium text-gray-900">{theme.tema}</h5>
                <div className="text-xs text-gray-500">{theme.total_votes} votações</div>
              </div>
              
              <div className="mb-3">
                <div className="flex items-center justify-between text-sm mb-1">
                  <span>Coesão Partidária</span>
                  <span className="font-medium">{(theme.cohesion_score * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div 
                    className={`h-3 rounded-full transition-all duration-300 ${
                      theme.cohesion_score >= 0.9 ? 'bg-green-500' :
                      theme.cohesion_score >= 0.7 ? 'bg-yellow-500' :
                      'bg-red-500'
                    }`}
                    style={{ width: `${theme.cohesion_score * 100}%` }}
                  />
                </div>
              </div>
              
              <div className="text-xs text-gray-600">
                {theme.cohesion_score >= 0.9 ? '🟢 Muito Coesa' :
                 theme.cohesion_score >= 0.7 ? '🟡 Moderada' :
                 '🔴 Fragmentada'}
              </div>
            </div>
          ))}
        </div>
        
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start">
            <Shield className="h-5 w-5 text-blue-600 mt-0.5 mr-3" />
            <div>
              <h5 className="text-sm font-medium text-blue-900">
                Coesão Partidária por Tema
              </h5>
              <p className="text-sm text-blue-700 mt-1">
                Mede o grau de unidade do partido em diferentes áreas políticas. 
                Scores altos indicam disciplina partidária forte.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Legislative Effectiveness Chart
  const EffectivenessChart = () => {
    const { legislative_effectiveness, participation_metrics } = analytics || {};
    
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <BarChart3 className="h-6 w-6 text-purple-600" />
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-purple-900">
                  {legislative_effectiveness.bills_initiated}
                </div>
                <div className="text-sm text-purple-600">Iniciativas</div>
              </div>
            </div>
            <p className="text-sm text-purple-700">Projetos de lei apresentados</p>
          </div>
          
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <Target className="h-6 w-6 text-green-600" />
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-green-900">
                  {legislative_effectiveness.bills_passed}
                </div>
                <div className="text-sm text-green-600">Aprovadas</div>
              </div>
            </div>
            <p className="text-sm text-green-700">Iniciativas bem-sucedidas</p>
          </div>
          
          <div className="bg-gradient-to-r from-orange-50 to-red-50 border border-orange-200 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                <Zap className="h-6 w-6 text-orange-600" />
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-orange-900">
                  {(legislative_effectiveness.success_rate * 100).toFixed(1)}%
                </div>
                <div className="text-sm text-orange-600">Taxa Sucesso</div>
              </div>
            </div>
            <p className="text-sm text-orange-700">Eficácia legislativa</p>
          </div>
        </div>
        
        <div className="bg-white border rounded-lg p-6">
          <h5 className="text-lg font-medium text-gray-900 mb-4">Métricas de Participação</h5>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-xl font-bold text-gray-900">{participation_metrics.total_interventions}</div>
              <div className="text-sm text-gray-600">Intervenções</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-xl font-bold text-gray-900">{participation_metrics.total_initiatives}</div>
              <div className="text-sm text-gray-600">Iniciativas</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-xl font-bold text-gray-900">{participation_metrics.total_votes_participated}</div>
              <div className="text-sm text-gray-600">Votações</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Ideological Positioning Chart
  const IdeologicalPositioningChart = () => {
    const { ideological_positioning } = analytics || {};
    
    if (!ideological_positioning || !ideological_positioning.all_parties || !ideological_positioning.all_parties.length) {
      return (
        <div className="text-center py-8">
          <Target className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Dados de posicionamento não disponíveis</p>
        </div>
      );
    }
    
    const sortedParties = [...ideological_positioning.all_parties].sort((a, b) => b.favor_rate - a.favor_rate);
    const ourParty = analytics?.party_info?.sigla;
    
    return (
      <div className="space-y-6">
        <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-lg p-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Target className="h-5 w-5 text-indigo-600 mr-2" />
            Posicionamento Ideológico (Taxa de Aprovação)
          </h4>
          
          <div className="space-y-3">
            {sortedParties.map((party, index) => {
              const isOurParty = party.sigla === ourParty;
              return (
                <div key={party.sigla} className={`flex items-center space-x-4 p-3 rounded-lg ${
                  isOurParty ? 'bg-blue-100 border-2 border-blue-300' : 'bg-white border border-gray-200'
                }`}>
                  <div className="w-16 text-sm font-medium text-gray-900">
                    {party.sigla}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-600">
                        {isOurParty && '👈 Seu partido'}
                      </span>
                      <span className="text-sm font-medium">
                        {(party.favor_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full transition-all duration-300 ${
                          isOurParty ? 'bg-blue-500' : 'bg-gray-400'
                        }`}
                        style={{ width: `${party.favor_rate * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          
          <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
            <span>← Mais Opositor</span>
            <span>Mais Favorável →</span>
          </div>
        </div>
        
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start">
            <Target className="h-5 w-5 text-yellow-600 mt-0.5 mr-3" />
            <div>
              <h5 className="text-sm font-medium text-yellow-900">
                Interpretação do Posicionamento
              </h5>
              <p className="text-sm text-yellow-700 mt-1">
                Partidos com taxas de aprovação mais altas tendem a votar favoravelmente 
                mais frequentemente, indicando posições pró-governo ou pró-iniciativas.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Coalition Patterns Chart
  const CoalitionPatternsChart = () => {
    const { coalition_patterns } = analytics || {};
    
    if (!coalition_patterns || !coalition_patterns.length) {
      return (
        <div className="text-center py-8">
          <Network className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Dados de coligação não disponíveis</p>
        </div>
      );
    }
    
    const sortedCoalitions = [...coalition_patterns].sort((a, b) => b.alignment_rate - a.alignment_rate);
    
    return (
      <div className="space-y-6">
        <h4 className="text-lg font-semibold text-gray-900 flex items-center">
          <Network className="h-5 w-5 text-green-600 mr-2" />
          Padrões de Colaboração Inter-Partidária
        </h4>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sortedCoalitions.map((coalition, index) => (
            <div key={coalition.party} className="bg-white border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h5 className="text-sm font-medium text-gray-900">{coalition.party}</h5>
                <span className="text-xs text-gray-500">
                  {coalition.aligned_votes}/{coalition.total_votes} votações
                </span>
              </div>
              
              <div className="mb-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-gray-600">Alinhamento</span>
                  <span className="text-sm font-medium">
                    {(coalition.alignment_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-300 ${
                      coalition.alignment_rate >= 0.7 ? 'bg-green-500' :
                      coalition.alignment_rate >= 0.5 ? 'bg-yellow-500' :
                      coalition.alignment_rate >= 0.3 ? 'bg-orange-500' :
                      'bg-red-500'
                    }`}
                    style={{ width: `${coalition.alignment_rate * 100}%` }}
                  />
                </div>
              </div>
              
              <div className="text-xs">
                {coalition.alignment_rate >= 0.7 ? '🤝 Parceiro Frequente' :
                 coalition.alignment_rate >= 0.5 ? '🤝 Parceiro Ocasional' :
                 coalition.alignment_rate >= 0.3 ? '⚖️ Relação Mista' :
                 '🔴 Opositor Frequente'}
              </div>
            </div>
          ))}
        </div>
        
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-start">
            <Network className="h-5 w-5 text-green-600 mt-0.5 mr-3" />
            <div>
              <h5 className="text-sm font-medium text-green-900">
                Análise de Coligações
              </h5>
              <p className="text-sm text-green-700 mt-1">
                Mostra com que frequência o partido vota alinhado com outros partidos, 
                revelando potenciais parceiros de coligação e adversários políticos.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Temporal Behavior Chart
  const TemporalBehaviorChart = () => {
    const { temporal_behavior } = analytics || {};
    
    if (!temporal_behavior || !temporal_behavior.length) {
      return (
        <div className="text-center py-8">
          <TrendingUp className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Dados temporais não disponíveis</p>
        </div>
      );
    }
    
    // Calculate monthly averages for better visualization
    const monthlyData = temporal_behavior.reduce((acc, day) => {
      const month = day.date.substring(0, 7); // YYYY-MM
      if (!acc[month]) {
        acc[month] = { 
          month, 
          total_votes: 0, 
          favor_votes: 0, 
          total_days: 0 
        };
      }
      acc[month].total_votes += day.total_votes;
      acc[month].favor_votes += day.favor_votes;
      acc[month].total_days += 1;
      return acc;
    }, {});
    
    const monthlyArray = Object.values(monthlyData).map(month => ({
      ...month,
      favor_rate: month.total_votes > 0 ? month.favor_votes / month.total_votes : 0
    })).slice(-12); // Last 12 months
    
    return (
      <div className="space-y-6">
        <h4 className="text-lg font-semibold text-gray-900 flex items-center">
          <TrendingUp className="h-5 w-5 text-blue-600 mr-2" />
          Comportamento Temporal (Últimos 12 Meses)
        </h4>
        
        <div className="bg-white border rounded-lg p-6">
          <div className="space-y-4">
            {monthlyArray.map((month, index) => (
              <div key={month.month} className="flex items-center space-x-4">
                <div className="w-20 text-sm font-medium text-gray-900">
                  {month.month}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-600">
                      {month.total_votes} votações
                    </span>
                    <span className="text-sm font-medium">
                      {(month.favor_rate * 100).toFixed(1)}% favorável
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="h-2 bg-blue-500 rounded-full transition-all duration-300"
                      style={{ width: `${month.favor_rate * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start">
            <TrendingUp className="h-5 w-5 text-blue-600 mt-0.5 mr-3" />
            <div>
              <h5 className="text-sm font-medium text-blue-900">
                Tendências Temporais
              </h5>
              <p className="text-sm text-blue-700 mt-1">
                Analisa mudanças no comportamento de votação ao longo do tempo, 
                identificando períodos de maior ou menor apoio a iniciativas.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Combined Overview Component
  const OverviewChart = () => {
    return (
      <div className="space-y-8">
        {/* Cohesion by Theme */}
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Shield className="h-5 w-5 text-blue-600 mr-2" />
            Coesão Partidária por Tema
          </h4>
          <CohesionByThemeChart />
        </div>

        {/* Legislative Effectiveness */}
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Zap className="h-5 w-5 text-purple-600 mr-2" />
            Eficácia Legislativa
          </h4>
          <EffectivenessChart />
        </div>

        {/* Temporal Behavior */}
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <TrendingUp className="h-5 w-5 text-green-600 mr-2" />
            Comportamento Temporal
          </h4>
          <TemporalBehaviorChart />
        </div>
      </div>
    );
  };

  const renderChart = () => {
    switch (activeChart) {
      case 'overview':
        return <OverviewChart />;
      case 'positioning':
        return <IdeologicalPositioningChart />;
      case 'coalitions':
        return <CoalitionPatternsChart />;
      case 'effectiveness':
        return <EffectivenessChart />;
      default:
        return <OverviewChart />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Chart Navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8 overflow-x-auto">
          {charts.map((chart) => {
            const Icon = chart.icon;
            return (
              <button
                key={chart.id}
                onClick={() => setActiveChart(chart.id)}
                className={`flex items-center py-4 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap ${
                  activeChart === chart.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-4 w-4 mr-2" />
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
      <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
        <div className="flex items-start">
          <BarChart3 className="h-5 w-5 text-indigo-600 mt-0.5 mr-3" />
          <div>
            <h5 className="text-sm font-medium text-indigo-900">
              Análise Política Avançada
            </h5>
            <p className="text-sm text-indigo-700 mt-1">
              Estas visualizações analisam o comportamento do partido {analytics.party_info?.sigla} 
              na {legislatura}ª Legislatura, incluindo coesão interna, posicionamento ideológico, 
              padrões de coligação e eficácia legislativa baseados em dados reais de votação.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PartyVotingAnalytics;