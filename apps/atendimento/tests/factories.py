"""Factories dos objetos persistidos do atendimento."""

import factory
from factory.django import DjangoModelFactory

from apps.atendimento.models import Contato, Conversa, Mensagem
from apps.contas.models import Usuario
from apps.empresas.models import Empresa


class EmpresaFactory(DjangoModelFactory):
    """Cria empresas independentes para os cenarios de dominio."""

    class Meta:
        """Vincula a factory ao model Empresa."""

        model = Empresa

    nome = factory.Sequence(lambda numero: f"Empresa {numero}")


class UsuarioFactory(DjangoModelFactory):
    """Cria atores com e-mail unico para auditoria."""

    class Meta:
        """Vincula a factory ao model Usuario."""

        model = Usuario

    email = factory.Sequence(lambda numero: f"ator-{numero}@example.com")


class ContatoFactory(DjangoModelFactory):
    """Cria contatos com numero unico por padrao."""

    class Meta:
        """Vincula a factory ao model Contato."""

        model = Contato

    empresa = factory.SubFactory(EmpresaFactory)
    nome = factory.Sequence(lambda numero: f"Contato {numero}")
    numero_normalizado = factory.Sequence(lambda numero: f"556899{numero:04d}")


class ConversaFactory(DjangoModelFactory):
    """Cria conversas coerentes com o tenant do contato."""

    class Meta:
        """Vincula a factory ao model Conversa."""

        model = Conversa

    contato = factory.SubFactory(ContatoFactory)
    empresa = factory.SelfAttribute("contato.empresa")


class MensagemFactory(DjangoModelFactory):
    """Cria mensagens coerentes com conversa e empresa."""

    class Meta:
        """Vincula a factory ao model Mensagem."""

        model = Mensagem

    conversa = factory.SubFactory(ConversaFactory)
    empresa = factory.SelfAttribute("conversa.empresa")
    direcao = Mensagem.Direcao.ENTRADA
    autor = Mensagem.Autor.CLIENTE
    texto = factory.Sequence(lambda numero: f"Mensagem {numero}")
    status = Mensagem.Status.RECEBIDA
