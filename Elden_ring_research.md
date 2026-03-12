# Arquitetura de Engenharia de Dados e Engenharia Reversa para Monitoramento em Tempo Real de Elden Ring v1.12+ no Ambiente Linux

A análise técnica de sistemas de persistência de dados em títulos da FromSoftware, especificamente sob o motor SoulsTech, exige uma compreensão profunda de estruturas binárias proprietárias, protocolos de integridade e a complexa interatividade entre o estado do mundo e os identificadores de eventos. No contexto de Elden Ring v1.12 e sua expansão, _Shadow of the Erdtree_, a arquitetura do arquivo de salvamento `ER0000.sl2` representa o ápice de décadas de refinamento iterativo pela desenvolvedora, consolidando informações de progresso global, inventários dinâmicos e coordenadas posicionais em um contêiner binário densamente compactado. O desenvolvimento de um dashboard em tempo real utilizando Python e Streamlit em um ambiente Linux, como o Pop!_OS via Proton, impõe desafios de engenharia que vão desde a navegação em sistemas de arquivos virtuais até a recomputação de somas de verificação MD5 para garantir que a leitura dos dados não seja interpretada pelo sistema como uma corrupção de arquivo.   

## Anatomia e Arquitetura Binária do Arquivo ER0000.sl2

O arquivo `ER0000.sl2` é a espinha dorsal de toda a experiência de persistência em Elden Ring. Ao contrário de formatos de salvamento baseados em texto ou bancos de dados relacionais simples, a FromSoftware utiliza um formato de slot fixo, onde cada um dos dez slots de personagem possíveis ocupa uma partição idêntica no arquivo, independentemente do tempo de jogo ou da quantidade de itens coletados. Essa previsibilidade estrutural é o que permite a engenheiros reversos identificar offsets de memória com alta precisão, mesmo após atualizações significativas do jogo, como a v1.12.   

### Organização de Slots de Personagem e Metadados

A estrutura do arquivo é dividida em um cabeçalho global e seções de slots individuais. Cada slot é precedido por uma assinatura de integridade (checksum) que valida os dados subsequentes. A precisão na identificação desses endereços é o primeiro passo para qualquer parser binário robusto, especialmente quando o objetivo é a extração de métricas de progresso em tempo real.   

|Elemento Estrutural|Offset de Início (Hex)|Comprimento (Bytes)|Função Técnica|
|---|---|---|---|
|Checksum MD5 (Slot 1)|`0x00000300`|16|Valida a integridade dos dados do primeiro slot.|
|Bloco de Dados do Slot 1|`0x00000310`|2.621.440 (`0x280000`)|Contém atributos, inventário e flags de mundo do Slot 1.|
|Checksum MD5 (Slot 2)|`0x00280310`|16|Valida a integridade do segundo slot de personagem.|
|Bloco de Dados do Slot 2|`0x00280320`|2.621.440 (`0x280000`)|Estrutura repetitiva para o segundo slot.|
|SteamID64 Binding|`0x019003B4`|8|Vincula o arquivo à conta específica do usuário.|

  

Cada slot subsequente segue a aritmética de `Offset_Slot_N = 0x310 + (N-1) * 0x280010`, onde o incremento leva em conta os 16 bytes adicionais do checksum que precede cada slot. O tamanho de 2,6 MiB por slot é reservado inteiramente no momento da criação do personagem, preenchido com _padding_ nulo onde os dados ainda não foram gerados, o que simplifica a lógica de leitura direta via `seek()` em Python.   

### Estrutura Interna do Slot: Inventário e Flags de Evento

Dentro de cada bloco de slot, os dados não são organizados de forma linear simples; há subseções dedicadas a diferentes aspectos da simulação. O inventário, por exemplo, é gerido como uma lista de entradas onde cada item possui um ID único de 32 bits, seguido por modificadores de nível de reforço e cinzas de guerra aplicadas. As flags de eventos, por outro lado, operam como uma bitmask massiva, onde cada bit representa um estado booleano: um chefe derrotado, uma porta aberta ou um diálogo concluído.   

A complexidade aumenta com a versão 1.12, que introduziu novos intervalos de flags para o Reino das Sombras. Para o arquiteto de dados, isso significa que o dashboard deve ser capaz de distinguir entre o mapa global original (_The Lands Between_) e o novo mapa da DLC, interpretando as faixas de IDs de eventos de forma contextual.   

