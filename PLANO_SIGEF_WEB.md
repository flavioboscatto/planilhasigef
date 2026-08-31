# Gerador de Planilha SIGEF — Plano de Implementação

> **Histórico — superado.** Este plano descreve a v1 em Streamlit
> (`app.py`/`ui/`), removida do repositório após a migração completa para
> desktop nativo (PySide6/Qt, `app_qt.py`/`ui_qt/`). A camada `core/`
> (regras de negócio, geodésia, gravação do `.ods`) descrita aqui não
> mudou — as decisões de arquitetura de dados abaixo continuam válidas.
> Para a arquitetura e os comandos atuais, ver `CLAUDE.md`.

App web (Streamlit) que preenche a planilha eletrônica oficial do INCRA
(`sigef_planilha_modelo_1.4_rc5.ods`), sempre a partir do modelo versionado no
GitHub, com interface espelhando a planilha.

**Decisões da v1**

| Item | Decisão |
|---|---|
| Escopo | Múltiplas parcelas (N abas de perímetro) |
| Grade | `streamlit-aggrid` (fidelidade visual) |
| Validação local | Formato + geometria (sentido, vértice inicial, autointerseção) |
| Vazio interno (lado Interno) | Fora da v1 — arquitetura já preparada |

---

## 1. Premissas técnicas

- O SIGEF lê a planilha **por posição de célula**. Nada de gerar ODS do zero:
  sempre abrir o modelo oficial e escrever nas células de entrada.
- O modelo tem **uma aba de Identificação** e **uma ou mais abas de Perímetro**
  (`perimetro_1`, `perimetro_2`, ...).
- As células de rótulo estão bloqueadas para edição, e o pacote ODS carrega as
  macros da Extensão SIGEF (validação F3, botão de município). Reescrever o ODS
  inteiro com uma biblioteca de alto nível destrói isso.
- **Regra de ouro do gravador:** abrir o `.ods` como ZIP, alterar apenas o
  `content.xml`, e regravar todas as demais entradas byte a byte.

## 2. Estrutura do repositório

```
sigef-web/
├── app.py                       # entrypoint Streamlit
├── requirements.txt
├── templates/
│   ├── sigef_planilha_modelo_1.4_rc5.ods
│   └── manifest.json            # versão, URL de origem, data, sha256
├── config/
│   ├── cell_map.yaml            # campo -> (aba, célula)
│   ├── dominios.json            # tipos de vértice, métodos, tipos de limite
│   └── theme_tokens.json        # cores extraídas do styles.xml do modelo
├── core/
│   ├── template_loader.py       # download + hash + cache + fallback
│   ├── ods_writer.py            # escrita ZIP/content.xml, clonagem de abas
│   ├── ods_reader.py            # reimportação de planilha preenchida
│   ├── models.py                # Pydantic: Identificacao, Perimetro, Vertice
│   ├── validators/
│   │   ├── formato.py
│   │   └── geometria.py
│   └── geo.py                   # pyproj / shapely
├── ui/
│   ├── grid.py                  # wrapper AgGrid (interface trocável)
│   ├── aba_identificacao.py
│   ├── aba_perimetro.py
│   └── painel_validacao.py
├── importers/                   # fase 4
│   ├── base.py                  # Importer.parse(file) -> DataFrame padrão
│   └── ...
├── tools/
│   ├── inspect_template.py      # dump de células/estilos do ODS
│   └── extract_theme.py         # styles.xml -> theme_tokens.json
└── tests/
    ├── fixtures/
    └── test_roundtrip.py
```

**Dependências:** `streamlit`, `streamlit-aggrid`, `lxml`, `pydantic`,
`pyproj`, `shapely`, `pyyaml`, `requests`. Versões fixadas.

## 3. Etapas

### Etapa 0 — Modelo versionado

1. Baixar o ODS oficial de <https://sigef.incra.gov.br/documentos/> e commitar
   em `templates/` junto com `manifest.json` (sha256, URL, data).
2. `template_loader.load()`: busca no `raw.githubusercontent`, confere o hash,
   `st.cache_resource`; se a rede falhar, usa a cópia local do pacote.
3. GitHub Action semanal: baixa o ODS do INCRA, compara o hash e abre uma issue
   se o modelo mudar de versão.

*Aceite:* o app roda offline e online, e loga qual versão do modelo carregou.

### Etapa 1 — Mapa de células

