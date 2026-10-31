"""The questions set: written questions (perguntas and requerimentos), their authors and their
recipients, in the parlamento-aberto marts ``questions``, ``question_authors`` and
``question_recipients``. Ids 7001 to 7007 (XVII) and 6001 to 6003 (XVI).

Perguntas to the Government (``question_type='Pergunta'``, ``recipient_category='AC'``):

- XVII: 7001 by person 1, to Ministra da Saúde, answered after 20 days. 7002 by person 1 with
  person 90, to Ministra da Saúde, answered after 40 days. 7003 by person 90, to Ministra da
  Saúde, unanswered. 7004 by person 2, to Ministro das Finanças (answered after 30 days) and to
  Ministra da Saúde (unanswered). 7005 by person 2, to Ministro das Finanças, withdrawn. 7007 by
  person 90, to Ministro das Finanças, returned.
- XVI: 6001 by person 1 (PS), to Ministra da Saúde, answered after 40 days. 6002 and 6003 by
  person 301, to Ministro das Finanças: 6002 answered after 10 days (its recipient spaced
  differently, as the source sometimes has it), 6003 answered with no answer date. 6003 is to
  Ministra das Finanças: the same office, after a new minister took it.

7006 is a requerimento by person 1, not a pergunta.
"""

SAUDE = "Ministra da Saúde"
FINANCAS = "Ministro das Finanças"

# question_id: (legislature, type, sent, authors [(cadastro_id, group)], recipients
# [(recipient, answer date or None, answered, extended, returned, withdrawn)])
QUESTIONS = {
    7001: ("XVII", "Pergunta", "2025-07-01", [(1, "PSD")], [(SAUDE, "2025-07-21", True, False, False, False)]),
    7002: (
        "XVII",
        "Pergunta",
        "2025-08-01",
        [(1, "PSD"), (90, "CH")],
        [(SAUDE, "2025-09-10", True, True, False, False)],
    ),
    7003: ("XVII", "Pergunta", "2025-09-01", [(90, "CH")], [(SAUDE, None, False, False, False, False)]),
    7004: (
        "XVII",
        "Pergunta",
        "2025-09-15",
        [(2, "PSD")],
        [(FINANCAS, "2025-10-15", True, False, False, False), (SAUDE, None, False, False, False, False)],
    ),
    7005: ("XVII", "Pergunta", "2025-10-01", [(2, "PSD")], [(FINANCAS, None, False, False, False, True)]),
    7006: ("XVII", "Requerimento", "2025-10-01", [(1, "PSD")], [(FINANCAS, None, False, False, False, False)]),
    7007: ("XVII", "Pergunta", "2026-10-01", [(90, "CH")], [(FINANCAS, None, False, False, True, False)]),
    6001: ("XVI", "Pergunta", "2024-05-01", [(1, "PS")], [(SAUDE, "2024-06-10", True, False, False, False)]),
    # The source spaces some recipient names differently from one question to the next.
    6002: (
        "XVI",
        "Pergunta",
        "2024-06-01",
        [(301, "PSD")],
        [("Ministro  das Finanças ", "2024-06-11", True, False, False, False)],
    ),
    # A new minister took the office: the source names it Ministra from then on.
    6003: (
        "XVI",
        "Pergunta",
        "2024-07-01",
        [(301, "PSD")],
        [("Ministra das Finanças", None, True, False, False, False)],
    ),
}


def question_tables():
    """{table: (columns, rows)} for the questions set."""
    questions, authors, recipients = [], [], []
    for qid, (leg, kind, sent, who, to) in QUESTIONS.items():
        answers = sum(1 for r in to if r[2])
        questions.append(
            (
                leg,
                qid,
                kind,
                "AC",
                str(qid % 1000),
                1,
                f"Pergunta {qid}",
                sent,
                sent,
                sent,
                False,
                f"https://example.org/perguntas/{qid}.pdf",
                len(who),
                len(to),
                answers,
            )
        )
        authors += [(leg, qid, cad, f"Deputado {cad}", group) for cad, group in who]
        recipients += [
            (leg, qid, name, sent, extended, returned, withdrawn, 1 if answered else 0, answered_on)
            for name, answered_on, answered, extended, returned, withdrawn in to
        ]
    return {
        "questions": (
            "legislature varchar, question_id bigint, question_type varchar, recipient_category varchar, "
            "number varchar, session_number integer, subject varchar, entry_date date, sent_date date, "
            "sent_date_raw varchar, sent_date_invalid boolean, document_url varchar, author_count bigint, "
            "recipient_count bigint, answer_count bigint",
            questions,
        ),
        "question_authors": (
            "legislature varchar, question_id bigint, cadastro_id bigint, author_name varchar, group_acronym varchar",
            authors,
        ),
        "question_recipients": (
            "legislature varchar, question_id bigint, recipient varchar, sent_date date, is_extended boolean, "
            "is_returned boolean, is_withdrawn boolean, answer_count bigint, first_answer_date date",
            recipients,
        ),
    }