## Mecanismos de Validação, Segurança e Integridade

A integridade do arquivo de salvamento é protegida por camadas de validação que impedem não apenas a corrupção acidental, mas também a manipulação trivial de dados que poderia desencadear banimentos pelo sistema _Easy Anti-Cheat_ (EAC) ou simplesmente impedir o carregamento do jogo. O entendimento desses mecanismos é vital para que o dashboard possa ler o arquivo continuamente sem causar conflitos de acesso ou ser detectado como uma ferramenta de modificação não autorizada.   

### Vinculação por SteamID64 e Portabilidade de Dados

O Elden Ring utiliza o SteamID64 do usuário para "selar" o arquivo de salvamento. Esse ID é um inteiro de 64 bits único para cada conta Steam e é verificado pelo jogo durante a inicialização. Se o ID contido no arquivo binário não coincidir com o ID da conta ativa na sessão da Steam, o jogo recusará o carregamento, alegando corrupção.   

A localização física desse ID no arquivo reside no offset global `0x019003B4`. Para um desenvolvedor no Linux, extrair esse valor é o primeiro passo para validar se o arquivo que o dashboard está tentando monitorar pertence realmente ao usuário atual. No ambiente Proton, o caminho do arquivo reflete frequentemente esse ID, facilitando a automação da descoberta do diretório de salvamento correto em `~/.steam/steam/steamapps/compatdata/1245620/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing/`.   

### Cálculo de Checksum MD5 em Python

O motor SoulsTech emprega o algoritmo de hash MD5 para validar blocos específicos de dados dentro do `.sl2`. Cada slot tem seu próprio MD5, calculado sobre o intervalo exato de dados que compõem o personagem. Se um único bit for alterado sem a atualização correspondente da hash no cabeçalho do slot, o jogo apresentará falha no carregamento.   

Para o dashboard, o uso da biblioteca nativa `hashlib` do Python é suficiente e preferível em termos de performance. O processo de validação segue a lógica de extrair o bloco de dados, passar pelo método `md5().digest()` e comparar o resultado com os 16 bytes armazenados no offset de checksum correspondente.   

Python

```
import hashlib

def validate_slot_integrity(save_data, slot_index):
    # Offset base para o primeiro slot de dados é 0x310
    # Offset base para o primeiro checksum é 0x300
    slot_offset = 0x310 + (slot_index * 0x280010)
    checksum_offset = 0x300 + (slot_index * 0x280010)

    # Extração do bloco de dados de 2.6 MiB
    data_block = save_data[slot_offset : slot_offset + 0x280000]
    calculated_hash = hashlib.md5(data_block).digest()

    # Extração da hash armazenada
    stored_hash = save_data[checksum_offset : checksum_offset + 16]

    return calculated_hash == stored_hash.[3, 4]
```

Essa validação deve ser executada toda vez que o dashboard detectar uma alteração no arquivo (via `inotify` no Linux ou polling regular), garantindo que a interface do Streamlit nunca apresente dados de um estado de salvamento inválido ou incompleto.   

## Rastreamento de Estatísticas e Atributos do Jogador

A extração de atributos como Nível, Runas, Vigor e Mente permite ao dashboard fornecer uma análise profunda da eficácia da build do jogador e o progresso em direção aos "soft caps" de cada estatística. Esses valores são armazenados como inteiros de 32 bits (Little-Endian) em localizações fixas dentro do bloco de dados de cada personagem.   

### Mapeamento de Atributos e Limites de Rendimento (Soft Caps)

O entendimento das estatísticas primárias é fundamental para a criação de alertas no dashboard, como quando um jogador atinge o nível de Vigor onde o ganho de HP por ponto investido cai drasticamente.   