1. `tools/inspect_template.py`: descompacta o ODS, percorre o `content.xml`
   expandindo `table:number-columns-repeated` / `number-rows-repeated`, e emite
   um CSV com aba, endereço, texto, `office:value-type` e nome do estilo.
2. A partir desse dump, escrever `cell_map.yaml` à mão, cobrindo:
   - **identificacao**: natureza do serviço; tipo pessoa, nome, CPF/CNPJ;
     denominação, situação, natureza da área, código do imóvel (SNCR), CNS,
     matrícula, municípios.
   - **perimetro_N**: denominação, parcela número, lado, tipo de coordenada,
     meridiano central, hemisfério, linha inicial e colunas da tabela de
     vértices/limites (código, E/Long, N/Lat, sigma long, sigma lat, h,
     sigma h, método de posicionamento, tipo de limite, CNS, matrícula,
     descritivo).
3. Nenhum endereço de célula fica no código Python — só no YAML. Troca de versão
   do modelo = troca do mapa.

*Aceite:* teste que valida o mapa contra o ODS (todo rótulo esperado bate).

### Etapa 2 — Gravador ODS

1. `ods_writer.write(dados) -> bytes`:
   - abre o template com `zipfile`, parseia só o `content.xml` com lxml;
   - escreve cada valor respeitando o `office:value-type` original da célula e
     o `text:p`;
   - regrava todas as outras entradas do ZIP sem tocar (mimetype primeiro, sem
     compressão, como manda o ODF).
2. **Clonagem de aba** (chave para múltiplas parcelas): `deepcopy` do
   `table:table` `perimetro_1`, renomear para `perimetro_2..N`, ajustar
   `table:name` e quaisquer referências internas, inserir na ordem correta.
3. Formatação de saída, sempre como o manual exige:
   - vírgula decimal, sem separador de milhar;
   - UTM, sigmas e h com 2 casas;
   - geodésicas como `GG MM SS,sss W` / `GG MM SS,sss S`.
4. **Droplist nas células de domínio.** No modelo oficial, a coluna Tipo
   Limite (`perimetro_N!I`) usa uma `table:content-validation` sem
   `condition` estática — a lista real é montada em tempo de execução pela
   macro da Extensão SIGEF, não está no `content.xml`. Como o gravador não
   roda a macro, toda célula de Método de Posicionamento e de Tipo de
   Limite que não vier de importação (dado ainda não preenchido, ou editado
   à mão depois de gerado) precisa ganhar sua própria
   `table:content-validation` com `of:cell-content-is-in-list(...)`,
   construída a partir de `dominios.json` (ver Anexo — Domínios
   normativos), para que abrir o arquivo no LibreOffice mostre um droplist
   de verdade em vez de texto livre.

*Aceite (marco crítico do projeto):* gerar uma planilha de duas parcelas, abrir
no LibreOffice com a Extensão SIGEF, rodar F3 e não obter erro. Só depois disso
faz sentido investir na interface.

**✅ Passou.** Usuário testou no LibreOffice com a Extensão SIGEF e confirmou
F3 sem erro — inclusive nos campos de droplist (Situação, Natureza da Área,
Hemisfério, Tipo de Coordenada, Lado, Tipo Pessoa, Natureza do Serviço), que
usam controle de formulário (`form:listbox`), não só o texto da célula (ver
Etapa 2, item 4, e a nota sobre clonagem de aba). O gravador com N parcelas
está validado ponta a ponta — o projeto passou do ponto onde "morre ou vive".

### Etapa 3 — Modelo de dados e validação

`models.py` com Pydantic: `Identificacao`, `Perimetro` (denominação, número,
lado, sistema de coordenadas, MC, hemisfério, lista de vértices), `Vertice`
(código, coordenadas, sigmas, h, método, tipo de limite de vante, confrontante).

**validators/formato.py**
- campos obrigatórios (exceções: SNCR, CNS e matrícula conforme o tipo de área);
- CPF/CNPJ (dígitos verificadores);
- padrão do código do vértice `CCCC-T-NNN`, com `T` ∈ tipos de vértice;
- unicidade do código de vértice dentro da aba;
- método de posicionamento e tipo de limite pertencentes aos domínios do
  MT-GIR (`dominios.json`, versionado — códigos no Anexo — Domínios
  normativos);
- sigma resultante × tipo de limite: 0,50 m (artificial), 3,00 m (natural),
  7,50 m (inacessível);
