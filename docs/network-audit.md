# Auditoria de Rede e Mapeamento de Comunicações

Este documento cataloga todos os pontos do código-fonte do **Zed** onde ocorrem saídas para a rede, sua criticidade para a privacidade e como o projeto **Muted** os neutraliza ou gerencia.

---

## 1. Inventário de Endpoints e Componentes

### 1.1 `crates/telemetry` & `crates/client/src/telemetry.rs`
- **Função:** Registro de eventos de uso, profiling de frame drops, ativação de extensões e métricas analíticas.
- **Endpoint Upstream:** `POST /telemetry/events` (com header `x-zed-checksum`).
- **Dados Transmitidos:**
  - `system_id`: Identificador persistente baseado nas informações de hardware da máquina.
  - `installation_id`: UUID único gerado na primeira execução do aplicativo.
  - `session_id`: UUID aleatório gerado a cada inicialização do processo.
  - `metrics_id`: UUID de usuário quando conectado com conta Zed.
  - `events`: Array de payloads em JSON contendo nomes de ações, linguagens de código abertas e flags de estado.
- **Tratamento no Muted:**
  - `crates/telemetry/src/telemetry.rs`: `send_event` e `init` convertidos em no-op imediato. A fila `TELEMETRY_QUEUE` não recebe nenhum item.
  - `crates/client/src/telemetry.rs`: `flush_events_inner` retorna imediatamente `Ok(())` sem construir requisições HTTP nem transmitir bytes.

---

### 1.2 `crates/crashes` & `crates/zed/src/reliability.rs`
- **Função:** Captura de sinais de panic e falhas catastróficas em um processo auxiliar `minidumper`, gerando arquivos `.dmp` e metadados de diagnóstico.
- **Endpoint Upstream:** `MINIDUMP_ENDPOINT` (configurado via env `ZED_MINIDUMP_ENDPOINT` ou servidor Sentry da Zed).
- **Dados Transmitidos:** Minidump de memória (registros de CPU, pilha de execução, trechos de memória do processo) + especificações de GPU e versão do OS.
- **Risco:** Minidumps de processo podem conter trechos residuais de buffers de texto abertos (código proprietário, credenciais de arquivos `.env` temporariamente em memória).
- **Tratamento no Muted:**
  - `MINIDUMP_ENDPOINT` forçado estaticamente para `None`.
  - Removida a chamada a `upload_previous_minidumps` em `reliability::init`. `upload_build_timings` (só para staff) segue ativo, mas emite via `telemetry::event!` → `send_event`, que é no-op. O upload de crashes de projetos remotos (`observe_new`) para cedo porque `MINIDUMP_ENDPOINT` é `None` (verificado em v1.9.0).
  - O arquivo minidump é preservado localmente em caso de colisão para uso exclusivo do usuário.

---

### 1.3 `crates/auto_update`
- **Função:** Verificação periódica de novas versões da aplicação (a cada 60 min no canal estável).
- **Endpoint Upstream:** `GET /releases/latest` ou consulta à API de releases do GitHub.
- **Dados Transmitidos:** Parâmetros de arquitetura e sistema operacional nos cabeçalhos (`os`, `arch`, `version`).
- **Tratamento no Muted:**
  - Configuração `auto_update` alterada para `false` no arquivo `assets/settings/default.json`.
  - O usuário atualiza o aplicativo controladamente através do gerenciador de pacotes ou downloads manuais de release.

---

### 1.4 `crates/collab` & Servidor de Presença
- **Função:** Canais de voz, edição compartilhada em tempo real e lista de contatos.
- **Endpoint Upstream:** `https://zed.dev` (configurado pela chave `server_url`).
- **Dados Transmitidos:** Autenticação OAuth via GitHub, sessões WebSocket de presença.
- **Tratamento no Muted:**
  - Não conecta silenciosamente se o usuário não clicar em "Sign In".
  - Permite configuração de servidor próprio via variável `ZED_SERVER_URL` ou chave `server_url` no `settings.json`.

---

### 1.5 `crates/assistant` (IA & Modelos de Linguagem)
- **Função:** Integração com LLMs para autocompletion, chat e edição inline.
- **Endpoint Upstream:** Zed Cloud AI Proxy ou APIs diretas de terceiros.
- **Tratamento no Muted:**
  - `disable_ai: false` por padrão com suporte nativo a **BYOK** (OpenAI, Anthropic, Google Gemini, Ollama).
  - Recomendação explícita de uso com endpoints locais (`http://localhost:11434/v1` para Ollama) para garantir retenção zero e isolamento total.

---