|Atributo|Significado Técnico|Intervalos de Soft Cap|Impacto na Gameplay|
|---|---|---|---|
|**Vigor**|Pontos de Vida (HP) e Resistência a Fogo|40 / 60|Redução drástica no ganho de HP após o nível 60.|
|**Mente**|Pontos de Foco (FP) e Resistência a Sono|50 / 60|Otimização para conjuradores de feitiços pesados.|
|**Tolerância**|Stamina e Carga de Equipamento|25 / 60|Crucial para evitar o "heavy roll" (rolamento lento).|
|**Força**|Escalonamento Físico e Defesa Física|20 / 53 / 80|O bônus de 1.5x ao segurar arma com duas mãos afeta o cap prático.|
|**Destreza**|Dano e Velocidade de Conjuração|20 / 53 / 80|Diminui o tempo de animação de magias entre os níveis 30 e 70.|
|**Inteligência**|Dano Mágico e Escalonamento de Cajados|20 / 50 / 80|Requisito para magias lendárias como o Cometa Azur.|
|**Fé**|Dano Sagrado/Fogo e Encantamentos|20 / 50 / 80|Essencial para builds de suporte e dano elemental.|
|**Arcano**|Descoberta de Itens e Escalonamento de Status|20 / 60 / 80|Afeta diretamente a rapidez com que Sangramento e Veneno ocorrem.|

  

No sistema de arquivos, esses valores residem em uma estrutura contígua. A utilização da biblioteca `struct` do Python permite desempacotar esses bytes em um dicionário utilizável pelo Streamlit de forma instantânea. É importante notar que as runas totais e as runas detidas no momento são campos distintos; o dashboard deve focar nas runas detidas para fornecer uma estimativa de risco de perda em caso de morte.   

## O Ecossistema de Event Flags e Progresso do Mundo

Para um dashboard de progresso, o rastreamento de chefes derrotados e locais descobertos é a funcionalidade mais valorizada. Isso é alcançado através da leitura das _Event Flags_, que funcionam como o registro histórico de todas as interações do jogador com o mundo de Elden Ring.   

### Estrutura de Bitmasks e Identificação de Chefes

Diferente dos atributos, que são valores numéricos diretos, o progresso é armazenado em campos de bits. Cada byte contém o estado de 8 eventos diferentes. A FromSoftware organiza esses IDs de evento em categorias lógicas, o que permite filtrar o progresso por "Chefes Principais", "Chefes de Campo" ou "Locais de Graça".   

|Categoria|Faixa de IDs|Exemplos de Flags (Defeat/Unlock)|
|---|---|---|
|**Chefes do Jogo Base**|`9100 - 9139`|`9100`: Godrick; `9101`: Margit; `9120`: Malenia.|
|**Chefes da DLC (SotE)**|`9140 - 9199`|`9143`: Radahn Consorte; `9146`: Messmer; `9190`: Rellana.|
|**Revelação de Mapa**|`62000 - 62099`|`62010`: Limgrave W; `62080`: Gravesite Plain.|
|**Aquisição de Mapa**|`63000 - 63099`|`63010`: Item de Mapa Limgrave; `63080`: Item Gravesite.|
|**Finais do Jogo**|`20 - 24`|`21`: Era das Estrelas; `22`: Lorde da Chama Frenética.|

  

A transição para o New Game Plus (NG+) é marcada pela flag `30`, e a contagem de ciclos (laps) é armazenada nas flags `50` a `58`. Um dashboard inteligente deve detectar essas flags para resetar visualmente o progresso das "Graças" e "Chefes", mantendo os registros de inventário e nível.   

### Shadow of the Erdtree: Novas Fronteiras de Dados

A expansão introduziu desafios técnicos adicionais. As novas áreas do Reino das Sombras utilizam faixas de flags que não existiam no lançamento inicial, como o intervalo `62080-62084` para a revelação das cinco principais áreas do mapa da DLC. Além disso, o sistema de bençãos (_Scadutree Fragments_) é rastreado por um conjunto específico de flags de coleta que o dashboard deve monitorar para informar ao jogador o seu nível de poder relativo dentro da expansão.   

Para garantir que o rastreador seja "à prova de futuro", a arquitetura do banco de dados de referência deve ser baseada em arquivos JSON que podem ser atualizados sem reescrever o motor de leitura binária. Isso permite que a comunidade adicione novos IDs de eventos conforme são descobertos em patches subsequentes.   

## O Sistema de Coordenadas e Geoprocessamento

A exibição da posição do jogador em um mapa interativo é o componente visualmente mais complexo do sistema. Elden Ring armazena a posição do jogador como um vetor de três componentes (XYZ) em ponto flutuante de precisão simples (float32). No entanto, esses valores representam metros em um espaço tridimensional e precisam ser projetados em um plano bidimensional para ferramentas como Folium ou Leaflet.   

### Conversão de Unidades do Jogo para Projeção 2D

