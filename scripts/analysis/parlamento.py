from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Legislatura(db.Model):
    __tablename__ = 'legislaturas'
    
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(10), nullable=False, unique=True)
    designacao = db.Column(db.String(100), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date)
    ativa = db.Column(db.Boolean, default=False)
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    mandatos = db.relationship('Mandato', backref='legislatura', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'numero': self.numero,
            'designacao': self.designacao,
            'data_inicio': self.data_inicio.isoformat() if self.data_inicio else None,
            'data_fim': self.data_fim.isoformat() if self.data_fim else None,
            'ativa': self.ativa,
            'observacoes': self.observacoes
        }

class Partido(db.Model):
    __tablename__ = 'partidos'
    
    id = db.Column(db.Integer, primary_key=True)
    sigla = db.Column(db.String(20), nullable=False, unique=True)
    designacao_completa = db.Column(db.String(200), nullable=False)
    data_constituicao = db.Column(db.Date)
    cor_representativa = db.Column(db.String(7))
    ideologia = db.Column(db.String(50))
    ativo = db.Column(db.Boolean, default=True)
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    mandatos = db.relationship('Mandato', backref='partido', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'sigla': self.sigla,
            'designacao_completa': self.designacao_completa,
            'data_constituicao': self.data_constituicao.isoformat() if self.data_constituicao else None,
            'cor_representativa': self.cor_representativa,
            'ideologia': self.ideologia,
            'ativo': self.ativo,
            'observacoes': self.observacoes
        }

class CirculoEleitoral(db.Model):
    __tablename__ = 'circulos_eleitorais'
    
    id = db.Column(db.Integer, primary_key=True)
    designacao = db.Column(db.String(100), nullable=False, unique=True)
    tipo = db.Column(db.String(30), nullable=False)
    numero_mandatos = db.Column(db.Integer)
    regiao = db.Column(db.String(50))
    ativo = db.Column(db.Boolean, default=True)
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    mandatos = db.relationship('Mandato', backref='circulo_eleitoral', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'designacao': self.designacao,
            'tipo': self.tipo,
            'numero_mandatos': self.numero_mandatos,
            'regiao': self.regiao,
            'ativo': self.ativo,
            'observacoes': self.observacoes
        }

class Deputado(db.Model):
    __tablename__ = 'deputados'
    
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(200), nullable=False)
    nome_parlamentar = db.Column(db.String(200))
    data_nascimento = db.Column(db.Date)
    sexo = db.Column(db.String(1))
    profissao = db.Column(db.String(100))
    habilitacoes_literarias = db.Column(db.String(100))
    naturalidade = db.Column(db.String(100))
    foto_url = db.Column(db.String(500))
    biografia = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    mandatos = db.relationship('Mandato', backref='deputado', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome_completo': self.nome_completo,
            'nome_parlamentar': self.nome_parlamentar,
            'data_nascimento': self.data_nascimento.isoformat() if self.data_nascimento else None,
            'sexo': self.sexo,
            'profissao': self.profissao,
            'habilitacoes_literarias': self.habilitacoes_literarias,
            'naturalidade': self.naturalidade,
            'foto_url': self.foto_url,
            'biografia': self.biografia,
            'ativo': self.ativo,
            'observacoes': self.observacoes
        }

class Mandato(db.Model):
    __tablename__ = 'mandatos'
    
    id = db.Column(db.Integer, primary_key=True)
    deputado_id = db.Column(db.Integer, db.ForeignKey('deputados.id'), nullable=False)
    partido_id = db.Column(db.Integer, db.ForeignKey('partidos.id'), nullable=False)
    circulo_eleitoral_id = db.Column(db.Integer, db.ForeignKey('circulos_eleitorais.id'), nullable=False)
    legislatura_id = db.Column(db.Integer, db.ForeignKey('legislaturas.id'), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date)
    motivo_fim = db.Column(db.String(50))
    numero_votos = db.Column(db.Integer)
    posicao_lista = db.Column(db.Integer)
    ativo = db.Column(db.Boolean, default=True)
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'deputado_id': self.deputado_id,
            'partido_id': self.partido_id,
            'circulo_eleitoral_id': self.circulo_eleitoral_id,
            'legislatura_id': self.legislatura_id,
            'data_inicio': self.data_inicio.isoformat() if self.data_inicio else None,
            'data_fim': self.data_fim.isoformat() if self.data_fim else None,
            'motivo_fim': self.motivo_fim,
            'numero_votos': self.numero_votos,
            'posicao_lista': self.posicao_lista,
            'ativo': self.ativo,
            'observacoes': self.observacoes
        }