- confrontante: CNS e matrícula juntos, ou descritivo, ou ambos;
- limites de coordenada UTM por hemisfério;
- coerência entre abas: mesmo sistema de referência, `parcela número` único.

**validators/geometria.py** (shapely + pyproj)
- polígono fechado e simples (sem autointerseção);
- sentido horário;
- primeiro vértice o mais ao norte, desempate pelo mais a oeste;
- perímetros de abas diferentes não podem se cruzar;
- área e perímetro calculados, exibidos para conferência (não vão para o ODS).

Saída padronizada: `Ocorrencia(severidade, aba, linha, campo, mensagem)`, que
alimenta o painel lateral e o realce na grade.

*Fora da v1 (dependem do banco do INCRA):* existência do CNS, código de
credenciado válido, sobreposição com parcela certificada, unicidade posicional,
município × malha IBGE. O painel deve dizer isso explicitamente, para o usuário
não confundir "sem erros aqui" com "vai certificar".

### Etapa 4 — Interface

**Estado real (adiantado nesta rodada, fora da ordem original do plano — o
usuário pediu pra ver a interface antes do gravador estar 100% validado):**

- `st.segmented_control`, não `st.tabs`: `st.tabs` manda o conteúdo de
  todas as abas pro navegador de uma vez e só esconde a inativa por CSS —
  qualquer componente que meça o próprio tamanho ao montar (era o caso do
  AG-Grid) nasce com largura zero dentro da aba escondida e nunca corrige.
  `segmented_control` dispara um rerun de verdade a cada troca, então só a
  seção visível é montada.
- Grade de vértices: **`st.data_editor`, não `streamlit-aggrid`**. Colar um
  bloco de células (várias de uma vez, do Excel/LibreOffice) só existe na
  versão paga (Enterprise) do AG-Grid — sem aviso nenhum, o grid options
  correspondente simplesmente não faz nada. `st.data_editor` é nativo do
  Streamlit, sem custo, já suporta colar bloco de fábrica, e não tem o
  problema de largura zero (não é um iframe). Perde a fidelidade visual
  total à planilha original que o AG-Grid prometia — decisão tomada com o
  usuário depois de confirmar o bloqueio do Enterprise na prática.
  `ui/grid.py` continua sendo o único arquivo que conhece o componente.
- N parcelas: `perimetro_1..N`, cada uma com denominação/número/lado/tipo de
  coordenada/meridiano/hemisfério + grade própria, mais botões "+ Adicionar
  aba Perímetro" / "- Remover última parcela". "Duplicar" não foi pedido,
  não implementado.
- Todos os widgets de uma parcela usam `key=f"..._{indice}"` — sem isso,
  trocar de parcela faz os campos de uma vazarem pra outra (mesma chave de
  session_state por causa do mesmo rótulo).
- Formulário de identificação em 2 colunas por seção (Detentor, Área) —
  pedido do usuário pra caber mais campo sem rolar tanto.
- Botão "↻ Reorganizar (mais ao norte, sentido horário)" — adiantado da
  Etapa 3: `core/validators/geometria.py` já tem
  `reordena_norte_horario(vertices)`, mas só isso; fechamento,
  autointerseção e cruzamento entre abas continuam pendentes.
- `core/parsing.py`: conversão tolerante texto → número (`parse_numero`) e
  texto → grau decimal aceitando GMS com espaço (`parse_coordenada`) — a
  grade grava tudo como texto livre, essa conversão só acontece ao montar o
  `Vertice`. Reaproveitado pelo importador (abaixo).

**Ainda não implementado desta lista original:**

1. Realce vermelho/amarelo por célula (depende de `Ocorrencia`, Etapa 3
   ainda não feita).
2. Painel de validação lateral.
3. Persistência de projeto em JSON (salvar/recarregar sessão).

### Etapa 4b — Aparência igual à planilha original (feito, com limite real)

`tools/extract_theme.py` lê `office:automatic-styles` do `content.xml` do
modelo (as cores de célula ficam ali, não em `styles.xml` — isso é fácil
de confundir) e gera `config/theme_tokens.json` com as cores reais de cada
seção da planilha: Serviço (vinho `#422525`), Detentor (azul `#353d71`),
Área/Perímetro (verde `#345b3a`), Confrontante (azul médio `#4e5791`), com
a variante clara de cada uma pras células de entrada. O dicionário
`PAPEIS` no topo do script mapeia papel semântico → nome do estilo
(`ce1`, `ce4`...) conferido célula a célula no dump do
`tools/inspect_template.py` — se a próxima versão do modelo trocar os
nomes de estilo, é só atualizar esse dicionário.

