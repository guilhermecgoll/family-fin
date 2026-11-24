from financas.domain.tipos import TipoLancamento

_D = TipoLancamento.DESPESA
_R = TipoLancamento.RECEITA

CATEGORIAS_INICIAIS: tuple[tuple[str, TipoLancamento], ...] = (
    ("Residência", _D),
    ("Escola", _D),
    ("Alimentação", _D),
    ("Entretenimento", _D),
    ("Assinaturas", _D),
    ("Automóvel", _D),
    ("Saúde", _D),
    ("Vestuário", _D),
    ("Pets", _D),
    ("Presentes e datas", _D),
    ("Viagens", _D),
    ("Impostos, taxas e multas", _D),
    ("Outros", _D),
    ("Proventos", _R),
    ("Vale-refeição", _R),
    ("Remuneração financeira", _R),
)
