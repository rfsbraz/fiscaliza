"""
Schema Mappers Package
=====================

This package contains all schema mappers for the unified parliament data importer.
Each mapper handles a specific file type and provides XML-to-database mapping functionality.
"""

from .enhanced_base_mapper import SchemaMapper, SchemaError
from .registo_biografico import RegistoBiograficoMapper
from .iniciativas import InitiativasMapper
from .intervencoes import IntervencoesMapper
from .registo_interesses import RegistoInteressesMapper
from .atividade_deputados import AtividadeDeputadosMapper
from .agenda_parlamentar import AgendaParlamentarMapper
from .atividades import AtividadesMapper
from .composicao_orgaos import ComposicaoOrgaosMapper
from .cooperacao import CooperacaoMapper
from .delegacao_eventual import DelegacaoEventualMapper
from .delegacao_permanente import DelegacaoPermanenteMapper
from .grupos_amizade import GruposAmizadeMapper
from .informacao_base_mapper import InformacaoBaseMapper
from .peticoes import PeticoesMapper
from .perguntas_requerimentos import PerguntasRequerimentosMapper
from .diplomas_aprovados import DiplomasAprovadosMapper
from .orcamento_estado_mapper import OrcamentoEstadoMapper
from .reunioes_nacionais import ReunioesNacionaisMapper

__all__ = [
    'SchemaMapper',
    'SchemaError', 
    'RegistoBiograficoMapper',
    'InitiativasMapper',
    'IntervencoesMapper',
    'RegistoInteressesMapper',
    'AtividadeDeputadosMapper',
    'AgendaParlamentarMapper',
    'AtividadesMapper',
    'ComposicaoOrgaosMapper',
    'CooperacaoMapper',
    'DelegacaoEventualMapper',
    'DelegacaoPermanenteMapper',
    'GruposAmizadeMapper',
    'InformacaoBaseMapper',
    'PeticoesMapper',
    'PerguntasRequerimentosMapper',
    'DiplomasAprovadosMapper',
    'OrcamentoEstadoMapper',
    'ReunioesNacionaisMapper'
]