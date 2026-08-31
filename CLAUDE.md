# CLAUDE.md — sigef-web

App Streamlit que preenche a planilha eletrônica oficial do INCRA
(`sigef_planilha_modelo_1.4_rc5.ods`) para certificação no SIGEF.
Responda e comente o código em português do Brasil.

O plano completo está em `PLANO_SIGEF_WEB.md`. Este arquivo traz só o que você
precisa saber para não quebrar nada.

## Regras invioláveis

1. **Nunca gerar o ODS do zero.** O SIGEF lê a planilha por posição de célula.
   Toda saída nasce do modelo oficial em `templates/`.
2. **Escrita no ODS = ZIP + `content.xml`.** Abrir o `.ods` com `zipfile`,
   alterar apenas o `content.xml` via lxml e regravar as demais entradas byte a
   byte (`mimetype` primeiro, sem compressão). Nunca usar odfpy/ezodf/pandas
   para *escrever*: eles descartam estilos, proteção de células e as macros da
   Extensão SIGEF.
3. **Nenhum endereço de célula no código Python.** Tudo em `config/cell_map.yaml`.
   Se precisar de uma célula que não está no mapa, adicione ao mapa.
4. **Não alterar layout da planilha**: não inserir/remover linhas ou colunas,
   não renomear abas fora do padrão `identificacao` / `perimetro_N`, não mexer em
   estilos.
5. **Domínios normativos** (tipos de vértice, métodos de posicionamento, tipos
   de limite) vivem em `config/dominios.json`. Não escrever essas listas
   inline no código, e não inventar códigos: se um valor não estiver no arquivo,
   pergunte.
6. **Dados pessoais** (CPF/CNPJ, nome do detentor, matrícula) só em memória
   durante o uso normal do app. Nunca logar, nunca mandar para serviço
   externo. Única exceção, deliberada: o arquivo de projeto `.sigefproj`
   (`core/projeto.py` + `ui/projeto.py`) que o profissional escolhe
   salvar/abrir por conta própria a qualquer momento — é a persistência
   oficial da ferramenta, nunca automática nem em segundo plano. Fora
   desse arquivo, a regra continua valendo sem exceção.

## Formatação exigida pelo SIGEF

- Vírgula como separador decimal, sem separador de milhar.
- UTM e sigmas (long/lat/h): 2 casas decimais.
- Altitude elipsoidal (h): 3 casas decimais — confirmado em planilha real
  preenchida (`config/dominios.json: limites_coordenadas.h_casas_decimais`),
  diferente do sigma apesar de os dois aparecerem juntos no manual.
- Geodésicas: `GG MM SS,sss W` e `GG MM SS,sss S` (3 casas nos segundos).
- Código do vértice: `CCCC-T-NNN` (credenciado, tipo, sequencial), letras
  maiúsculas. Ex.: `AJ4-M-9121`.
- Ao escrever uma célula, respeitar o `office:value-type` original dela.
- O dado de limite (tipo, confrontante) fica na linha do vértice de **ré** e
  descreve o segmento de **vante**. O último limite fecha no primeiro vértice.

## Arquitetura

```
app.py                  entrypoint Streamlit
core/template_loader.py download do modelo no GitHub + sha256 + cache + fallback
core/ods_writer.py      escrita e clonagem de abas de perímetro
core/ods_reader.py      reimportação de planilha preenchida
core/models.py          Pydantic: Identificacao, Perimetro, Vertice
core/validators/        formato.py e geometria.py
core/geo.py             pyproj / shapely
core/projeto.py         serialização do projeto .sigefproj (ver regra 6)
ui/grid.py              wrapper do AgGrid (única porta de entrada)
ui/projeto.py           gate inicial + salvar/abrir projeto (barra lateral)
ui/                     abas e painel de validação
importers/              fase posterior; interface em base.py
config/                 cell_map.yaml, dominios.json, theme_tokens.json
tools/                  inspect_template.py, extract_theme.py
tests/                  fixtures de 1 e 2 parcelas
```

Fronteiras que devem ser respeitadas:

- `core/` não importa `streamlit` nem `st_aggrid`. Deve rodar em teste puro.
- `ui/grid.py` é o único arquivo que conhece `streamlit-aggrid`. Nenhum outro
  módulo importa esse pacote — a ideia é poder trocar o componente mexendo em
  um arquivo só.
- Validadores não geram ODS; o gravador não valida. Cada um no seu papel.
- Toda validação devolve `Ocorrencia(severidade, aba, linha, campo, mensagem)`.

## Múltiplas parcelas

Uma aba de perímetro por parcela (`perimetro_1`, `perimetro_2`, ...), criadas por
`deepcopy` do `table:table` de `perimetro_1` no `content.xml`, com ajuste de
`table:name`. Cada parcela tem número único; todas as abas devem usar o mesmo
sistema de referência; os perímetros não podem se cruzar.

Vazio interno (campo `Lado` = Interno) está fora do escopo atual, mas o modelo
de dados já carrega o campo — não remova.

## Escopo da validação local

Implementado: campos obrigatórios, CPF/CNPJ, padrão e unicidade do código de
vértice, domínios de método e tipo de limite, sigma × tipo de limite
(0,50 / 3,00 / 7,50 m), limites de coordenada UTM por hemisfério, regra do
confrontante (CNS+matrícula e/ou descritivo), fechamento e simplicidade do
polígono, sentido horário, vértice inicial mais ao norte (desempate a oeste),
cruzamento entre perímetros.

Impossível offline (depende do banco do INCRA): existência do CNS, validade do
código de credenciado, sobreposição com parcela certificada, unicidade
posicional de vértice, município × malha IBGE. A interface precisa dizer isso;
nunca sugerir ao usuário que "sem erros" equivale a "vai certificar".

## Comandos

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
pytest -q
python tools/inspect_template.py    # dump de células do modelo
python tools/extract_theme.py       # styles.xml -> theme_tokens.json
```

Ambiente: macOS (Apple Silicon), Python 3.11+.

## Critério de aceite do gravador

Antes de considerar qualquer tarefa de escrita concluída: gerar uma planilha com
duas parcelas, abrir no LibreOffice com a Extensão SIGEF e rodar F3 sem erro.
Teste automatizado não substitui essa conferência.

## Como trabalhar neste repositório

- Antes de editar, leia apenas os arquivos realmente envolvidos na tarefa; evite
  varrer o repositório inteiro.
- Edições cirúrgicas, não reescritas de arquivo. Não refatore o que não foi
  pedido, não renomeie funções por estilo, não acrescente dependências sem
  perguntar.
- Não mexa em `templates/`: o ODS é o arquivo oficial e é imutável no repo.
- Ao alterar `cell_map.yaml` ou `dominios.json`, diga em uma linha o que mudou.
- Se o modelo oficial mudar de versão, a solução é um novo `cell_map`, não
  ajustes espalhados no código.
