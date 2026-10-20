"""
Funcionamento da loja SALTY: horários semanais e abertura/fechamento manual.

Os dados ficam na tabela existente `configuracoes_loja` (chave, valor):

    loja_modo   -> "automatico" | "aberta" | "fechada"
    horario_0   -> segunda-feira  (0 = segunda ... 6 = domingo)
    ...
    horario_6   -> domingo
                   valor: "fechado" ou "HH:MM-HH:MM" ou "HH:MM-HH:MM,HH:MM-HH:MM"

Modos:
    automatico  segue os horários cadastrados
    aberta      aberta manualmente (ignora os horários)
    fechada     fechada manualmente (bloqueia pedidos mesmo no horário normal)

Este módulo é usado pelo painel (admin.py), pela API pública de status
e pela rota que cria pedidos (via loja_aberta_para_pedido).
"""

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Blueprint, jsonify

from backend.database import get_connection


DIAS_SEMANA = (
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
)

MODOS_LOJA = ("automatico", "aberta", "fechada")
CHAVE_MODO = "loja_modo"
CHAVES_HORARIO = tuple(f"horario_{i}" for i in range(7))
MAX_PERIODOS = 2

PADRAO_HORA = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

loja_publica_bp = Blueprint("loja_publica", __name__)


# ==========================================
# HORA ATUAL (America/Sao_Paulo)
# ==========================================

def agora_brasil():
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo"))
    except ZoneInfoNotFoundError:
        # Windows sem o pacote tzdata: usa UTC-3 (Brasil sem horário de verão)
        return datetime.now(timezone(timedelta(hours=-3)))


# ==========================================
# LEITURA E INTERPRETAÇÃO
# ==========================================

def interpretar_dia(valor):
    """None = não configurado; [] = fechado; lista = períodos do dia."""
    if valor is None:
        return None

    texto = str(valor).strip().lower()

    if texto in ("", "fechado"):
        return []

    periodos = []

    for parte in texto.split(","):
        abre, _, fecha = parte.strip().partition("-")

        if (
            not PADRAO_HORA.match(abre)
            or not PADRAO_HORA.match(fecha)
            or fecha <= abre
        ):
            return []  # valor corrompido: trata o dia como fechado

        periodos.append({"abre": abre, "fecha": fecha})

    return periodos


def formatar_dia(periodos):
    if not periodos:
        return "fechado"

    return ",".join(f"{p['abre']}-{p['fecha']}" for p in periodos)


def ler_configuracao(cursor):
    chaves = (CHAVE_MODO,) + CHAVES_HORARIO
    marcadores = ", ".join(["%s"] * len(chaves))

    cursor.execute(
        f"SELECT chave, valor FROM configuracoes_loja "
        f"WHERE chave IN ({marcadores})",
        chaves,
    )

    valores = {}

    for linha in cursor.fetchall():
        if isinstance(linha, dict):
            valores[linha["chave"]] = linha["valor"]
        else:
            valores[linha[0]] = linha[1]

    modo = str(valores.get(CHAVE_MODO) or "automatico").strip().lower()

    if modo not in MODOS_LOJA:
        modo = "automatico"

    dias = [interpretar_dia(valores.get(chave)) for chave in CHAVES_HORARIO]

    return modo, dias


# ==========================================
# VALIDAÇÃO E GRAVAÇÃO
# ==========================================

def validar_dias(dias):
    """Retorna (lista de 7 itens com os períodos de cada dia, erro)."""
    if not isinstance(dias, list) or len(dias) != 7:
        return None, "Informe a configuração dos 7 dias da semana."

    resultado = [None] * 7

    for item in dias:
        if not isinstance(item, dict):
            return None, "Configuração de dia inválida."

        dia = item.get("dia")

        if (
            isinstance(dia, bool)
            or not isinstance(dia, int)
            or not 0 <= dia <= 6
            or resultado[dia] is not None
        ):
            return None, "Dia da semana inválido ou repetido."

        nome = DIAS_SEMANA[dia]
        aberto = item.get("aberto")

        if not isinstance(aberto, bool):
            return None, f"Informe se {nome} abre ou fica fechado."

        if not aberto:
            resultado[dia] = []
            continue

        periodos = item.get("periodos")

        if (
            not isinstance(periodos, list)
            or not 1 <= len(periodos) <= MAX_PERIODOS
        ):
            return None, (
                f"Informe de 1 a {MAX_PERIODOS} períodos para {nome}."
            )

        validados = []

        for periodo in periodos:
            abre = periodo.get("abre") if isinstance(periodo, dict) else None
            fecha = periodo.get("fecha") if isinstance(periodo, dict) else None

            if not (
                isinstance(abre, str)
                and isinstance(fecha, str)
                and PADRAO_HORA.match(abre)
                and PADRAO_HORA.match(fecha)
            ):
                return None, (
                    f"Informe abertura e fechamento válidos (HH:MM) "
                    f"para {nome}."
                )

            if fecha <= abre:
                return None, (
                    f"Em {nome}, o fechamento deve ser depois da abertura."
                )

            if validados and abre <= validados[-1]["fecha"]:
                return None, (
                    f"Em {nome}, o segundo período deve começar depois "
                    f"do fim do primeiro."
                )

            validados.append({"abre": abre, "fecha": fecha})

        resultado[dia] = validados

    return resultado, None


