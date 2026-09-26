# CLAUDE.md — sigef-web

App desktop nativo (PySide6/Qt) que preenche a planilha eletrônica oficial
do INCRA (`sigef_planilha_modelo_1.4_rc5.ods`) para certificação no SIGEF.
Responda e comente o código em português do Brasil.

Era um app Streamlit (`app.py`/`ui/`) até a migração pra desktop nativo —
removido do repositório depois que o Qt foi validado ponta a ponta
(`PLANO_SIGEF_WEB.md` documenta esse plano original, hoje histórico). Este
arquivo traz só o que você precisa saber para não quebrar nada.

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
   (`core/projeto.py` + `ui_qt/projeto_qt.py`, menu Arquivo em `app_qt.py`)
   que o profissional escolhe salvar/abrir por conta própria a qualquer
   momento — é a persistência oficial da ferramenta, nunca automática nem
   em segundo plano. Fora desse arquivo, a regra continua valendo sem
   exceção.

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
app_qt.py                    entrypoint (QApplication/QMainWindow) — menus (Arquivo/
                              Importar/Exportar/Gerenciar Parcelas/Gerenciar Planilha
                              (Parcela atual)), toolbar de ícones (Novo/Abrir/Salvar/
                              Salvar Como/Desfazer), abas (Identificação + parcelas)
core/template_loader.py      carrega o modelo local + sha256 (cache em memória)
core/ods_writer.py           escrita e clonagem de abas de perímetro
core/tabela_vertices.py      conversão DataFrame <-> Vertice (Pydantic); coluna
                              "pt_original" (ajuda de tela, nunca vai pro ODS)
core/importacao.py           mesclar_por_codigo (importação de vértices, casa por
                              Pt.Original antes do código — sobrevive à renumeração)
core/numeracao.py            renumerar_parcelas, atualizar_tipos_parcelas
core/parsing.py              parse de número/coordenada/CPF-CNPJ tolerante a formato
core/formatacao_vertices.py  formata vértices igual à planilha final (GMS, casas
                              decimais) — reaproveitado por exportacao_txt/relatorio_docx
core/exportacao_txt.py       exporta a Tabela de Perímetro em TXT (colunas oficiais)
core/exportacao_xlsx.py      exporta a Tabela de Perímetro em XLSX (mesmas colunas,
                              uma aba por parcela) — não confundir com core/ods_writer.py
core/exportacao_kml.py       exporta o projeto em KML — um Folder (camada) por parcela,
                              polígono do perímetro + um Placemark de ponto por vértice
core/exportacao_shapefile.py exporta o projeto em Shapefile (pyshp) — pontos (vértices,
                              todos os atributos da planilha + área SGL) e polígonos
                              (perímetro por parcela), zipados; SIRGAS2000 (EPSG:4674)
core/relatorio_docx.py       gera o Relatório em DOCX (identificação + por parcela:
                              resumo, importações, planilha em página paisagem)
core/models.py               Pydantic: Identificacao, Perimetro, Vertice
core/validators/geometria.py reordena_norte_horario (usado por "Reorganizar") e
                              verificar_autointersecao (V3, via shapely)
core/geo.py                  pyproj (conversão UTM <-> Geodésica e o inverso,
                              Geodésica -> UTM, usado só pra desenhar a parcela)
core/sgl.py                  área/distância/perímetro no Sistema Geodésico Local do
                              INCRA (Manual Técnico de Posicionamento, cap. 9) — só
                              `math`, sem pyproj/shapely (ver docstring do módulo)
core/projeto.py              serialização do projeto .sigefproj (ver regra 6)
ui_qt/vertices_table.py      grade de vértices (QTableView) — única porta de
                              entrada pra essa grade; nenhum outro módulo a redesenha.
                              Freeze panes das 4 primeiras colunas (Pt.Original/Renum./
                              Tipo/Código): TabelaVerticesView.painel_congelado é uma
                              segunda instância da mesma classe (padrão "Frozen Column"
                              do próprio Qt — QTableView não congela coluna nativamente)