No motor do jogo, o eixo Y frequentemente representa a altitude, enquanto X e Z definem a posição no plano do solo. Para um mapa 2D, ignoramos o componente de altitude (embora ele possa ser usado para alternar automaticamente entre níveis de mapa, como o subterrâneo e a superfície).   

A fórmula de conversão para o Leaflet, utilizando o sistema de coordenadas `L.CRS.Simple` (que trata lat/lng como pixels diretos), segue uma transformação afim baseada em um ponto de origem e um fator de escala.   

Xpixel​=(Xgame​⋅Scalex​)+Offsetx​

Ypixel​=(Zgame​⋅Scaley​)+Offsety​

Pesquisas da comunidade de cartografia de Elden Ring sugerem que a unidade fundamental é de 1 metro por unidade de coordenada. Em certas projeções, a origem (0,0) do mapa centraliza-se em áreas específicas, e as coordenadas NE (Nordeste) podem atingir valores de até 15359 em cada eixo. O dashboard deve carregar esses parâmetros de calibração para garantir que o marcador do jogador não "flutue" fora das estradas ou pontos de interesse conhecidos.   

### Datasets Públicos e Cartografia OSINT

Para evitar a necessidade de extrair manualmente cada coordenada de "Site de Graça" ou "Localização de Chefe", o projeto deve alavancar datasets existentes em JSON ou CSV provenientes de repositórios de código aberto.   

1. **ERDB (Elden Ring Database)**: Fornece mapeamentos detalhados de itens e inimigos com metadados associados.   

2. **Elden Ring API (FanAPIs)**: Útil para buscar nomes e descrições de locais em formato JSON via REST.   

3. **Map Tiles**: Imagens de alta resolução podem ser encontradas em projetos como o `LandsBetween` ou extraídas diretamente do jogo via ferramentas de extração de texturas, permitindo a criação de um mapa interativo fluido e visualmente fiel.   


## Implementação do Dashboard: Python, Streamlit e Pop!_OS

A execução do dashboard em um ambiente Linux focado em performance, como o Pop!_OS, requer uma ponte entre o sistema de arquivos do Linux e o ambiente simulado do Proton onde o jogo reside. O dashboard não deve apenas ler o arquivo uma vez, mas "vigiar" alterações para fornecer telemetria em tempo real.   

### Estrutura de Software e Monitoramento de Arquivos

O núcleo do sistema utiliza a biblioteca `watchdog` para monitorar eventos de escrita no arquivo `ER0000.sl2`. Devido à forma como o Proton gerencia a escrita (muitas vezes criando arquivos temporários ou reescrevendo o arquivo inteiro de uma vez), o script deve ser resiliente a travamentos de leitura e erros de permissão.   

A arquitetura recomendada segue este fluxo:

1. **Observador de Sistema**: Detecta o fechamento de uma operação de escrita no salvamento.

2. **Parser Binário**: Lê os blocos de dados, valida o MD5 e desempacota as estatísticas e flags.   

3. **Processador de Estado**: Compara as flags atuais com o banco de dados de referência (JSON) para identificar mudanças no progresso.   

4. **Interface Streamlit**: Atualiza os componentes visuais, como o mapa e os gráficos de barra de HP/FP/Stamina, utilizando `st.empty()` para evitar recarregamentos totais de página.


### Esquema de Dados para Referência (JSON)

Para manter a modularidade e facilitar a manutenção com novos patches, as definições de dados devem seguir um esquema rigoroso. Abaixo, o esquema para os dados de referência:

JSON

```
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EldenRingReferenceDB",
  "type": "object",
  "properties": {
    "bosses": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "integer" },
          "name": { "type": "string" },
          "flag": { "type": "integer" },
          "coords": {
            "type": "object",
            "properties": {
              "x": { "type": "number" },
              "y": { "type": "number" },
              "z": { "type": "number" }
            }
          },
          "is_dlc": { "type": "boolean" }
        }
      }
    },
    "maps": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "reveal_flag": { "type": "integer" },
          "acquire_flag": { "type": "integer" }
        }
      }
    }
  }
}
```

### Snippet de Implementação do Parser Binário

O código a seguir demonstra como extrair as estatísticas vitais utilizando a biblioteca `struct`. Os offsets mostrados são baseados em análise de engenharia reversa para a versão 1.12+.   

Python

