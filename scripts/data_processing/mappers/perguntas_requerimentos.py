"""
Parliamentary Questions and Requests Mapper
===========================================

Schema mapper for parliamentary questions and requests files (Requerimentos<Legislatura>.xml).
Handles parliamentary questions and formal requests submitted by deputies.

Based on official Parliament documentation (December 2017):
- Questions (Perguntas) are oversight instruments and political control acts that can only
  be directed to the Government and Public Administration, not to regional and local administration.
- Requests (Requerimentos) are used to obtain information, elements and official publications
  useful for the exercise of the Deputy's mandate and can be directed to any public entity.

XML Structure: Requerimentos_DetalheRequerimentosOut containing:
- Main request data with TipodeRequerimento enum for reqTipo field
- Authors using Iniciativas_AutoresDeputadosOut structure
- Recipients using Requerimentos_DestinatariosOut structure with status tracking
- Publications using PublicacoesOut structure with TipodePublicacao enum
- Responses using Requerimentos_RespostasOut structure (for older requests)
"""

import logging
import os
import re
import uuid

# Import our models
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Set

from .enhanced_base_mapper import EnhancedSchemaMapper, SchemaError

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from database.models import (
    Deputado,
    Legislatura,
    PerguntaRequerimento,
    PerguntaRequerimentoAutor,
    PerguntaRequerimentoDestinatario,
    PerguntaRequerimentoPublicacao,
    PerguntaRequerimentoResposta,
)

logger = logging.getLogger(__name__)


