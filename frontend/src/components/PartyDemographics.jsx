import React, { useState, useEffect } from 'react';
import { Users, Briefcase, GraduationCap, MapPin, Calendar, UserCheck, RotateCcw, User, ArrowRight } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Link } from 'react-router-dom';
import { apiFetch } from '../config/api';

const PartyDemographics = ({ partidoId, dadosDemograficos, partidoInfo }) => {
  const [loading, setLoading] = useState(false);
  const [demographics, setDemographics] = useState(dadosDemograficos || null);

  useEffect(() => {
    if (!dadosDemograficos && partidoId) {
      fetchDemographics();
    } else if (dadosDemograficos) {
      setDemographics(dadosDemograficos);
    }
  }, [partidoId, dadosDemograficos]);

  const fetchDemographics = async () => {
    try {
      setLoading(true);
      const response = await apiFetch(`partidos/${encodeURIComponent(partidoId)}/deputados`);
      if (!response.ok) throw new Error('Erro ao carregar dados demográficos');
      const data = await response.json();
      setDemographics(data.demografia);
    } catch (error) {
      console.error('Erro ao carregar demografia:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Carregando análise demográfica...</span>
      </div>
    );
  }

  if (!demographics) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Dados demográficos não disponíveis</p>
      </div>
    );
  }

  // Color schemes for charts
  const PROFESSION_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16', '#F97316'];
  const AGE_COLORS = ['#1E40AF', '#3B82F6', '#60A5FA', '#93C5FD', '#DBEAFE'];
  const GENDER_COLORS = ['#3B82F6', '#EC4899', '#6B7280'];
  const EDUCATION_COLORS = ['#059669', '#10B981', '#34D399', '#6EE7B7'];
  const GEOGRAPHIC_COLORS = ['#7C3AED', '#8B5CF6', '#A78BFA', '#C4B5FD'];

  // Format data for charts
  const professionData = Object.entries(demographics.profissoes?.categorias || {})
    .map(([category, count]) => ({ name: category, value: count }))
    .sort((a, b) => b.value - a.value);

  const ageData = Object.entries(demographics.idades?.cohorts_geracionais || {})
    .map(([group, count]) => ({ name: group, value: count }))
    .sort((a, b) => a.name.localeCompare(b.name));

  const genderData = Object.entries(demographics.genero || {})
    .map(([gender, count]) => ({ 
      name: gender, 
      value: count 
    }));

  const educationData = Object.entries(demographics.educacao?.niveis || {})
    .map(([level, count]) => ({ name: level, value: count }))
    .sort((a, b) => b.value - a.value);

  const geographicData = Object.entries(demographics.geografia?.regional || {})
    .map(([region, count]) => ({ name: region, value: count }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="space-y-8">
      {/* Key Statistics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
          <div className="flex items-center">
            <Users className="h-8 w-8 text-blue-600" />
            <div className="ml-3">
              <p className="text-sm font-medium text-blue-600">Total Deputados</p>
              <p className="text-2xl font-bold text-blue-900">
                {demographics.profissoes?.total_especificadas || 
                 Object.values(demographics.genero || {}).reduce((a, b) => a + b, 0) || 0}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-gradient-to-r from-green-50 to-green-100 rounded-lg p-4 border border-green-200">
          <div className="flex items-center">
            <Calendar className="h-8 w-8 text-green-600" />
            <div className="ml-3">
              <p className="text-sm font-medium text-green-600">Idade Média</p>
              <p className="text-2xl font-bold text-green-900">
                {demographics.idades?.idade_media ? 
                  `${demographics.idades.idade_media} anos` : 'N/A'}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-gradient-to-r from-purple-50 to-purple-100 rounded-lg p-4 border border-purple-200">
          <div className="flex items-center">
            <UserCheck className="h-8 w-8 text-purple-600" />
            <div className="ml-3">
              <p className="text-sm font-medium text-purple-600">Diversidade</p>
              <p className="text-2xl font-bold text-purple-900">
                {demographics.genero && Object.keys(demographics.genero).length > 1 ? 
                  `${Math.min(...Object.values(demographics.genero)) / Math.max(...Object.values(demographics.genero)) * 100}%`.substring(0, 4) : 'N/A'}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-gradient-to-r from-orange-50 to-orange-100 rounded-lg p-4 border border-orange-200">
          <div className="flex items-center">
            <RotateCcw className="h-8 w-8 text-orange-600" />
            <div className="ml-3">
              <p className="text-sm font-medium text-orange-600">Renovação</p>
              <p className="text-2xl font-bold text-orange-900">
                {demographics.renovacao?.percentual_renovacao ? 
                  `${demographics.renovacao.percentual_renovacao.toFixed(1)}%` : 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Professional Background */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center mb-6">
          <Briefcase className="h-6 w-6 text-blue-600 mr-3" />
          <h3 className="text-xl font-semibold text-gray-900">Formação Profissional</h3>
        </div>
        
        {professionData.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={professionData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="name" 
                    angle={-45}
                    textAnchor="end"
                    height={80}
                    fontSize={12}
                  />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#3B82F6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            
            <div className="space-y-3">
              {professionData.map((item, index) => (
                <div key={item.name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center">
                    <div 
                      className="w-4 h-4 rounded mr-3"
                      style={{ backgroundColor: PROFESSION_COLORS[index % PROFESSION_COLORS.length] }}
                    ></div>
                    <span className="text-sm font-medium text-gray-900">{item.name}</span>
                  </div>
                  <span className="text-sm font-bold text-gray-700">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">Dados de formação profissional não disponíveis</p>
        )}
      </div>

      {/* Age Demographics */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center mb-6">
          <Calendar className="h-6 w-6 text-green-600 mr-3" />
          <h3 className="text-xl font-semibold text-gray-900">Demografia Etária</h3>
        </div>
        
        {ageData.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={ageData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {ageData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={AGE_COLORS[index % AGE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <p className="text-sm text-green-600 font-medium">Idade Média</p>
                  <p className="text-2xl font-bold text-green-900">
                    {demographics.idades?.idade_media || 'N/A'}
                  </p>
                </div>
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-600 font-medium">Idade Mediana</p>
                  <p className="text-2xl font-bold text-blue-900">
                    {demographics.idades?.idade_mediana || 'N/A'}
                  </p>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <p className="text-sm text-purple-600 font-medium">Amplitude</p>
                  <p className="text-2xl font-bold text-purple-900">
                    {demographics.idades?.min && demographics.idades?.max ? 
                      `${demographics.idades.min}-${demographics.idades.max}` : 'N/A'}
                  </p>
                </div>
              </div>
              
              
              <div className="space-y-2">
                {ageData.map((item, index) => (
                  <div key={item.name} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <div className="flex items-center">
                      <div 
                        className="w-3 h-3 rounded mr-2"
                        style={{ backgroundColor: AGE_COLORS[index % AGE_COLORS.length] }}
                      ></div>
                      <span className="text-sm text-gray-900">{item.name}</span>
                    </div>
                    <span className="text-sm font-medium text-gray-700">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">Dados etários não disponíveis</p>
        )}
        
        {/* Oldest and Youngest Deputies */}
        {(demographics.idades?.oldest_deputy || demographics.idades?.youngest_deputy) && (
          <div className="mt-8 bg-gray-50 rounded-lg p-6">
            <div className="divide-y divide-gray-200">
              {demographics.idades?.oldest_deputy && (
                <div className="py-4 hover:bg-gray-100 transition-colors rounded">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <div className="flex-shrink-0 relative">
                          {demographics.idades.oldest_deputy.id_cadastro ? (
                            <div className="h-12 w-12 relative group">
                              <img
                                src={`https://www.parlamento.pt/PublishingImages/Deputados/XVII/${demographics.idades.oldest_deputy.id_cadastro}.jpg`}
                                alt={demographics.idades.oldest_deputy.nome}
                                className="h-12 w-12 rounded-full object-cover bg-gray-200 ring-2 ring-white shadow-sm group-hover:ring-blue-300 transition-all duration-200"
                                onError={(e) => {
                                  e.target.style.display = 'none';
                                  e.target.nextSibling.style.display = 'flex';
                                }}
                              />
                              <div 
                                className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center ring-2 ring-white shadow-sm hidden"
                              >
                                <User className="h-6 w-6 text-blue-600" />
                              </div>
                            </div>
                          ) : (
                            <div className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center ring-2 ring-white shadow-sm hover:ring-blue-300 transition-all duration-200">
                              <User className="h-6 w-6 text-blue-600" />
                            </div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <Link 
                            to={`/deputados/${demographics.idades.oldest_deputy.id}/${demographics.idades.oldest_deputy.ultima_legislatura || '17'}`}
                            className="text-lg font-medium text-gray-900 hover:text-blue-600 transition-colors"
                          >
                            {demographics.idades.oldest_deputy.nome}
                          </Link>
                          {demographics.idades.oldest_deputy.profissao && (
                            <p className="text-sm text-gray-600 mt-1">
                              {demographics.idades.oldest_deputy.profissao}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-4 text-sm text-gray-500">
                      <div className="flex items-center">
                        <Calendar className="h-4 w-4 mr-1" />
                        <span className="font-bold text-red-600">{demographics.idades.oldest_deputy.idade} anos</span>
                        <span className="text-xs text-gray-400 ml-1">(mais velho)</span>
                      </div>
                      
                      <div className="flex items-center">
                        <MapPin className="h-4 w-4 mr-1" />
                        <span>{demographics.idades.oldest_deputy.circulo}</span>
                      </div>
                      
                      <div className="flex items-center">
                        <span className="text-xs text-gray-400">
                          {demographics.idades.oldest_deputy.mandato_ativo ? 
                            `Leg. ${demographics.idades.oldest_deputy.ultima_legislatura} (atual)` : 
                            `Última: Leg. ${demographics.idades.oldest_deputy.ultima_legislatura}`
                          }
                        </span>
                      </div>
                      
                      <div className="flex items-center">
                        {demographics.idades.oldest_deputy.mandato_ativo ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Ativo
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            Inativo
                          </span>
                        )}
                      </div>
                      
                      <Link 
                        to={`/deputados/${demographics.idades.oldest_deputy.id}/${demographics.idades.oldest_deputy.ultima_legislatura || '17'}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        Ver Detalhes →
                      </Link>
                    </div>
                  </div>
                </div>
              )}
              
              {demographics.idades?.youngest_deputy && (
                <div className="py-4 hover:bg-gray-100 transition-colors rounded">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <div className="flex-shrink-0 relative">
                          {demographics.idades.youngest_deputy.id_cadastro ? (
                            <div className="h-12 w-12 relative group">
                              <img
                                src={`https://www.parlamento.pt/PublishingImages/Deputados/XVII/${demographics.idades.youngest_deputy.id_cadastro}.jpg`}
                                alt={demographics.idades.youngest_deputy.nome}
                                className="h-12 w-12 rounded-full object-cover bg-gray-200 ring-2 ring-white shadow-sm group-hover:ring-blue-300 transition-all duration-200"
                                onError={(e) => {
                                  e.target.style.display = 'none';
                                  e.target.nextSibling.style.display = 'flex';
                                }}
                              />
                              <div 
                                className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center ring-2 ring-white shadow-sm hidden"
                              >
                                <User className="h-6 w-6 text-blue-600" />
                              </div>
                            </div>
                          ) : (
                            <div className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center ring-2 ring-white shadow-sm hover:ring-blue-300 transition-all duration-200">
                              <User className="h-6 w-6 text-blue-600" />
                            </div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <Link 
                            to={`/deputados/${demographics.idades.youngest_deputy.id}/${demographics.idades.youngest_deputy.ultima_legislatura || '17'}`}
                            className="text-lg font-medium text-gray-900 hover:text-blue-600 transition-colors"
                          >
                            {demographics.idades.youngest_deputy.nome}
                          </Link>
                          {demographics.idades.youngest_deputy.profissao && (
                            <p className="text-sm text-gray-600 mt-1">
                              {demographics.idades.youngest_deputy.profissao}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-4 text-sm text-gray-500">
                      <div className="flex items-center">
                        <Calendar className="h-4 w-4 mr-1" />
                        <span className="font-bold text-blue-600">{demographics.idades.youngest_deputy.idade} anos</span>
                        <span className="text-xs text-gray-400 ml-1">(mais novo)</span>
                      </div>
                      
                      <div className="flex items-center">
                        <MapPin className="h-4 w-4 mr-1" />
                        <span>{demographics.idades.youngest_deputy.circulo}</span>
                      </div>
                      
                      <div className="flex items-center">
                        <span className="text-xs text-gray-400">
                          {demographics.idades.youngest_deputy.mandato_ativo ? 
                            `Leg. ${demographics.idades.youngest_deputy.ultima_legislatura} (atual)` : 
                            `Última: Leg. ${demographics.idades.youngest_deputy.ultima_legislatura}`
                          }
                        </span>
                      </div>
                      
                      <div className="flex items-center">
                        {demographics.idades.youngest_deputy.mandato_ativo ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Ativo
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            Inativo
                          </span>
                        )}
                      </div>
                      
                      <Link 
                        to={`/deputados/${demographics.idades.youngest_deputy.id}/${demographics.idades.youngest_deputy.ultima_legislatura || '17'}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        Ver Detalhes →
                      </Link>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Gender and Geographic Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gender Representation */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center mb-6">
            <UserCheck className="h-6 w-6 text-purple-600 mr-3" />
            <h3 className="text-xl font-semibold text-gray-900">Representação de Género</h3>
          </div>
          
          {genderData.length > 0 ? (
            <div className="space-y-4">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={genderData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name} (${(percent * 100).toFixed(1)}%)`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {genderData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={GENDER_COLORS[index % GENDER_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              
              {demographics.genero && Object.keys(demographics.genero).length > 1 && (
                <div className="text-center p-3 bg-purple-50 rounded-lg">
                  <p className="text-sm text-purple-600 font-medium">Equilíbrio de Género</p>
                  <p className="text-lg font-bold text-purple-900">
                    {((Math.min(...Object.values(demographics.genero)) / Math.max(...Object.values(demographics.genero))) * 100).toFixed(1)}%
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">Dados de género não disponíveis</p>
          )}
        </div>

        {/* Geographic Distribution */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center mb-6">
            <MapPin className="h-6 w-6 text-indigo-600 mr-3" />
            <h3 className="text-xl font-semibold text-gray-900">Distribuição Geográfica</h3>
          </div>
          
          {geographicData.length > 0 ? (
            <div className="space-y-4">
              <div className="space-y-2">
                {geographicData.map((item, index) => (
                  <div key={item.name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center">
                      <div 
                        className="w-4 h-4 rounded mr-3"
                        style={{ backgroundColor: GEOGRAPHIC_COLORS[index % GEOGRAPHIC_COLORS.length] }}
                      ></div>
                      <span className="text-sm font-medium text-gray-900">{item.name}</span>
                    </div>
                    <span className="text-sm font-bold text-gray-700">{item.value}</span>
                  </div>
                ))}
              </div>
              
              {demographics.geografia?.urbano_rural && (
                <div className="mt-4 p-4 bg-indigo-50 rounded-lg">
                  <h4 className="text-sm font-medium text-indigo-900 mb-2">Distribuição Urbano/Rural</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-center">
                      <span className="text-indigo-600">Urbano:</span>
                      <span className="font-bold ml-1">
                        {demographics.geografia.urbano_rural.Urbano || 0}
                      </span>
                    </div>
                    <div className="text-center">
                      <span className="text-indigo-600">Rural:</span>
                      <span className="font-bold ml-1">
                        {demographics.geografia.urbano_rural.Rural || 0}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">Dados geográficos não disponíveis</p>
          )}
        </div>
      </div>

      {/* Education and Political Experience */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Educational Attainment */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center mb-6">
            <GraduationCap className="h-6 w-6 text-emerald-600 mr-3" />
            <h3 className="text-xl font-semibold text-gray-900">Habilitações Académicas</h3>
          </div>
          
          {educationData.length > 0 ? (
            <div className="space-y-3">
              {educationData.map((item, index) => (
                <div key={item.name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center">
                    <div 
                      className="w-4 h-4 rounded mr-3"
                      style={{ backgroundColor: EDUCATION_COLORS[index % EDUCATION_COLORS.length] }}
                    ></div>
                    <span className="text-sm font-medium text-gray-900">{item.name}</span>
                  </div>
                  <span className="text-sm font-bold text-gray-700">{item.value}</span>
                </div>
              ))}
              
              {demographics.educacao?.niveis && (
                <div className="mt-4 p-3 bg-emerald-50 rounded-lg text-center">
                  <p className="text-sm text-emerald-600 font-medium">Ensino Superior</p>
                  <p className="text-lg font-bold text-emerald-900">
                    {Object.entries(demographics.educacao.niveis)
                      .filter(([key]) => key.includes('Superior') || key.includes('Doutoramento') || key.includes('Pós-Graduação'))
                      .reduce((sum, [, value]) => sum + value, 0)}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500 mb-2">Dados educacionais em desenvolvimento</p>
              <p className="text-xs text-gray-400">TODO: Estruturar dados de habilitações académicas</p>
            </div>
          )}
        </div>

        {/* Political Experience */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center mb-6">
            <RotateCcw className="h-6 w-6 text-orange-600 mr-3" />
            <h3 className="text-xl font-semibold text-gray-900">Experiência Política</h3>
          </div>
          
          {demographics.experiencia_politica || demographics.renovacao ? (
            <div className="space-y-6">
              {/* Basic renewal metrics */}
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-4 bg-orange-50 rounded-lg">
                  <p className="text-sm text-orange-600 font-medium">Taxa de Renovação</p>
                  <p className="text-2xl font-bold text-orange-900">
                    {demographics.renovacao?.percentual_renovacao ? 
                      `${demographics.renovacao.percentual_renovacao.toFixed(1)}%` : 
                      demographics.renovacao?.percentagem_estreantes ? 
                        `${(demographics.renovacao.percentagem_estreantes * 100).toFixed(1)}%` : 'N/A'}
                  </p>
                  <p className="text-xs text-orange-600">novos deputados</p>
                </div>
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-600 font-medium">Experiência</p>
                  <p className="text-2xl font-bold text-blue-900">
                    {demographics.renovacao?.veteranos || 0}
                  </p>
                  <p className="text-xs text-blue-600">deputados com mandatos anteriores</p>
                </div>
              </div>

              {/* Experience categories chart */}
              {demographics.experiencia_politica?.categorias && 
               Object.keys(demographics.experiencia_politica.categorias).length > 0 && (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h4 className="text-sm font-medium text-gray-900 mb-3">Categorias de Experiência</h4>
                  <div className="h-64 mb-4">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={Object.entries(demographics.experiencia_politica.categorias).map(([category, count]) => ({ 
                        name: category.replace(/\(.*?\)/g, '').trim(), 
                        fullName: category,
                        value: count 
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="name" 
                          angle={-45}
                          textAnchor="end"
                          height={80}
                          fontSize={11}
                        />
                        <YAxis />
                        <Tooltip 
                          labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
                        />
                        <Bar dataKey="value" fill="#F97316" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  
                  {/* Legend */}
                  <div className="space-y-2">
                    {Object.entries(demographics.experiencia_politica.categorias).map(([category, count]) => (
                      <div key={category} className="flex items-center justify-between p-2 bg-white rounded border">
                        <span className="text-sm text-gray-900">{category}</span>
                        <span className="text-sm font-bold text-orange-600">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Mandate distribution */}
              {demographics.experiencia_politica?.mandatos_anteriores && 
               Object.keys(demographics.experiencia_politica.mandatos_anteriores).length > 0 && (
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h4 className="text-sm font-medium text-blue-900 mb-3">Distribuição por Número de Mandatos</h4>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={Object.entries(demographics.experiencia_politica.mandatos_anteriores)
                        .sort(([a], [b]) => parseInt(a) - parseInt(b))
                        .map(([mandates, count]) => ({ 
                          name: `${mandates} mandato${parseInt(mandates) > 1 ? 's' : ''}`, 
                          value: count 
                        }))}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" fontSize={12} />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="value" fill="#3B82F6" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Summary stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <p className="text-sm text-green-600 font-medium">Novos Deputados</p>
                  <p className="text-xl font-bold text-green-900">
                    {demographics.renovacao?.novos_deputados || 0}
                  </p>
                </div>
                <div className="text-center p-3 bg-purple-50 rounded-lg">
                  <p className="text-sm text-purple-600 font-medium">Veteranos</p>
                  <p className="text-xl font-bold text-purple-900">
                    {demographics.renovacao?.veteranos || 0}
                  </p>
                </div>
                <div className="text-center p-3 bg-indigo-50 rounded-lg">
                  <p className="text-sm text-indigo-600 font-medium">Total Analisado</p>
                  <p className="text-xl font-bold text-indigo-900">
                    {(demographics.renovacao?.novos_deputados || 0) + (demographics.renovacao?.veteranos || 0)}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500 mb-2">Análise de experiência política não disponível</p>
              <p className="text-xs text-gray-400">Os dados de carreira política necessitam de processamento adicional</p>
            </div>
          )}
        </div>
      </div>

      {/* Data Quality Notice */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800">Qualidade dos Dados</h3>
            <div className="mt-2 text-sm text-yellow-700">
              <p>Esta análise demográfica combina dados reais disponíveis com estimativas estatísticas para categorias onde os dados detalhados não estão completos. Algumas categorias utilizam projeções baseadas em padrões históricos típicos do parlamento português, que serão refinadas à medida que dados adicionais ficarem disponíveis.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PartyDemographics;