### 1.6 `crates/extension` & `crates/language` (Extensões e LSPs)
- **Função:** Instalação de extensões de temas, linguagens e servidores LSP.
- **Endpoint Upstream:** Repositórios de extensões do Zed e releases oficiais de LSPs no GitHub (ex: `rust-analyzer`, `pyright`, `gopls`).
- **Tratamento no Muted:**
  - Upstream instala a extensão `html` automaticamente na inicialização (`auto_install_extensions`) e logo depois consulta `/extensions/updates` (`crates/extension_host/src/extension_host.rs:346-348`). O patch 0003 desliga a instalação automática do `html`.
  - Com extensões instaladas pelo usuário, a checagem de atualização na inicialização continua ativa (ver matriz abaixo).
  - Downloads de LSP e Node.js continuam automáticos ao abrir arquivos de uma linguagem.

---

## 2. Matriz de Status por Endpoint (verificada em Zed v1.9.0)

Legenda: **Bloqueado no código** = removido ou no-op por patch; **Desligado por padrão** = só a configuração padrão mudou, o usuário pode religar; **Ativo** = sem alteração.

| Saída de rede | Gatilho | Status | Evidência |
| :--- | :--- | :--- | :--- |
| Eventos de telemetria (`/telemetry/events`) | Automático | Bloqueado no código | Patch 0001; auditoria estática |
| Upload de minidumps locais | Inicialização | Bloqueado no código | Patch 0002 (`MINIDUMP_ENDPOINT = None`) |
| Upload de crashes de projeto remoto | Ao abrir projeto remoto | Bloqueado no código | Retorna cedo sem `MINIDUMP_ENDPOINT` (`reliability.rs`) |
| Build timings / hang reports | Automático | Bloqueado no código | Emitidos via `telemetry::event!` → `send_event` no-op |
| Verificação de atualização do Zed | Periódico | Desligado por padrão | Patch 0003 (`auto_update: false`) |
| Instalação automática da extensão `html` | Inicialização | Desligado por padrão | Patch 0003 (`auto_install_extensions.html: false`) |
| Checagem de atualização de extensões sem extensões instaladas | Inicialização | Bloqueado no código | Patch 0005 |
| Checagem de atualização de extensões instaladas (`/extensions/updates` em `api.zed.dev`) | Inicialização | **Ativo** | `extension_host.rs:348` |
| Registro de agentes ACP (`cdn.agentclientprotocol.com`) e ícones (`*.githubusercontent.com`) | Abrir a página do registro, ou usar agente do registro configurado (no máximo 1×/h) | Sob demanda | Patch 0006; antes era na inicialização |
| Sondagem de Ollama (`localhost:11434`) e LM Studio (`localhost:1234`) | Inicialização | Ativo (só loopback) | Observado em runtime (2026-10-19) |
| Login automático na Zed Cloud | Inicialização, se houver credencial salva | **Ativo** | `crates/zed/src/main.rs:878-881` |
| `system_id` no header `x-zed-system-id` | Requisições à Zed Cloud API com login | **Ativo** | `crates/cloud_api_client/src/cloud_api_client.rs:121` |
| Edit predictions (`provider: "zed"`) | Ao editar | **Ativo** (exige login; sem login não verificado) | `assets/settings/default.json` |
| Download de LSPs e Node.js | Ao abrir arquivo da linguagem | **Ativo** | `crates/languages`, `crates/node_runtime` |
| Provedores de IA | Ação do usuário | Ativo, sob demanda | `crates/language_models` |

### Verificação em runtime

**Resultado em 2026-10-19, patches 0001–0006 (macOS, build debug, HOME vazio, sem login, 90 s ocioso, Zed oficial aberto em paralelo):** PASSOU. Via proxy só houve requisições a `localhost:11434` e `localhost:1234`; sem proxy, só sockets loopback e nenhum socket de DNS.

**Resultado anterior, patches 0001–0004:** FALHOU. Via proxy local que registra e recusa cada `CONNECT`, o binário tentou `api.zed.dev:443` e `cdn.agentclientprotocol.com:443`. Sem o proxy, abriu ~28 conexões HTTPS ao CDN do registro ACP (download de ícones) e 1 a `zed.dev`. Nenhuma conexão contornou o proxy.

`scripts/runtime_network_check.py` roda o binário Linux por 90 s numa network namespace isolada, sob `strace`, com HOME vazio (sem credenciais nem extensões), e falha em qualquer tentativa de conexão não-loopback ou de consulta DNS. O job roda no CI após a compilação. Esse teste cobre só a **inicialização ociosa** de uma instalação nova; não cobre abrir arquivos, extensões instaladas nem login.