ui_qt/visualizar_parcela_dialog.py  diálogo "Visualizar parcela" (V3): desenho
                              nativo Qt (QGraphicsView, zoom no scroll + pan por
                              arraste) dos vértices + polilinha + área SGL/INCRA
ui_qt/perimetro_tab.py       aba de uma parcela: cabeçalho + grade + sub-abas de importação
ui_qt/importacao_tab.py      sub-aba "Importação N" persistente dentro da parcela —
                              colunas extras só-leitura com o valor original (UTM E/N
                              ou texto geodésico não-decimal) antes da conversão
ui_qt/importar_vertices_dialog.py  diálogo de importação de arquivo (TXT/CSV)
ui_qt/remover_parcela_dialog.py  diálogo "Remover parcela" (V4): lista com caixa de
                              marcação, remove uma ou várias parcelas de uma vez
ui_qt/boas_vindas_dialog.py  tela de abertura (V4): Novo projeto/Abrir/Recentes,
                              mostrada logo após a splash (app_qt.py::main)
ui_qt/preferencias_qt.py     projetos recentes via QSettings (V4) — fora de core/
                              (não importa PySide6) e fora de config/ (não é domínio)
ui_qt/identificacao_tab.py   aba Identificação
ui_qt/renumeracao_panel.py   painel de numeração (faixa acima das abas) + botões em 3
                              fileiras: 1) Importar + Adicionar/Remover parcela;
                              2) Exportar KML/Shapefile (azul) + Limpar Parcela (rosa) +
                              Desfazer; 3) Exportar SIGEF .ods/.txt/.xlsx/.docx (marrom).
                              Adicionar/Remover/Limpar Parcela só expostos aqui,
                              conectados em app_qt.py
ui_qt/relatorio_qt.py        recolhe dados das abas ao vivo pro core/relatorio_docx.py
ui_qt/projeto_qt.py          monta/aplica o projeto .sigefproj a partir da janela,
                              inclusive qual aba/sub-aba estava aberta ao salvar e o
                              nome customizado de cada aba de parcela (V4)
ui_qt/tema_qt.py             cores do modelo oficial (config/theme_tokens.json) em Qt;
                              icone() (qtawesome) — ícones vetoriais dos botões, no lugar
                              de emoji no texto (nomes "fa5s.xxx"/"mdi.xxx")
ui_qt/estilo_qt.py           folha de estilo (QSS) global do app
importers/delimitado.py      leitura de arquivo TXT/CSV pra importação
importers/planilha.py        leitura de planilha XLS/XLSX/ODS pra importação (V5) —
                              mesma sistemática de delimitado.py, DataFrame cru