class PerguntasRequerimentosMapper(EnhancedSchemaMapper):
    """Schema mapper for parliamentary questions and requests files"""

    def __init__(self, session, import_status_record=None):
        # Accept SQLAlchemy session directly (passed by unified importer)
        super().__init__(session, import_status_record=import_status_record)

    def get_expected_fields(self) -> Set[str]:
        return {
            # Root elements
            "ArrayOfRequerimentoOut",
            "ArrayOfRequerimentoOut.RequerimentoOut",
            # Main request fields from Requerimentos_DetalheRequerimentosOut
            "ArrayOfRequerimentoOut.RequerimentoOut.Id",  # id: Código de Identificação
            "ArrayOfRequerimentoOut.RequerimentoOut.Tipo",  # tipo: Pergunta ou Requerimento
            "ArrayOfRequerimentoOut.RequerimentoOut.Nr",  # nr: Número do Requerimento/Pergunta
            "ArrayOfRequerimentoOut.RequerimentoOut.ReqTipo",  # reqTipo: TipodeRequerimento
            "ArrayOfRequerimentoOut.RequerimentoOut.Legislatura",  # legislatura: Legislatura
            "ArrayOfRequerimentoOut.RequerimentoOut.Sessao",  # sessao: Sessão Legislativa
            "ArrayOfRequerimentoOut.RequerimentoOut.Assunto",  # assunto: Assunto do requerimento
            "ArrayOfRequerimentoOut.RequerimentoOut.DtEntrada",  # dtEntrada: Data da Entrada
            "ArrayOfRequerimentoOut.RequerimentoOut.DataEnvio",  # dataEnvio: Data de envio para destinatário
            "ArrayOfRequerimentoOut.RequerimentoOut.Observacoes",  # observacoes: Observações
            "ArrayOfRequerimentoOut.RequerimentoOut.Ficheiro",  # ficheiro: Nome do ficheiro com texto
            "ArrayOfRequerimentoOut.RequerimentoOut.Fundamentacao",  # fundamentacao: Descrição da fundamentação
            # Publication section
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubNr",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTipo",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTp",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubLeg",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubSL",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubdt",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.idPag",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.URLDiario",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pag",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pag.string",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.supl",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.obs",
            "ArrayOfRequerimentoOut.RequerimentoOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pagFinalDiarioSupl",
            # Recipients section from Requerimentos_DestinatariosOut
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.nomeEntidade",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.dataProrrogacao",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.dataReenvio",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.devolvido",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.prazoProrrogacao",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.prorrogado",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.reenviado",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.retirado",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.dataEnvio",
            # Responses section
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.entidade",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.dataResposta",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.ficheiro",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.docRemetida",
            
            # Publication section within Destinatarios respostas
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubNr",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTipo",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTp",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubLeg",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubSL",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubdt",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.idPag",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.URLDiario",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pag",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pag.string",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.supl",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.obs",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pagFinalDiarioSupl",
            
            # File attachment fields (ficheiroComTipo structure)
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.ficheiroComTipo",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.ficheiroComTipo.pt_gov_ar_objectos_Requirimento_Ficheiro_de_Resposta",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.ficheiroComTipo.pt_gov_ar_objectos_Requirimento_Ficheiro_de_Resposta.url",
            "ArrayOfRequerimentoOut.RequerimentoOut.Destinatarios.pt_gov_ar_objectos_requerimentos_DestinatariosOut.respostas.pt_gov_ar_objectos_requerimentos_RespostasOut.ficheiroComTipo.pt_gov_ar_objectos_Requirimento_Ficheiro_de_Resposta.tipo",
            # Authors section
            "ArrayOfRequerimentoOut.RequerimentoOut.Autores",
            "ArrayOfRequerimentoOut.RequerimentoOut.Autores.pt_gov_ar_objectos_iniciativas_AutoresDeputadosOut",
            "ArrayOfRequerimentoOut.RequerimentoOut.Autores.pt_gov_ar_objectos_iniciativas_AutoresDeputadosOut.idCadastro",
            "ArrayOfRequerimentoOut.RequerimentoOut.Autores.pt_gov_ar_objectos_iniciativas_AutoresDeputadosOut.nome",
            "ArrayOfRequerimentoOut.RequerimentoOut.Autores.pt_gov_ar_objectos_iniciativas_AutoresDeputadosOut.GP",
            
            # RespostasSPerguntas section (alternative response structure for questions)
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.entidade",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.dataResposta",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.ficheiro",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.docRemetida",
            
            # RespostasSPerguntas publication section
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubNr",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTipo",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTp",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubLeg",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubSL",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubdt",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.idPag",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.URLDiario",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pag",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pag.string",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.supl",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.obs",
            "ArrayOfRequerimentoOut.RequerimentoOut.RespostasSPerguntas.pt_gov_ar_objectos_requerimentos_RespostasOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pagFinalDiarioSupl",
        }

    def validate_and_map(
        self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False
    ) -> Dict:
        """Map parliamentary questions and requests to database"""
        results = {"records_processed": 0, "records_imported": 0, "errors": []}

        # Store file_info for use in other methods
        self.file_info = file_info

        try:
            # Validate schema coverage according to strict mode
            self.validate_schema_coverage(xml_root, file_info, strict_mode)

            # Extract legislatura from filename or XML
            legislatura_sigla = self._extract_legislatura(
                file_info["file_path"], xml_root
            )
            legislatura = self._get_or_create_legislatura(legislatura_sigla)

            # Process requests/questions
            for request in xml_root.findall(".//RequerimentoOut"):
                try:
                    success = self._process_request(request, legislatura)
                    results["records_processed"] += 1
                    if success:
                        results["records_imported"] += 1
                except Exception as e:
                    error_msg = f"Request processing error: {str(e)}"
                    logger.error(error_msg)
                    logger.error("Data integrity issue detected during request processing")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    results["errors"].append(error_msg)
                    results["records_processed"] += 1
                    raise RuntimeError(f"Data integrity issue: {error_msg}")

            # Commit all changes
            return results

        except Exception as e:
            error_msg = f"Critical error processing requests: {str(e)}"
            logger.error(error_msg)
            logger.error("Data integrity issue detected during critical request processing")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            results["errors"].append(error_msg)
            raise RuntimeError(f"Data integrity issue: {error_msg}")

    def _process_request(self, request: ET.Element, legislatura: Legislatura) -> bool:
        """Process individual request/question"""
        try:
            # Extract basic fields
            req_id = self._get_int_value(request, "Id")
            tipo = self._get_text_value(request, "Tipo")
            nr = self._get_int_value(request, "Nr")
            req_tipo = self._get_text_value(request, "ReqTipo")
            sessao = self._get_int_value(request, "Sessao")
            assunto = self._get_text_value(request, "Assunto")
            dt_entrada_str = self._get_text_value(request, "DtEntrada")
            data_envio_str = self._get_text_value(request, "DataEnvio")
            observacoes = self._get_text_value(request, "Observacoes")
            ficheiro = self._get_text_value(request, "Ficheiro")
            fundamentacao = self._get_text_value(request, "Fundamentacao")

            if not assunto:
                raise ValueError(
                    "Missing required Assunto field. Data integrity violation - cannot generate artificial content"
                )

            # Parse dates
            dt_entrada = self._parse_date(dt_entrada_str)
            data_envio = self._parse_date(data_envio_str)

            # Check if request already exists
            existing = None
            if req_id:
                existing = (
                    self.session.query(PerguntaRequerimento)
                    .filter_by(requerimento_id=req_id)
                    .first()
                )

            if existing:
                # Update existing record
                existing.tipo = tipo
                existing.nr = nr
                existing.req_tipo = req_tipo
                existing.sessao = sessao
                existing.assunto = assunto
                existing.dt_entrada = dt_entrada
                existing.data_envio = data_envio
                existing.observacoes = observacoes
                existing.ficheiro = ficheiro
                existing.fundamentacao = fundamentacao
                existing.legislatura_id = legislatura.id
            else:
                # Create new record
                pergunta_req = PerguntaRequerimento(
                    id=uuid.uuid4(),
                    requerimento_id=req_id,
                    tipo=tipo,
                    nr=nr,
                    req_tipo=req_tipo,
                    sessao=sessao,
                    assunto=assunto,
                    dt_entrada=dt_entrada,
                    data_envio=data_envio,
                    observacoes=observacoes,
                    ficheiro=ficheiro,
                    fundamentacao=fundamentacao,
                    legislatura_id=legislatura.id,
                )
                self._add_with_tracking(pergunta_req)
                existing = pergunta_req

            # Process related data
            self._process_request_publications(request, existing)
            self._process_request_destinatarios(request, existing)
            self._process_request_respostas_perguntas(request, existing)
            self._process_request_authors(request, existing)

            return True

        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return False

    def _get_author_info(self, request: ET.Element) -> Optional[str]:
        """Get author information from request"""
        authors_element = request.find("Autores")
        if authors_element is not None:
            for author in authors_element.findall(
                "pt_gov_ar_objectos_iniciativas_AutoresDeputadosOut"
            ):
                nome = self._get_text_value(author, "nome")
                gp = self._get_text_value(author, "GP")
                if nome:
                    return f"{nome} ({gp})" if gp else nome
        return None

    def _map_request_type(self, tipo: str, req_tipo: str) -> str:
        """Map request type to standard activity type"""
        if not tipo:
            return "PERGUNTA_REQUERIMENTO"

        tipo_upper = tipo.upper()

        if "PERGUNTA" in tipo_upper:
            return "PERGUNTA"
        elif "REQUERIMENTO" in tipo_upper:
            return "REQUERIMENTO"
        else:
            return "PERGUNTA_REQUERIMENTO"

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format"""
        if not date_str:
            return None

        try:
            # Handle ISO format: YYYY-MM-DD
            if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
                return date_str

            # Handle datetime format: DD/MM/YYYY HH:MM:SS
            if " " in date_str:
                date_part = date_str.split(" ")[0]
            else:
                date_part = date_str

            # Try DD/MM/YYYY format
            if "/" in date_part:
                parts = date_part.split("/")
                if len(parts) == 3:
                    day, month, year = parts
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        except (ValueError, IndexError):
            logger.warning(f"Could not parse date: {date_str}")

        return None

    # NOTE: _get_or_create_legislatura is inherited from EnhancedSchemaMapper (with caching)
    # NOTE: Roman numeral conversion uses ROMAN_TO_NUMBER from LegislatureHandlerMixin

    def _process_request_publications(
        self, request: ET.Element, pergunta_req: PerguntaRequerimento
    ):
        """Process publications for request"""
        publicacao = request.find("Publicacao")
        if publicacao is not None:
            for pub in publicacao.findall("pt_gov_ar_objectos_PublicacoesOut"):
                pub_nr = self._get_int_value(pub, "pubNr")
                pub_tipo = self._get_text_value(pub, "pubTipo")
                pub_tp = self._get_text_value(pub, "pubTp")
                pub_leg = self._get_text_value(pub, "pubLeg")
                pub_sl = self._get_int_value(pub, "pubSL")
                pub_dt = self._parse_date(self._get_text_value(pub, "pubdt"))
                id_pag = self._get_int_value(pub, "idPag")
                url_diario = self._get_text_value(pub, "URLDiario")
                supl = self._get_text_value(pub, "supl")
                obs = self._get_text_value(pub, "obs")
                pag_final_diario_supl = self._get_text_value(pub, "pagFinalDiarioSupl")

                # Handle page numbers
                pag_text = None
                pag_elem = pub.find("pag")
                if pag_elem is not None:
                    string_elems = pag_elem.findall("string")
                    if string_elems:
                        pag_text = ", ".join([s.text for s in string_elems if s.text])

                publicacao_record = PerguntaRequerimentoPublicacao(
                    pergunta_requerimento_id=pergunta_req.id,
                    pub_nr=pub_nr,
                    pub_tipo=pub_tipo,
                    pub_tp=pub_tp,
                    pub_leg=pub_leg,
                    pub_sl=pub_sl,
                    pub_dt=pub_dt,
                    id_pag=id_pag,
                    url_diario=url_diario,
                    pag=pag_text,
                    supl=supl,
                    obs=obs,
                    pag_final_diario_supl=pag_final_diario_supl,
                )
                self._add_with_tracking(publicacao_record)

    def _process_request_destinatarios(
        self, request: ET.Element, pergunta_req: PerguntaRequerimento
    ):
        """Process recipients for request from Requerimentos_DestinatariosOut structure"""
        destinatarios = request.find("Destinatarios")
        if destinatarios is not None:
            for dest in destinatarios.findall(
                "pt_gov_ar_objectos_requerimentos_DestinatariosOut"
            ):
                # Extract all recipient fields per PDF documentation
                nome_entidade = self._get_text_value(dest, "nomeEntidade")
                data_prorrogacao = self._parse_date(
                    self._get_text_value(dest, "dataProrrogacao")
                )
                data_reenvio = self._parse_date(
                    self._get_text_value(dest, "dataReenvio")
                )
                devolvido = self._get_boolean_value(dest, "devolvido")
                prazo_prorrogacao = self._get_int_value(dest, "prazoProrrogacao")
                prorrogado = self._get_boolean_value(dest, "prorrogado")
                reenviado = self._get_boolean_value(dest, "reenviado")
                retirado = self._get_boolean_value(dest, "retirado")
                data_envio = self._parse_date(self._get_text_value(dest, "dataEnvio"))

                destinatario_record = PerguntaRequerimentoDestinatario(
                    id=uuid.uuid4(),
                    pergunta_requerimento_id=pergunta_req.id,
                    nome_entidade=nome_entidade,
                    data_prorrogacao=data_prorrogacao,
                    data_reenvio=data_reenvio,
                    devolvido=devolvido,
                    prazo_prorrogacao=prazo_prorrogacao,
                    prorrogado=prorrogado,
                    reenviado=reenviado,
                    retirado=retirado,
                    data_envio=data_envio,
                )
                self._add_with_tracking(destinatario_record)

                # Process responses
                respostas = dest.find("respostas")
                if respostas is not None:
                    for resp in respostas.findall(
                        "pt_gov_ar_objectos_requerimentos_RespostasOut"
                    ):
                        entidade = self._get_text_value(resp, "entidade")
                        data_resposta = self._parse_date(
                            self._get_text_value(resp, "dataResposta")
                        )
                        ficheiro = self._get_text_value(resp, "ficheiro")
                        doc_remetida = self._get_text_value(resp, "docRemetida")
                        
                        # Process file attachment (ficheiroComTipo structure)
                        ficheiro_url = None
                        ficheiro_tipo = None
                        ficheiro_com_tipo = resp.find("ficheiroComTipo")
                        if ficheiro_com_tipo is not None:
                            ficheiro_resposta = ficheiro_com_tipo.find("pt_gov_ar_objectos_Requirimento_Ficheiro_de_Resposta")
                            if ficheiro_resposta is not None:
                                ficheiro_url = self._get_text_value(ficheiro_resposta, "url")
                                ficheiro_tipo = self._get_text_value(ficheiro_resposta, "tipo")

                        resposta_record = PerguntaRequerimentoResposta(
                            id=uuid.uuid4(),
                            destinatario_id=destinatario_record.id,
                            entidade=entidade,
                            data_resposta=data_resposta,
                            ficheiro=ficheiro,
                            doc_remetida=doc_remetida,
                            ficheiro_url=ficheiro_url,
                            ficheiro_tipo=ficheiro_tipo,
                        )
                        self._add_with_tracking(resposta_record)
                        
                        # Process publications within this response (same logic as RespostasSPerguntas)
                        publicacao = resp.find("publicacao")
                        if publicacao is not None:
                            for pub in publicacao.findall("pt_gov_ar_objectos_PublicacoesOut"):
                                pub_nr = self._get_int_value(pub, "pubNr")
                                pub_tipo = self._get_text_value(pub, "pubTipo")
                                pub_tp = self._get_text_value(pub, "pubTp")
                                pub_leg = self._get_text_value(pub, "pubLeg")
                                pub_sl = self._get_int_value(pub, "pubSL")
                                pub_dt = self._parse_date(self._get_text_value(pub, "pubdt"))
                                id_pag = self._get_int_value(pub, "idPag")
                                url_diario = self._get_text_value(pub, "URLDiario")
                                supl = self._get_text_value(pub, "supl")
                                obs = self._get_text_value(pub, "obs")
                                pag_final_diario_supl = self._get_text_value(pub, "pagFinalDiarioSupl")

                                # Handle page numbers
                                pag_text = None
                                pag_elem = pub.find("pag")
                                if pag_elem is not None:
                                    string_elems = pag_elem.findall("string")
                                    if string_elems:
                                        pag_text = ", ".join([s.text for s in string_elems if s.text])

                                publicacao_record = PerguntaRequerimentoPublicacao(
                                    pergunta_requerimento_id=pergunta_req.id,
                                    pub_nr=pub_nr,
                                    pub_tipo=pub_tipo,
                                    pub_tp=pub_tp,
                                    pub_leg=pub_leg,
                                    pub_sl=pub_sl,
                                    pub_dt=pub_dt,
                                    id_pag=id_pag,
                                    url_diario=url_diario,
                                    pag=pag_text,
                                    supl=supl,
                                    obs=obs,
                                    pag_final_diario_supl=pag_final_diario_supl,
                                )
                                self._add_with_tracking(publicacao_record)

    def _process_request_authors(
        self, request: ET.Element, pergunta_req: PerguntaRequerimento
    ):
        """Process authors for request"""
        autores = request.find("Autores")
        if autores is not None:
            for autor in autores.findall(
                "pt_gov_ar_objectos_iniciativas_AutoresDeputadosOut"
            ):
                id_cadastro = self._get_int_value(autor, "idCadastro")
                nome = self._get_text_value(autor, "nome")
                gp = self._get_text_value(autor, "GP")

                # Try to find the deputy
                deputado = None
                if id_cadastro:
                    deputado = (
                        self.session.query(Deputado)
                        .filter_by(id_cadastro=id_cadastro)
                        .first()
                    )
                    if not deputado:
                        raise ValueError(
                            f"Deputy with id_cadastro {id_cadastro} not found. Data integrity violation - cannot generate artificial content"
                        )

                autor_record = PerguntaRequerimentoAutor(
                    pergunta_requerimento_id=pergunta_req.id,
                    deputado_id=deputado.id if deputado else None,
                    id_cadastro=id_cadastro,
                    nome=nome,
                    gp=gp,
                )
                self._add_with_tracking(autor_record)

    def _process_request_respostas_perguntas(
        self, request: ET.Element, pergunta_req: PerguntaRequerimento
    ):
        """Process RespostasSPerguntas (direct responses to questions) for request"""
        respostas_perguntas = request.find("RespostasSPerguntas")
        if respostas_perguntas is not None:
            for resp in respostas_perguntas.findall(
                "pt_gov_ar_objectos_requerimentos_RespostasOut"
            ):
                entidade = self._get_text_value(resp, "entidade")
                data_resposta = self._parse_date(
                    self._get_text_value(resp, "dataResposta")
                )
                ficheiro = self._get_text_value(resp, "ficheiro")
                doc_remetida = self._get_text_value(resp, "docRemetida")
                
                # Create response record (direct response to question, no destinatario)
                resposta_record = PerguntaRequerimentoResposta(
                    id=uuid.uuid4(),
                    destinatario_id=None,  # Direct response, not through a recipient
                    entidade=entidade,
                    data_resposta=data_resposta,
                    ficheiro=ficheiro,
                    doc_remetida=doc_remetida
                )

                self._add_with_tracking(resposta_record)
                
                # Process publications within this response
                publicacao = resp.find("publicacao")
                if publicacao is not None:
                    for pub in publicacao.findall("pt_gov_ar_objectos_PublicacoesOut"):
                        pub_nr = self._get_int_value(pub, "pubNr")
                        pub_tipo = self._get_text_value(pub, "pubTipo")
                        pub_tp = self._get_text_value(pub, "pubTp")
                        pub_leg = self._get_text_value(pub, "pubLeg")
                        pub_sl = self._get_int_value(pub, "pubSL")
                        pub_dt = self._parse_date(self._get_text_value(pub, "pubdt"))
                        id_pag = self._get_int_value(pub, "idPag")
                        url_diario = self._get_text_value(pub, "URLDiario")
                        supl = self._get_text_value(pub, "supl")
                        obs = self._get_text_value(pub, "obs")
                        pag_final_diario_supl = self._get_text_value(pub, "pagFinalDiarioSupl")

                        # Handle page numbers
                        pag_text = None
                        pag_elem = pub.find("pag")
                        if pag_elem is not None:
                            string_elems = pag_elem.findall("string")
                            if string_elems:
                                pag_text = ", ".join([s.text for s in string_elems if s.text])

                        publicacao_record = PerguntaRequerimentoPublicacao(
                            pergunta_requerimento_id=pergunta_req.id,
                            pub_nr=pub_nr,
                            pub_tipo=pub_tipo,
                            pub_tp=pub_tp,
                            pub_leg=pub_leg,
                            pub_sl=pub_sl,
                            pub_dt=pub_dt,
                            id_pag=id_pag,
                            url_diario=url_diario,
                            pag=pag_text,
                            supl=supl,
                            obs=obs,
                            pag_final_diario_supl=pag_final_diario_supl,
                        )
                        self._add_with_tracking(publicacao_record)