Aplicado em dois lugares:
- `.streamlit/config.toml`: tema global do Streamlit (`primaryColor` e
  `secondaryBackgroundColor` na família verde Área/Perímetro, a mais
  recorrente) — afeta botão primário, `st.data_editor` e widgets em geral.
- `ui/tema.py` (`titulo_secao`): banner HTML com a cor exata de cada
  título de seção (Identificação do Serviço/Detentor/Área, Tabela de
  Perímetro), testado e conferido pixel a pixel (RGB extraído bate com o
  hex do modelo).

**Limite real, não escondido:** `st.data_editor` desenha a grade num
canvas — não existe seletor CSS que alcance dentro dele. O cabeçalho da
grade pega cor pelo tema global, não célula a célula como no modelo
(a coluna Tipo Limite/CNS/Matrícula/Descritivo não sai com o azul
diferente do resto). Os rótulos de campo individuais (que na planilha
original também são barras coloridas, tipo "Nome:") continuam com o
estilo padrão do Streamlit — colorir cada um exigiria abrir mão dos
widgets nativos (rótulo virar HTML solto por cima de cada input), trocado
não foi feito porque o ganho visual não parecia valer a complexidade a
mais nesta rodada.

### Etapa 6b — Importador de vértices (adiantado da Etapa 6, TXT/CSV)

Pedido do usuário: nem sempre os dados vêm num arquivo só (às vezes só
coordenadas, às vezes só precisões), sempre casando pelo código do vértice.

- `importers/delimitado.py`: lê TXT/CSV com separador escolhido (vírgula,
  ponto e vírgula, tabulação, espaço, barra vertical, ou "Outro" com campo
  livre) — devolve um DataFrame cru, colunas como vieram do arquivo.
- `ui/importar_vertices.py`: upload → escolha de separador → prévia (5
  linhas) → correlação manual de cada coluna do arquivo para um campo do
  vértice (ou "ignorar") → botão aplicar.
- `core/importacao.py` (`mesclar_por_codigo`): casa pelo código; um campo
  presente e não vazio no arquivo **sempre sobrescreve** o que já estava
  (decisão do usuário: "o mais recente vence"); campo ausente/vazio no
  arquivo não apaga dado existente; código que não existe na tabela vira
  linha nova automaticamente, respeitando o limite de vértices da parcela
  (o que não couber fica de fora, com aviso).
- Uma importação de cada vez (upload → aplica → session_state atualiza →
  novo upload pra próximo arquivo), não simultânea.
- Só TXT/CSV delimitado por enquanto — XLSX, ODS SIGEF reimportado, DXF,
  KML/KMZ, SHP/GPKG continuam na Etapa 6 original, não iniciados.
- Separador decimal do arquivo importado (ponto) é normalizado pra vírgula
  (`core/parsing.normaliza_decimal`) antes de mesclar — mesma regra da
  grade, ver Etapa 4c.

### Etapa 4c — Ajustes vindos da conferência com a planilha real preenchida

O usuário mandou um `.ods` preenchido de verdade pra comparar. Achados:

- **Formato de E/Long e N/Lat já estava certo**: o modelo grava
  `"48 32 28,781 W"` / `"27 35 39,554 S"` — exatamente o que
  `core/parsing._fmt_geografica` já produzia. Nada a mudar aí.
- **Separador decimal sempre vírgula, inclusive na grade** (não só no
  `.ods` final): `core/parsing.normaliza_decimal` troca ponto por vírgula
  entre dígitos; aplicado depois de cada edição na grade
  (`ui/aba_perimetro._normaliza_tabela`) e depois de mesclar uma
  importação. Limitação conhecida: não distingue separador de milhar
  brasileiro (`1.234,56` vira `1,234,56`) — improvável nos campos de
  coordenada/sigma, que não usam milhar, então não tratado.
- **Meridiano Central virou dropdown**, só com os 8 valores válidos pro
  Brasil (múltiplos de 6°, fusos UTM 18 a 25S):
  `-75, -69, -63, -57, -51, -45, -39, -33` — lista em
  `dominios.json.meridianos_centrais_brasil`, padrão `-63`.