config/                      cell_map.yaml, dominios.json, theme_tokens.json, municipios.json
assets/icone_app.ico         ícone do app (barra de título/tarefas e do .exe)
assets/abertura.png          imagem da splash screen (app_qt.py::main, ~3s na abertura)
tools/                       inspect_template.py, extract_theme.py, gerar_icone.py
sigef_qt.spec                empacotamento PyInstaller (.exe onefile, sem console)
tests/                       um arquivo de teste por módulo de ui_qt/ + core/
```

Fronteiras que devem ser respeitadas:

- `core/` não importa `PySide6`. Deve rodar em teste puro (`pytest-qt` só
  entra nos testes de `ui_qt/`, nunca em `core/`).
- `ui_qt/vertices_table.py` é o único arquivo que desenha a grade de
  vértices. Nenhum outro módulo cria um `QTableView`/`QAbstractTableModel`
  próprio pra isso — evita duas implementações divergentes da mesma grade.
- Validadores não geram ODS; o gravador não valida. Cada um no seu papel.

## Múltiplas parcelas

Uma aba de perímetro por parcela (`perimetro_1`, `perimetro_2`, ...), criadas por
`deepcopy` do `table:table` de `perimetro_1` no `content.xml`, com ajuste de
`table:name`. Cada parcela tem número único; todas as abas devem usar o mesmo
sistema de referência; os perímetros não podem se cruzar.

Vazio interno (campo `Lado` = Interno) está fora do escopo atual, mas o modelo
de dados já carrega o campo — não remova.

## Escopo da validação local

Nenhuma validação de conteúdo com aviso/erro por linha está implementada
hoje — era o plano original (`PLANO_SIGEF_WEB.md`), mas nunca foi
construída (nem na versão Streamlit — `core/validators/geometria.py` já
dizia isso no próprio docstring antes da migração). O que existe de fato:

- domínios (tipo de vértice, método de posicionamento, tipo de limite)
  restritos por combo — não dá pra digitar um código fora da lista;
- máscara progressiva de CPF/CNPJ (`core/parsing.py::formatar_cpf_cnpj`) —
  só formata a pontuação, não confere dígito verificador;
- `core/validators/geometria.py::reordena_norte_horario` — reordena a
  pedido do usuário (botão "Reorganizar"), não valida nem avisa sozinho;
- `core/validators/geometria.py::verificar_autointersecao` (V3) — detecta
  lados do perímetro que se cruzam ("borboleta"), via shapely, só
  topológico (grau decimal cru, sem projeção — ver docstring da função pro
  porquê disso ser válido). Chamada depois de "Reorganizar" (avisa, não
  bloqueia) e dentro do diálogo "Visualizar parcela"
  (`ui_qt/visualizar_parcela_dialog.py`, desenha o lado problemático em
  vermelho). Devolve `Cruzamento(indice_a, indice_b, mensagem)`, não o
  `Ocorrencia` abaixo — aquele é pra problema de uma célula, isto é uma
  relação entre dois lados.

Ainda não implementado: padrão/unicidade do código de vértice, sigma ×
tipo de limite (0,50 / 3,00 / 7,50 m), limites de coordenada UTM por
hemisfério, regra do confrontante (CNS+matrícula e/ou descritivo),
fechamento do polígono, cruzamento entre perímetros/parcelas (autointerseção
DENTRO de um perímetro já existe, ver acima). Se for construir isso,
`Ocorrencia(severidade, aba, linha, campo, mensagem)` era o formato de
retorno planejado — não existe ainda no código.

Impossível offline (depende do banco do INCRA), mesmo depois de
implementado o resto: existência do CNS, validade do código de
credenciado, sobreposição com parcela certificada, unicidade posicional de
vértice, município × malha IBGE. A interface precisa dizer isso; nunca
sugerir ao usuário que "sem erros" equivale a "vai certificar".

## Área no Sistema Geodésico Local (SGL/INCRA)

`core/sgl.py` (V3) implementa área/distância/perímetro conforme o Manual
Técnico de Posicionamento (cap. 9) — geodésicas ⇄ geocêntricas ⇄
cartesianas locais (e, n, u), área pela fórmula de Gauss. Mostrado no
diálogo "Visualizar parcela" (`ui_qt/visualizar_parcela_dialog.py`), só
quando o perímetro não tem autointerseção.

Desvio deliberado do Manual (item 9.2 do documento de especificação, a
pedido do usuário): a norma manda **recusar** vértice sem altitude
elipsoidal em vez de assumir `h=0`, mas a grade deste app não distingue
"célula de h vazia" de "usuário digitou 0" (mesmo comportamento de toda
coluna numérica — ver `core/tabela_vertices.py`), e parcelas litorâneas
podem ter `h` genuinamente perto de zero. `area_sgl` calcula com o `h`
que vier, sem bloquear por `h=0` — ver docstring do módulo.

`azimute_puissant` está com `NotImplementedError` explícito de propósito:
a especificação fornecida não trazia a fórmula fechada de Puissant, e
azimute errado é pior que a função ausente.

## Comandos

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python app_qt.py
pytest -q
python tools/inspect_template.py    # dump de células do modelo
python tools/extract_theme.py       # styles.xml -> theme_tokens.json
python tools/gerar_icone.py         # placeholder de assets/icone_app.ico
pyinstaller sigef_qt.spec --noconfirm   # gera dist/PlanSIGEF.exe (onefile)
```

Ambiente: Windows, Python 3.11+.

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
