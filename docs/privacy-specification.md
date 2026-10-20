# Especificação de Privacidade e Threat Model

Este documento formaliza as garantias de privacidade, o modelo de ameaças (*threat model*) e as diretrizes arquiteturais do projeto **Muted**.

---

## 1. Princípios Norteadores

1. **Privacidade por Desenho e por Padrão (Privacy by Design & Default):**
   Nenhuma informação de telemetria, metadados de hardware, identificadores de usuário ou diagnósticos de execução deve sair da máquina do desenvolvedor sem consentimento explícito e prévio.
2. **Separação Rígida entre Core Editor e Nuvem:**
   O editor de texto e suas funções essenciais (edição, sintaxe, busca, LSP local, terminal integrado) devem funcionar perfeitamente em ambientes 100% desconectados (*air-gapped*).
3. **Sustentabilidade via Patches Determinísticos:**
   Em vez de desviar a base de código em um fork que acumula débito técnico, o projeto emprega patches modulares aplicados sobre tags estáveis oficiais da Zed Industries.

---

## 2. Threat Model (Modelo de Ameaças)

### 2.1 Atores e Vetores de Rastreamento

| Vetor de Risco | Como o Zed Original Opera | Impacto de Privacidade | Mitigação do Muted |
| :--- | :--- | :--- | :--- |
| **Identificadores Persistentes de Máquina** | `system_id` (hardware hash) e `installation_id` (gerado por canal). | Permite correlacionar todas as sessões e projetos abertos à mesma máquina física. | Parcial. Sem envio por telemetria (no-op), mas os IDs continuam gerados e persistidos localmente (`crates/zed/src/main.rs`), e `system_id` é enviado no header `x-zed-system-id` à Zed Cloud API quando há login (`crates/cloud_api_client`, verificado em v1.9.0). |
| **Identificadores de Usuário** | `metrics_id` associado à conta GitHub/Zed Cloud quando autenticado. | Permite vincular métricas de comportamento ao e-mail/usuário real. | Neutralizado. Sem envio de métricas; autenticação na nuvem torna-se estritamente opt-in. |
| **Eventos de Telemetria** | `crates/telemetry` enfileira cliques, linguagens de programação usadas, extensões ativas e tempos de frame para `/telemetry/events`. | Perfilamento de produtividade, stack tecnológica da empresa e hábitos de trabalho. | Macro `telemetry::event!` e método `send_event` convertidos em no-op completo. Fila nunca inicializada. |
| **Minidumps e Stacktraces** | `crates/crashes` e `crates/zed/src/reliability.rs` geram minidumps `.dmp` e metadados `.json` com envio remoto para Sentry/Zed. | Dumps de memória podem conter pedaços de código-fonte, nomes de variáveis, tokens em memória ou caminhos de diretórios privados. | Upload remoto desativado (`MINIDUMP_ENDPOINT` forçado para `None`). Arquivos preservados exclusivamente em disco local. |
| **Pings Periódicos de Atualização** | `crates/auto_update` consulta servidores a cada 60 minutos (ou 15 min no nightly). | Expõe IP, versão em uso e padrões de horário de atividade. | `auto_update` definido como `false` por padrão. Checagem periódica não ocorre sem ação manual. |
| **Assistente de IA com Proxy de Terceiros** | O painel de assistente pode direcionar prompts via servidores da Zed Cloud. | Vazamento inadvertido de código proprietário para infraestrutura intermediária. | Configurações incentivam uso de chaves próprias (BYOK) direto com o provedor (ex: OpenAI, Anthropic) ou inferência local via Ollama / `llama.cpp`. |

---

## 3. Perfis de Conformidade (Privacy Levels)

O projeto categoriza o isolamento de privacidade em três níveis:

### Nível 1: Zero Telemetry (Perfil Padrão)
- **Escopo:** Desativação total de métricas de uso, telemetria de performance e relatórios remotos de colisão/crash.
- **Configurações Padrão:** `telemetry.diagnostics = false`, `telemetry.metrics = false`, `auto_update = false`.
- **Comportamento de Rede:** Uma instalação nova, ociosa e sem login não faz conexões externas (verificado em runtime no macOS em 2026-10-19; só sondagens loopback de Ollama/LM Studio). Continuam automáticos: download de Language Servers e Node.js ao abrir arquivos, checagem de atualização de extensões já instaladas e login na Zed Cloud quando há credencial salva. Ver `docs/network-audit.md` §2. Continuam automáticos: download de Language Servers e Node.js ao abrir arquivos, checagem de atualização de extensões já instaladas e login na Zed Cloud quando há credencial salva. Ver a matriz em `docs/network-audit.md` §2.

### Nível 2: De-Clouded (Local-First)
- **Escopo:** Nível 1 + neutralização visual e funcional dos módulos de autenticação compulsória e presença em nuvem (`zed.dev`).
- **Assistente:** Exclusivamente provedores locais (`Ollama`) ou endpoints definidos pelo usuário via `settings.json`.

### Nível 3: Air-Gapped (Strict Offline)
- **Escopo:** Nível 2 + bloqueio total de qualquer tentativa de download automático de binários em background (como Node.js ou LSPs pré-compilados).
- Todas as dependências externas e language servers devem ser fornecidos pelo sistema operacional local (ex: via `PATH`).

---

## 4. Verificação e Auditoria Contínua

Toda release gerada pelo **Muted** deve passar pelos seguintes critérios de aceitação:
1. **Verificação de Compilação de Patches:** Todos os patches modulares aplicam com sucesso sem `fuzz` crítico na tag estável correspondente.
2. **Inspeção Estática de Símbolos (`scripts/audit_network.py`):** O script de auditoria estática confirma que `MINIDUMP_ENDPOINT` é nulo e `flush_events` não referencia endpoints ativos de telemetria.
3. **Auditoria de Tráfego em Execução (`scripts/runtime_network_check.py`):** Na inicialização e repouso de uma sessão nova (Linux, HOME vazio), zero tentativas de conexão não-loopback ou de DNS. Executado no CI a cada build Linux; macOS ainda sem cobertura.
