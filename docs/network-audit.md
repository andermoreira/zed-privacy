# Auditoria de Rede e Mapeamento de Comunicações

Este documento cataloga todos os pontos do código-fonte do **Zed** onde ocorrem saídas para a rede, sua criticidade para a privacidade e como o projeto **Zed Privacy** os neutraliza ou gerencia.

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
- **Tratamento no Zed Privacy:**
  - `crates/telemetry/src/telemetry.rs`: `send_event` e `init` convertidos em no-op imediato. A fila `TELEMETRY_QUEUE` não recebe nenhum item.
  - `crates/client/src/telemetry.rs`: `flush_events_inner` retorna imediatamente `Ok(())` sem construir requisições HTTP nem transmitir bytes.

---

### 1.2 `crates/crashes` & `crates/zed/src/reliability.rs`
- **Função:** Captura de sinais de panic e falhas catastróficas em um processo auxiliar `minidumper`, gerando arquivos `.dmp` e metadados de diagnóstico.
- **Endpoint Upstream:** `MINIDUMP_ENDPOINT` (configurado via env `ZED_MINIDUMP_ENDPOINT` ou servidor Sentry da Zed).
- **Dados Transmitidos:** Minidump de memória (registros de CPU, pilha de execução, trechos de memória do processo) + especificações de GPU e versão do OS.
- **Risco:** Minidumps de processo podem conter trechos residuais de buffers de texto abertos (código proprietário, credenciais de arquivos `.env` temporariamente em memória).
- **Tratamento no Zed Privacy:**
  - `MINIDUMP_ENDPOINT` forçado estaticamente para `None`.
  - Neutralizada a rotina de envio em background (`upload_previous_minidumps` e `upload_build_timings`).
  - O arquivo minidump é preservado localmente em caso de colisão para uso exclusivo do usuário.

---

### 1.3 `crates/auto_update`
- **Função:** Verificação periódica de novas versões da aplicação (a cada 60 min no canal estável).
- **Endpoint Upstream:** `GET /releases/latest` ou consulta à API de releases do GitHub.
- **Dados Transmitidos:** Parâmetros de arquitetura e sistema operacional nos cabeçalhos (`os`, `arch`, `version`).
- **Tratamento no Zed Privacy:**
  - Configuração `auto_update` alterada para `false` no arquivo `assets/settings/default.json`.
  - O usuário atualiza o aplicativo controladamente através do gerenciador de pacotes ou downloads manuais de release.

---

### 1.4 `crates/collab` & Servidor de Presença
- **Função:** Canais de voz, edição compartilhada em tempo real e lista de contatos.
- **Endpoint Upstream:** `https://zed.dev` (configurado pela chave `server_url`).
- **Dados Transmitidos:** Autenticação OAuth via GitHub, sessões WebSocket de presença.
- **Tratamento no Zed Privacy:**
  - Não conecta silenciosamente se o usuário não clicar em "Sign In".
  - Permite configuração de servidor próprio via variável `ZED_SERVER_URL` ou chave `server_url` no `settings.json`.

---

### 1.5 `crates/assistant` (IA & Modelos de Linguagem)
- **Função:** Integração com LLMs para autocompletion, chat e edição inline.
- **Endpoint Upstream:** Zed Cloud AI Proxy ou APIs diretas de terceiros.
- **Tratamento no Zed Privacy:**
  - `disable_ai: false` por padrão com suporte nativo a **BYOK** (OpenAI, Anthropic, Google Gemini, Ollama).
  - Recomendação explícita de uso com endpoints locais (`http://localhost:11434/v1` para Ollama) para garantir retenção zero e isolamento total.

---

### 1.6 `crates/extension` & `crates/language` (Extensões e LSPs)
- **Função:** Instalação de extensões de temas, linguagens e servidores LSP.
- **Endpoint Upstream:** Repositórios de extensões do Zed e releases oficiais de LSPs no GitHub (ex: `rust-analyzer`, `pyright`, `gopls`).
- **Tratamento no Zed Privacy:**
  - Mantido sob demanda explícita do desenvolvedor ao abrir um arquivo ou solicitar a instalação de uma extensão.
  - Conexões futuras poderão ser intermediadas por cache offline ou repositórios espelho.