```
import struct

def parse_save_slot(data_block):
    """
    Desempacota estatísticas vitais de um bloco de dados de slot de Elden Ring.
    Considera o início do bloco em 0x00 para cálculos relativos.
    """
    stats = {}

    # Exemplo de extração de Nível e Runas
    # Offsets relativos ao início do bloco de dados (0x310 no arquivo total)
    # Nota: Estes offsets podem variar levemente entre patches; recomenda-se
    # usar assinaturas de busca (pattern matching) para resiliência.

    # Nível do Personagem (RL)
    stats['level'] = struct.unpack('<I', data_block[0x20:0x24])

    # Atributos Base
    # Frequentemente armazenados em uma sequência de 8 inteiros
    attr_block = data_block[0x30:0x50]
    attrs = struct.unpack('<8I', attr_block)
    stats['attributes'] = {
        'Vigor': attrs,
        'Mind': attrs,
        'Endurance': attrs,
        'Strength': attrs,
        'Dexterity': attrs,
        'Intelligence': attrs,
        'Faith': attrs,
        'Arcane': attrs
    }

    # Extração de Coordenadas Atuais
    # Armazenadas como float32 (X, Y, Z)
    coord_block = data_block[0x110:0x11C] # Offset ilustrativo
    stats['pos'] = struct.unpack('<3f', coord_block)

    return stats.[8, 21, 30]
```

## Inteligência de Código Aberto (OSINT) e Repositórios Essenciais

O sucesso deste projeto depende da integração de dados curados pela comunidade. Abaixo estão os repositórios e links de dados primordiais para alimentar a lógica do dashboard.

### Mapeamento de IDs e Descrições

- **ERDB (EldenRingDatabase/erdb)**: Este repositório é a fonte autoritativa para mapeamentos de `item_id` para `item_name`. Ele contém geradores que extraem dados diretamente dos arquivos do jogo (`regulation.bin` e `msg/engUS`) para gerar JSONs consumíveis. Ideal para traduzir os IDs encontrados no inventário do arquivo de salvamento.   

- **Impalers-Archive (ividyon/Impalers-Archive)**: Um dump completo dos textos e diálogos do DLC _Shadow of the Erdtree_. Essencial para obter os nomes e descrições dos novos chefes e itens da expansão, garantindo que o dashboard exiba os nomes oficiais.


### Ativos Cartográficos e Coordenadas

- **LandsBetween (honzaap/LandsBetween)**: Oferece remakes do mapa das Terras Intermédias que podem ser adaptados para o dashboard. Embora focado em low-poly, a lógica de posicionamento é útil para referência de escala.   

- **BossTrackER (LucaFraMacera/BossTrackER)**: Um rastreador focado em chefes que já contém listas parciais de coordenadas e drops, servindo como uma excelente base de comparação para validar a localização dos chefes no dashboard.   

- **Interactive Map Assets**: Sites como Fextralife e IGN possuem as texturas de mapa mais atualizadas, que podem ser segmentadas em tiles para uso com a biblioteca Folium em Python.   


## Considerações Finais sobre Robustez e Manutenção

O desenvolvimento de uma ferramenta que interage com dados binários de um jogo em constante evolução como Elden Ring exige uma mentalidade de "design para falha". Patches como o 1.12 frequentemente deslocam pequenos blocos de dados ou alteram a forma como certas flags são interpretadas. Portanto, a implementação de buscas por padrões (signatures) em vez de offsets estáticos rígidos é uma prática recomendada para garantir que o dashboard não quebre em cada atualização menor do Steam.   

Além disso, o monitoramento em tempo real no Linux deve levar em conta a latência de sincronização do Proton e da Steam Cloud. É imperativo que o dashboard opere em modo de leitura apenas (`rb`), evitando qualquer tentativa de escrita que possa corromper o arquivo original ou ser sinalizada como trapaça. Através da síntese de engenharia reversa, geoprocessamento e desenvolvimento web moderno com Streamlit, é possível criar uma janela analítica sem precedentes para a jornada do Maculado, transformando bytes obscuros em insights estratégicos e progresso visualizado.   