def _gravar(cursor, chave, valor):
    cursor.execute("""
        INSERT INTO configuracoes_loja (chave, valor)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE valor = VALUES(valor)
    """, (chave, valor))


def salvar_dias(cursor, dias):
    for indice, periodos in enumerate(dias):
        _gravar(cursor, CHAVES_HORARIO[indice], formatar_dia(periodos))


def salvar_modo(cursor, modo):
    _gravar(cursor, CHAVE_MODO, modo)


# ==========================================
# SITUAÇÃO ATUAL DA LOJA
# ==========================================

def _texto_periodos(periodos):
    return " e ".join(f"{p['abre']} às {p['fecha']}" for p in periodos)


def _proxima_abertura(dias, dia_atual, hhmm):
    for deslocamento in range(8):
        indice = (dia_atual + deslocamento) % 7

        for periodo in dias[indice] or []:
            if deslocamento == 0 and periodo["abre"] <= hhmm:
                continue

            if deslocamento == 0:
                quando = "hoje"
            elif deslocamento == 1:
                quando = "amanhã"
            else:
                quando = DIAS_SEMANA[indice].lower()

            return {
                "quando": quando,
                "dia": DIAS_SEMANA[indice],
                "abre": periodo["abre"],
            }

    return None


def obter_situacao(cursor, agora=None):
    modo, dias = ler_configuracao(cursor)

    agora = agora or agora_brasil()
    hhmm = agora.strftime("%H:%M")
    dia_atual = agora.weekday()

    configurado = any(dia is not None for dia in dias)

    if configurado:
        periodos_hoje = dias[dia_atual] or []
        aberta_pelo_horario = any(
            p["abre"] <= hhmm < p["fecha"] for p in periodos_hoje
        )
    else:
        # Nenhum horário cadastrado ainda: não bloqueia pedidos.
        periodos_hoje = []
        aberta_pelo_horario = True

    proxima = None

    if modo == "aberta":
        aberta, motivo = True, "manual_aberta"
        mensagem = "Loja aberta."
    elif modo == "fechada":
        aberta, motivo = False, "manual_fechada"
        mensagem = (
            "Loja fechada no momento. "
            "Não estamos aceitando novos pedidos agora."
        )
    elif not configurado:
        aberta, motivo = True, "sem_horario_configurado"
        mensagem = "Loja aberta."
    elif aberta_pelo_horario:
        aberta, motivo = True, "horario"
        mensagem = "Loja aberta."
    else:
        aberta, motivo = False, "fora_do_horario"
        proxima = _proxima_abertura(dias, dia_atual, hhmm)
        mensagem = "Loja fechada no momento."

        if proxima:
            mensagem += (
                f" Próxima abertura: {proxima['quando']} "
                f"às {proxima['abre']}."
            )

    if not configurado:
        horario_hoje = None
    elif periodos_hoje:
        horario_hoje = _texto_periodos(periodos_hoje)
    else:
        horario_hoje = "Fechado hoje"

    return {
        "aberta": aberta,
        "modo": modo,
        "motivo": motivo,
        "mensagem": mensagem,
        "proxima_abertura": proxima,
        "horario_hoje": horario_hoje,
        "horarios_configurados": configurado,
        "agora": agora.strftime("%Y-%m-%d %H:%M"),
        "dias": [
            {
                "dia": indice,
                "nome": DIAS_SEMANA[indice],
                "aberto": bool(dias[indice]),
                "periodos": dias[indice] or [],
            }
            for indice in range(7)
        ],
    }


def situacao_publica(cursor):
    """Somente o que o cliente precisa saber (sem o modo interno)."""
    situacao = obter_situacao(cursor)

    return {
        "aberta": situacao["aberta"],
        "mensagem": situacao["mensagem"],
        "proxima_abertura": situacao["proxima_abertura"],
        "horario_hoje": situacao["horario_hoje"],
        "dias": [
            {
                "nome": dia["nome"],
                "aberto": dia["aberto"],
                "periodos": dia["periodos"],
            }
            for dia in situacao["dias"]
        ],
    }


def loja_aberta_para_pedido(cursor):
    """
    Use na rota que cria pedidos, ANTES de gravar o pedido, com a mesma
    conexão do banco. Retorna (aberta, mensagem).
    """
    situacao = obter_situacao(cursor)

    return situacao["aberta"], situacao["mensagem"]


# ==========================================
# API PÚBLICA: GET /api/loja/status
# (registre com url_prefix="/api/loja")
# ==========================================

@loja_publica_bp.get("/status")
def status_loja_publico():
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        resposta = jsonify(situacao_publica(cursor))
        resposta.headers["Cache-Control"] = "no-store"

        return resposta, 200

    except Exception:
        return jsonify({
            "error": "Não foi possível consultar o funcionamento da loja."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()