- **Cor nas células de dado da tabela de vértices**: pedido de deixar a
  grade com a cara da planilha (célula colorida por grupo de coluna, não
  só o banner de título). Problema real: `st.data_editor` (editável) não
  aceita `pandas.Styler` — só `st.dataframe` (só leitura) aceita. Solução
  adotada: uma prévia só-leitura colorida (`ui.grid.render_vertices_preview`)
  logo abaixo da grade editável, usando as mesmas cores de
  `theme_tokens.json` por grupo de coluna (vértice/coordenadas/sigma/método
  em um tom, confrontante — tipo limite/CNS/matrícula/descritivo — em
  outro). Eu não consegui verificar visualmente pixel a pixel na sessão em
  que construí (a grade usa shadow DOM fechado, e a ferramenta de
  screenshot não cooperou) — **usuário conferiu na tela e confirmou que as
  cores saíram corretas.** Considerar definitivo, não mais experimental.

### Futuro próximo — Conversão UTM → Geodésicas

Hoje o app só aceita o que o usuário digita: se o dado de campo vem em
UTM, é UTM que entra nas células (sem reprojeção). O usuário tem um motor
geodésico próprio em Python, já calibrado pras conversões oficiais no
Brasil (SIRGAS2000), e quer poder subir dados em UTM e o programa
converter pra Geográfica automaticamente (ou vice-versa), em vez de
obrigar sempre o mesmo sistema de coordenada de entrada.

Não implementado agora — fica para uma rodada futura, depois do
importador/validação estarem mais maduros. Quando entrar:
- Provável lugar: `core/geo.py` (já reservado na estrutura do repositório
  para pyproj/shapely), ou um módulo dedicado se o motor do usuário tiver
  lógica própria a preservar em vez de recalcular via pyproj.
- Precisa decidir: a conversão roda automaticamente ao trocar
  "Tipo de Coordenada", ou só quando o usuário pedir explicitamente (um
  botão "Converter"), já que reprojeção muda o dado e não deveria
  acontecer de forma silenciosa.
- CLAUDE.md já lista `pyproj` como dependência prevista — o motor do
  usuário pode substituir isso ou rodar em paralelo pra conferência.

### Etapa 5 — Deploy

- Streamlit Community Cloud ou Docker; nada persistido em disco.
- CPF, matrícula e nome do detentor só em memória; sem log desses campos.
- `pytest` com fixtures de planilhas de 1 e 2 parcelas; CI gerando um ODS de
  teste a cada commit.

### Etapa 6 — Importação (posterior)

`importers/base.py` define `Importer.parse(file) -> DataFrame` no schema padrão.
Adaptadores independentes, um por formato: TXT/CSV delimitado, XLSX, ODS SIGEF
já preenchido (reimportação, reaproveita o `ods_reader`), DXF (ezdxf), KML/KMZ,
SHP/GPKG (geopandas), CSV exportado do próprio SIGEF. Sobre eles, um assistente
de mapeamento de colunas, reprojeção e reordenação automática (horário, a partir
do extremo norte).

## 4. Ordem de ataque sugerida

1. Etapa 0 + 1 + 2 até o F3 passar com duas parcelas. É aqui que o projeto
   morre ou vive.
2. Etapa 3 (validação), ainda em linha de comando, com fixtures.
3. Etapa 4 (UI), que passa a ser só uma casca sobre código já testado.
4. Deploy e, por último, importadores.

## 5. Anexo — Domínios normativos (Manual Técnico de Georreferenciamento)

Fonte: *Manual Técnico para o Georreferenciamento de Imóveis Rurais* — INCRA,
2ª Edição (MT-GIR). Estas são as listas que alimentam `config/dominios.json`;
nenhum código abaixo deve ser digitado solto no código Python (regra 5 do
`CLAUDE.md`) — se um valor não estiver aqui, não inventar, perguntar.

No modelo oficial, o droplist da coluna Tipo Limite (`perimetro_N!I`) é
montado em tempo de execução pela macro da Extensão SIGEF (o
`table:content-validation` correspondente no `content.xml` não tem
`condition` estática — ver Etapa 2, item 4). Por isso essas listas precisam
existir de forma independente em `dominios.json`, tanto para validação
quanto para o gravador recriar o droplist nas células que não vierem de
importação.

### Tipos de vértice (Tabela 2 do manual)

| Código | Tipo |
|---|---|
| `M` | Marco — posicionamento direto, materializado em campo |
| `P` | Ponto — posicionamento direto, não materializado |
| `V` | Virtual — posicionamento indireto |