[

![](https://t1.gstatic.com/faviconV2?url=https://github.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

github.com

dsyer/jersc - GitHub

Abre em uma nova janela](https://github.com/dsyer/jersc)[

![](https://t1.gstatic.com/faviconV2?url=https://github.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

github.com

ividyon/Impalers-Archive: A dump of ELDEN RING: Shadow of the Erdtree's text (Based on AsteriskAmpersand's Carian-Archive) - GitHub

Abre em uma nova janela](https://github.com/ividyon/Impalers-Archive)[

![](https://t2.gstatic.com/faviconV2?url=https://www.reddit.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

reddit.com

Fix for "The save data is corrupted." after PC crash with Steam Cloud Off (back-up save required) : r/EldenRingMods - Reddit

Abre em uma nova janela](https://www.reddit.com/r/EldenRingMods/comments/1oglbrg/fix_for_the_save_data_is_corrupted_after_pc_crash/)[

![](https://t2.gstatic.com/faviconV2?url=https://steamcommunity.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

steamcommunity.com

Comunidad de Steam :: Guía :: Corrupted Save Data; Every Workaround Possible

Abre em uma nova janela](https://steamcommunity.com/sharedfiles/filedetails/?l=latam&id=2797241037)[

![](https://t0.gstatic.com/faviconV2?url=https://www.techradar.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

techradar.com

Where is your Elden Ring save file location on PC - TechRadar

Abre em uma nova janela](https://www.techradar.com/how-to/where-to-find-your-elden-ring-save-file-location-on-pc)[

![](https://t2.gstatic.com/faviconV2?url=https://www.reddit.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

reddit.com

I want to make a save file mod : r/EldenRingMods - Reddit

Abre em uma nova janela](https://www.reddit.com/r/EldenRingMods/comments/1h2r5r3/i_want_to_make_a_save_file_mod/)[

![](https://t2.gstatic.com/faviconV2?url=https://steamcommunity.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

steamcommunity.com

Society if Fromsoft let me have more than 10 save slots: :: ELDEN RING General Discussions

Abre em uma nova janela](https://steamcommunity.com/app/1245620/discussions/0/4298194004191872845/)[

![](https://t1.gstatic.com/faviconV2?url=https://github.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

github.com

hexedit.py - Ariescyn/EldenRing-Save-Manager - GitHub

Abre em uma nova janela](https://github.com/Ariescyn/EldenRing-Save-Manager/blob/main/hexedit.py)[

![](https://t1.gstatic.com/faviconV2?url=https://github.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

github.com

Nordgaren/Elden-Ring-Debug-Tool - GitHub

Abre em uma nova janela](https://github.com/Nordgaren/Elden-Ring-Debug-Tool)[

![](https://t2.gstatic.com/faviconV2?url=https://www.reddit.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

reddit.com

Failed to load save data - any fix? : r/Eldenring - Reddit

Abre em uma nova janela](https://www.reddit.com/r/Eldenring/comments/t8205l/failed_to_load_save_data_any_fix/)[

![](https://t2.gstatic.com/faviconV2?url=https://www.reddit.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

reddit.com

I've made an Elden Ring item hex ID list. : r/opensouls3 - Reddit

Abre em uma nova janela](https://www.reddit.com/r/opensouls3/comments/to9t6l/ive_made_an_elden_ring_item_hex_id_list/)[

![](https://t1.gstatic.com/faviconV2?url=https://soulsmodding.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

soulsmodding.com

Event Flags (ER) - Souls Modding Wiki

Abre em uma nova janela](https://soulsmodding.com/doku.php?id=er-refmat:event-flag-list)[

![](https://t0.gstatic.com/faviconV2?url=http://soulsmodding.wikidot.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

soulsmodding.wikidot.com

Tutorial: Learning How To Use EMEVD - Souls Modding - Wikidot

Abre em uma nova janela](http://soulsmodding.wikidot.com/tutorial:learning-how-to-use-emevd)[

![](https://t2.gstatic.com/faviconV2?url=https://www.reddit.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

reddit.com

HOW TO: Elden Ring Save File Steam Account Swap / Recover Broken Save Game : r/Eldenring - Reddit

Abre em uma nova janela](https://www.reddit.com/r/Eldenring/comments/t61znv/how_to_elden_ring_save_file_steam_account_swap/)[

![](https://t1.gstatic.com/faviconV2?url=https://cybergiant7.github.io/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

cybergiant7.github.io

Elden Ring Checklist

Abre em uma nova janela](https://cybergiant7.github.io/Elden-Ring-Automatic-Checklist/)[

![](https://t2.gstatic.com/faviconV2?url=https://www.reddit.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

reddit.com

CORRUPTED SAVE DATA. People knowledgeable in hex editors wanted - Reddit

Abre em uma nova janela](https://www.reddit.com/r/Eldenring/comments/1lzczde/corrupted_save_data_people_knowledgeable_in_hex/)[

![](https://t0.gstatic.com/faviconV2?url=https://stackoverflow.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

stackoverflow.com

How to calculate the MD5 checksum of a file in Python? [duplicate] - Stack Overflow

Abre em uma nova janela](https://stackoverflow.com/questions/16874598/how-to-calculate-the-md5-checksum-of-a-file-in-python)[

![](https://t0.gstatic.com/faviconV2?url=https://stackoverflow.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

stackoverflow.com

How to generate an MD5 checksum of a file in Python? - Stack Overflow

Abre em uma nova janela](https://stackoverflow.com/questions/3431825/how-to-generate-an-md5-checksum-of-a-file-in-python)[

![](https://t2.gstatic.com/faviconV2?url=https://www.reddit.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

reddit.com

Elden Ring Compass. Save file / Progression Website : r/EldenRingMods - Reddit

Abre em uma nova janela](https://www.reddit.com/r/EldenRingMods/comments/1dslf38/elden_ring_compass_save_file_progression_website/)[

![](https://t0.gstatic.com/faviconV2?url=https://eldenring.wiki.fextralife.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

eldenring.wiki.fextralife.com

Stats | Elden Ring Wiki

Abre em uma nova janela](https://eldenring.wiki.fextralife.com/Stats)[

![](https://t2.gstatic.com/faviconV2?url=https://steamcommunity.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

steamcommunity.com

The Huge Recluse Guide - Steam Community

Abre em uma nova janela](https://steamcommunity.com/sharedfiles/filedetails/?id=3530117501)[

![](https://t0.gstatic.com/faviconV2?url=https://eldenring.wiki.fextralife.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

eldenring.wiki.fextralife.com

Vigor | Elden Ring Wiki

Abre em uma nova janela](https://eldenring.wiki.fextralife.com/Vigor)[

![](https://t2.gstatic.com/faviconV2?url=https://www.reddit.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

reddit.com

Quick graph of Rune Level vs Vigor, Mind and Endurance : r/Eldenring - Reddit

Abre em uma nova janela](https://www.reddit.com/r/Eldenring/comments/udxi3j/quick_graph_of_rune_level_vs_vigor_mind_and/)[

![](https://t2.gstatic.com/faviconV2?url=https://steamcommunity.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

steamcommunity.com

Steam-samfunn :: Veiledning :: Stat Breakpoints aka "Soft Caps"

Abre em uma nova janela](https://steamcommunity.com/sharedfiles/filedetails/?l=norwegian&id=2765060616)[

![](https://t0.gstatic.com/faviconV2?url=https://eldenring.wiki.fextralife.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

eldenring.wiki.fextralife.com

Marika's Soreseal | Elden Ring Wiki

Abre em uma nova janela](https://eldenring.wiki.fextralife.com/Marika's+Soreseal)[

![](https://t0.gstatic.com/faviconV2?url=https://digitalchumps.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

digitalchumps.com

Elden Ring Nightreign Review - digitalchumps

Abre em uma nova janela](https://digitalchumps.com/elden-ring-nightreign-review/)[

![](https://t1.gstatic.com/faviconV2?url=https://www.rockpapershotgun.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

rockpapershotgun.com

Elden Ring Shadow Of The Erdtree: Sites Of Grace map | Rock Paper Shotgun

Abre em uma nova janela](https://www.rockpapershotgun.com/elden-ring-shadow-of-the-erdtree-sites-of-grace-locations)[

![](https://t1.gstatic.com/faviconV2?url=https://github.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

github.com

EldenRingDatabase/erdb: JSON schema and data parser for ELDEN RING - GitHub

Abre em uma nova janela](https://github.com/EldenRingDatabase/erdb)[

![](https://t1.gstatic.com/faviconV2?url=https://github.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

github.com

GitHub - deliton/eldenring-api: Open source API for the awesome Elden Ring game

Abre em uma nova janela](https://github.com/deliton/eldenring-api)[

![](https://t0.gstatic.com/faviconV2?url=https://stackoverflow.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

stackoverflow.com

How to get xy screen coordinates from xyz world coordinates? - Stack Overflow

Abre em uma nova janela](https://stackoverflow.com/questions/55445154/how-to-get-xy-screen-coordinates-from-xyz-world-coordinates)[

![](https://t0.gstatic.com/faviconV2?url=https://stackoverflow.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

stackoverflow.com

Converting XYZ to XY (world coords to screen coords) - Stack Overflow

Abre em uma nova janela](https://stackoverflow.com/questions/45154726/converting-xyz-to-xy-world-coords-to-screen-coords)[

![](https://t2.gstatic.com/faviconV2?url=https://www.reddit.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

reddit.com

Help converting Lat/Long to 2D coordinates for a game? : r/cartography - Reddit

Abre em uma nova janela](https://www.reddit.com/r/cartography/comments/1cyzgab/help_converting_latlong_to_2d_coordinates_for_a/)[

![](https://t0.gstatic.com/faviconV2?url=https://stackoverflow.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

stackoverflow.com

Leaflet JS: Custom 2D projection that uses meters instead of lat,long - Stack Overflow

Abre em uma nova janela](https://stackoverflow.com/questions/34688018/leaflet-js-custom-2d-projection-that-uses-meters-instead-of-lat-long)[

![](https://t0.gstatic.com/faviconV2?url=https://stackoverflow.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

stackoverflow.com

Changing the coordinate system on my leaflet map to custom (scale and 0,0 position)

Abre em uma nova janela](https://stackoverflow.com/questions/57894197/changing-the-coordinate-system-on-my-leaflet-map-to-custom-scale-and-0-0-positi)[

![](https://t1.gstatic.com/faviconV2?url=https://github.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

github.com

EldenRing-Save-Manager/ALL_ITEM_IDS.md at main - GitHub

Abre em uma nova janela](https://github.com/Ariescyn/EldenRing-Save-Manager/blob/main/ALL_ITEM_IDS.md)[

![](https://t2.gstatic.com/faviconV2?url=https://docs.eldenring.fanapis.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

docs.eldenring.fanapis.com

Locations Route - Elden Ring API

Abre em uma nova janela](https://docs.eldenring.fanapis.com/docs/locations)[

![](https://t1.gstatic.com/faviconV2?url=https://github.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

github.com

honzaap/LandsBetween: The Lands Between from Elden Ring in low-poly - GitHub

Abre em uma nova janela](https://github.com/honzaap/LandsBetween)[

![](https://t1.gstatic.com/faviconV2?url=https://github.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

github.com

commenthol/gdal2tiles-leaflet: Generate raster image tiles for use with leaflet. - GitHub

Abre em uma nova janela](https://github.com/commenthol/gdal2tiles-leaflet)[

![](https://t1.gstatic.com/faviconV2?url=https://github.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

github.com

LucaFraMacera/BossTrackER: An Elden Ring Boss tracker, where you can see the location and drops of all the bosses/invasions present in the game. - GitHub

Abre em uma nova janela](https://github.com/LucaFraMacera/BossTrackER)[

![](https://t3.gstatic.com/faviconV2?url=https://www.eurogamer.net/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

eurogamer.net

Elden Ring Site of Grace locations | Eurogamer.net

Abre em uma nova janela](https://www.eurogamer.net/elden-ring-all-site-of-grace-locations-8042)[

![](https://t3.gstatic.com/faviconV2?url=https://www.powerpyx.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

powerpyx.com

Elden Ring All Sites of Grace Locations - PowerPyx

Abre em uma nova janela](https://www.powerpyx.com/elden-ring-all-sites-of-grace-locations/)[

![](https://t0.gstatic.com/faviconV2?url=https://stackoverflow.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

stackoverflow.com

How to create a Datasheet for Elden Ring Save-Files - Stack Overflow

Abre em uma nova janela](https://stackoverflow.com/questions/71605442/how-to-create-a-datasheet-for-elden-ring-save-files)[

![](https://t2.gstatic.com/faviconV2?url=https://steamcommunity.com/&client=BARD&type=FAVICON&size=256&fallback_opts=TYPE,SIZE,URL)

steamcommunity.com

Checklist (Items, spells, etc.) + 100% save file download DLC ready - Steam Community





](https://steamcommunity.com/sharedfiles/filedetails/?l=english&id=2789996107)
