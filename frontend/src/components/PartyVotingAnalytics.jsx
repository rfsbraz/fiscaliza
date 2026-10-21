import React, { useState, useEffect } from 'react';
import { TrendingUp, BarChart3, Zap, Network, Activity, Shield } from 'lucide-react';
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
    { id: 'coalitions', label: 'Alinhamento com Outros Grupos', icon: Network },
    { id: 'effectiveness', label: 'Iniciativas e Votações', icon: Zap }
  ];

  // Votes with no different vote recorded, by initiative type. The record only names deputies
  // who vote differently from their group, and small groups have few deputies to name, so this
  // is a count for this group alone and is not compared across groups.
  const CohesionByThemeChart = () => {
    const { cohesion_by_theme } = analytics || {};

    if (!cohesion_by_theme || !cohesion_by_theme.length) {
      return (
        <div className="text-center py-8">
          <Shield className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Sem votações por tipo de iniciativa nesta legislatura</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cohesion_by_theme.map((theme) => (
            <div key={theme.tema} className="bg-white border rounded-lg p-6">
              <h5 className="text-sm font-medium text-gray-900 mb-2">{theme.tema}</h5>
              <div className="text-sm text-gray-700">
                {theme.cohesive_votes.toLocaleString('pt-PT')} de {theme.total_votes.toLocaleString('pt-PT')} votações
                sem votos diferentes registados
              </div>
            </div>
          ))}
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start">
            <Shield className="h-5 w-5 text-blue-600 mt-0.5 mr-3" />
            <div>
              <h5 className="text-sm font-medium text-blue-900">
                Votações sem votos diferentes registados
              </h5>
              <p className="text-sm text-blue-700 mt-1">
                Votações em plenário em que o grupo votou como um todo, por tipo de iniciativa, e em quantas
                o registo da votação não nomeia nenhum dos seus deputados com outro sentido de voto. Ausências
                não contam. O registo só nomeia quem vota de forma diferente, e um grupo pequeno tem poucos
                deputados que possam ser nomeados, por isso este número não serve para comparar grupos.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Initiatives and their outcomes
  const EffectivenessChart = () => {
    const { legislative_effectiveness, participation_metrics } = analytics || {};
    const byType = legislative_effectiveness?.by_type || [];

    return (
      <div className="space-y-6">
        <div className="bg-white border rounded-lg p-6 overflow-x-auto">
          <h5 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
            <BarChart3 className="h-5 w-5 text-purple-600 mr-2" />
            Iniciativas por Tipo
          </h5>
          {byType.length === 0 ? (
            <p className="text-sm text-gray-500">Nenhuma iniciativa nesta legislatura</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-600 border-b">
                  <th className="py-2 pr-4">Tipo</th>
                  <th className="py-2 pr-4 text-right">Apresentadas</th>
                  <th className="py-2 pr-4 text-right">Aprovadas</th>
                  <th className="py-2 pr-4 text-right">Rejeitadas</th>
                  <th className="py-2 pr-4 text-right">Sem desfecho</th>
                  <th className="py-2 text-right">Taxa de aprovação</th>
                </tr>
              </thead>
              <tbody>
                {byType.map((row) => (
                  <tr key={row.type_code} className="border-b last:border-0">
                    <td className="py-2 pr-4 text-gray-900">{row.tipo}</td>
                    <td className="py-2 pr-4 text-right">{row.initiated}</td>
                    <td className="py-2 pr-4 text-right">
                      {row.approved}
                      {row.partly_approved > 0 && (
                        <span className="text-xs text-gray-500"> ({row.partly_approved} em parte)</span>
                      )}
                    </td>
                    <td className="py-2 pr-4 text-right">{row.rejected}</td>
                    <td className="py-2 pr-4 text-right">{row.undecided}</td>
                    <td className="py-2 text-right">
                      {row.approval_rate == null ? 'sem taxa' : `${(row.approval_rate * 100).toFixed(1)}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {legislative_effectiveness?.note && (
            <p className="text-xs text-gray-500 mt-4">{legislative_effectiveness.note}</p>
          )}
        </div>

        <div className="bg-white border rounded-lg p-6">
          <h5 className="text-lg font-medium text-gray-900 mb-4">Atividade na Legislatura</h5>
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
          {participation_metrics.interventions_note && (
            <p className="text-xs text-gray-500 mt-4">{participation_metrics.interventions_note}</p>
          )}
        </div>
      </div>
    );
  };

  // Agreement with other groups
  const CoalitionPatternsChart = () => {
    const { coalition_patterns } = analytics || {};

    if (!coalition_patterns || !coalition_patterns.length) {
      return (
        <div className="text-center py-8">
          <Network className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Dados de alinhamento com outros grupos não disponíveis</p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <h4 className="text-lg font-semibold text-gray-900 flex items-center">
          <Network className="h-5 w-5 text-green-600 mr-2" />
          Alinhamento com Outros Grupos
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {coalition_patterns.map((coalition) => (
            <div key={coalition.party} className="bg-white border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h5 className="text-sm font-medium text-gray-900">{coalition.party}</h5>
                <span className="text-xs text-gray-500">
                  {coalition.aligned_votes}/{coalition.total_votes} votações
                </span>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-gray-600">Mesmo sentido de voto</span>
                  <span className="text-sm font-medium">
                    {(coalition.alignment_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="h-2 rounded-full transition-all duration-300 bg-blue-500"
                    style={{ width: `${coalition.alignment_rate * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-start">
            <Network className="h-5 w-5 text-green-600 mt-0.5 mr-3" />
            <div>
              <h5 className="text-sm font-medium text-green-900">
                Como se calcula
              </h5>
              <p className="text-sm text-green-700 mt-1">
                Votações em plenário em que os dois grupos votaram como um todo (a favor, contra ou abstenção),
                e em quantas o sentido de voto foi o mesmo.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Votes and initiatives by month
  const TemporalBehaviorChart = () => {
    const { temporal_behavior } = analytics || {};

    if (!temporal_behavior || !temporal_behavior.length) {
      return (
        <div className="text-center py-8">
          <TrendingUp className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Dados mensais não disponíveis</p>
        </div>
      );
    }

    const monthlyArray = temporal_behavior.slice(-12);

    return (
      <div className="space-y-6">
        <h4 className="text-lg font-semibold text-gray-900 flex items-center">
          <TrendingUp className="h-5 w-5 text-blue-600 mr-2" />
          Votações e Iniciativas por Mês (Últimos 12 Meses)
        </h4>

        <div className="bg-white border rounded-lg p-6">
          <div className="space-y-4">
            {monthlyArray.map((month) => (
              <div key={month.date} className="flex items-center space-x-4">
                <div className="w-20 text-sm font-medium text-gray-900">
                  {month.date}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1 text-xs text-gray-600">
                    <span>
                      {month.total_votes} votações: {month.favor_votes} a favor, {month.against_votes} contra,{' '}
                      {month.abstention_votes} abstenções
                    </span>
                    <span>{month.initiatives} iniciativas</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="h-2 bg-blue-500 rounded-full transition-all duration-300"
                      style={{ width: `${month.total_votes > 0 ? (month.favor_votes / month.total_votes) * 100 : 0}%` }}
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
                Por Mês
              </h5>
              <p className="text-sm text-blue-700 mt-1">
                Sentido de voto do grupo como um todo nas votações em plenário de cada mês (a barra mostra a parte
                a favor), e iniciativas que o grupo ou os seus deputados apresentaram nesse mês.
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
            Votações sem votos diferentes registados
          </h4>
          <CohesionByThemeChart />
        </div>

        {/* Legislative Effectiveness */}
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Zap className="h-5 w-5 text-purple-600 mr-2" />
            Iniciativas e Votações
          </h4>
          <EffectivenessChart />
        </div>

        {/* Temporal Behavior */}
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <TrendingUp className="h-5 w-5 text-green-600 mr-2" />
            Por Mês
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
              Sobre estes números
            </h5>
            <p className="text-sm text-indigo-700 mt-1">
              Votações em plenário e iniciativas do grupo {analytics.party_info?.sigla} na legislatura{' '}
              {analytics.legislatura}, a partir dos dados abertos da Assembleia da República.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PartyVotingAnalytics;