Usado no `T` do código do vértice `CCCC-T-NNN`.

### Tipos de limite (Tabela 1 do manual)

| Código | Tipo | Natureza |
|---|---|---|
| `LA1` | Cerca | Artificial |
| `LA2` | Muro | Artificial |
| `LA3` | Estrada | Artificial |
| `LA4` | Vala | Artificial |
| `LA5` | Canal | Artificial |
| `LA6` | Linha ideal | Artificial |
| `LA7` | Limite artificial não tipificado | Artificial |
| `LN1` | Corpo d'água ou curso d'água | Natural |
| `LN2` | Linha de cumeada | Natural |
| `LN3` | Grota | Natural |
| `LN4` | Crista de encosta | Natural |
| `LN5` | Pé de encosta | Natural |
| `LN6` | Limite natural não tipificado | Natural |

A natureza (Artificial/Natural) do limite é o que define o sigma exigido:
0,50 m para artificial, 3,00 m para natural (regra já em `CLAUDE.md`); o
manual também prevê sigma de 7,50 m para vértice em limite inacessível, que
não tem código de tipo próprio nesta tabela — é uma condição do
posicionamento (métodos `PS*`/`PB*`, ver abaixo), não do limite em si.

### Métodos de posicionamento (Tabelas 5, 6 e 7 do manual)

| Código | Método | Aplicável a limite (Tabela 6) | Aplicável a tipo de vértice (Tabela 7) |
|---|---|---|---|
| `PG1` | Relativo estático | Artificial ou Natural | M, P |
| `PG2` | Relativo estático-rápido | Artificial ou Natural | M, P |
| `PG3` | Relativo semicinemático | Artificial ou Natural | M, P |
| `PG4` | Relativo cinemático | Artificial ou Natural | P |
| `PG5` | Relativo a partir de códigos | Natural | P |
| `PG6` | RTK convencional / RTPPP | Artificial ou Natural | M, P |
| `PG7` | RTK em rede | Artificial ou Natural | M, P |
| `PG8` | Differential GPS (DGPS) | Natural | P |
| `PG9` | Posicionamento por Ponto Preciso | Artificial ou Natural | M, P |
| `PT1` | Poligonação | Artificial ou Natural | M, P |
| `PT2` | Triangulação | Artificial ou Natural | M, P |
| `PT3` | Trilateração | Artificial ou Natural | M, P |
| `PT4` | Triangulateração | Artificial ou Natural | M, P |
| `PT5` | Irradiação | Artificial ou Natural | M, P |
| `PT6` | Interseção linear | Artificial ou Natural | M, P, V |
| `PT7` | Interseção angular | Artificial ou Natural | M, P, V |
| `PT8` | Alinhamento | Artificial ou Natural | M, P |
| `PT9` | Estação Livre | Artificial ou Natural | M, P |
| `PA1` | Paralela | Artificial ou Natural | V |
| `PA2` | Interseção de Retas | Artificial ou Natural | V |
| `PA3` | Projeção Técnica | Artificial ou Natural | V |
| `PS1` | Aerofotogrametria | Artificial¹, Natural ou Inacessível | V |
| `PS2` | Radar aerotransportado | Artificial¹, Natural ou Inacessível | V |
| `PS3` | Laser scanner aerotransportado | Artificial¹, Natural ou Inacessível | V |
| `PS4` | Sensores orbitais | Artificial², Natural ou Inacessível | V |
| `PB1` | Base cartográfica com precisão conhecida | Artificial¹, Natural ou Inacessível | V |
| `PB2` | Base cartográfica sem precisão conhecida | Artificial², Natural ou Inacessível | V |

¹ Com exceção de vértices tipo M. ² Com exceção de vértices tipo M e
limites por cerca.

`PG1`–`PG9` e `PT1`–`PT4` também aparecem na Tabela 5 (vértices de apoio,
que não entram na planilha SIGEF — são referência para o levantamento, não
campo do formulário). O `dominios.json` só precisa da lista de vértice de
**limite** (Tabelas 6 e 7 acima).

A validação cruzada método × tipo de vértice e método × tipo de limite
(colunas 3 e 4 da tabela acima) é candidata a regra extra em
`validators/formato.py` na Etapa 3, além do que já está listado — hoje o
plano só previa checar se o código pertence ao domínio, não a
compatibilidade entre as duas colunas.
