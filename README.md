# Muted

**Muted** é uma distribuição *privacy-first* compilada a partir do código-fonte do editor [Zed](https://github.com/zed-industries/zed), com foco em **zero telemetria**, neutralização de rastreamento de hardware/sessão, e desativação de chamadas remotas silenciosas.

Inspirado no modelo de engenharia do **VSCodium** e do **Ungoogled Chromium**, este projeto adota uma arquitetura baseada em **patches modulares e compilação reproduzível** sobre o código upstream do Zed, permitindo acompanhar continuamente novas versões estáveis sem o atrito de manter um fork monolítico manual.

---

## 🎯 Objetivos de Privacidade

1. **Zero Telemetria (Client & Server Metrics):**
   - Elimina o envio de eventos de uso, latência de digitação, tempos de renderização e inventário de linguagens/extensões para `telemetry.zed.dev`.
   - Os identificadores de máquina (`system_id`), instalação (`installation_id`) e sessão (`session_id`) deixam de sair pela telemetria. Limitação: `system_id` ainda é gerado localmente e enviado no header `x-zed-system-id` às APIs da Zed Cloud quando o usuário faz login e usa recursos de nuvem (`crates/cloud_api_client`).
2. **Zero Upload de Diagnósticos & Minidumps:**
   - Desativa o envio automático de minidumps e stacktraces para Sentry ou servidores da Zed Industries.
   - Preserva dumps de travamento estritamente em disco local para inspeção manual pelo próprio desenvolvedor.
3. **Opt-out Invertido & Configurações Seguras por Padrão:**
   - As opções de `telemetry.metrics` e `telemetry.diagnostics` vêm desativadas por padrão no binário (`assets/settings/default.json`).
   - `auto_update` desativado por padrão, evitando pings de hora em hora a servidores remotos.
4. **Desacoplamento de Nuvem Proprietária:**
   - Uso de modelos de inteligência artificial via **BYOK (Bring Your Own Key)** direto (Anthropic, OpenAI, etc.) ou backends locais (`Ollama`, `llama.cpp`), sem trânsito obrigatório pelo proxy corporativo da Zed.
   - Editor funcional offline. Downloads automáticos de LSPs e Node.js ainda ocorrem ao abrir arquivos; para *air-gapped* forneça-os via `PATH`. Status por endpoint em [`docs/network-audit.md`](docs/network-audit.md#2-matriz-de-status-por-endpoint-verificada-em-zed-v190).

---

## 📁 Estrutura do Repositório

```text
zed-privacy/
├── docs/
│   ├── privacy-specification.md   # Threat Model, perfis de privacidade e garantias formais
│   └── network-audit.md           # Inventário de todas as chamadas de rede no código do Zed
├── patches/
│   ├── 0001-disable-telemetry-metrics.patch   # Torna crates/telemetry e client/telemetry no-op
│   ├── 0002-disable-crash-reporting.patch     # Desativa upload de minidumps em reliability
│   ├── 0003-privacy-default-settings.patch    # Telemetry, auto-update e auto-install desativados por padrão
│   ├── 0004-rebrand-muted.patch               # Binário `muted`, dados e porta de instância próprios
│   ├── 0005-skip-extension-update-check.patch # Sem checagem de extensões quando não há nenhuma
│   └── 0006-agent-registry-on-demand.patch    # Registro de agentes ACP só sob demanda
├── scripts/
│   ├── build.sh                   # Script principal para clonar upstream, aplicar patches e compilar
│   ├── audit_network.py           # Checagem estática dos patches no código upstream
│   └── runtime_network_check.py   # Checagem em runtime: binário sob strace sem rede (Linux)
├── tests/                         # Testes unitários (python3 -m unittest discover -s tests)
├── .github/
│   └── workflows/
│       └── build-release.yml      # CI/CD automatizado para compilar releases (macOS / Linux)
└── README.md
```

---

## 🚀 Como Compilar Localmente

### Pré-requisitos
- **Rust Toolchain:** `rustc` e `cargo` instalados (versão estável recente, compatível com a release do Zed).
- **Git** e **Python 3**.
- Dependências de sistema do Zed:
  - **macOS:** Xcode, `cmake` (`brew install cmake`) e, no macOS 26+, o Metal Toolchain (`xcodebuild -downloadComponent MetalToolchain`).
  - **Linux:** Pacotes de desenvolvimento de vídeo e áudio (`libasound2-dev`, `libfontconfig1-dev`, `libwayland-dev`, `libxkbcommon-dev`, `libvulkan-dev`).

### Passo a Passo

1. **Clonar este repositório:**
   ```bash
   git clone https://github.com/andermoreira/zed-privacy.git
   cd zed-privacy
   ```

2. **Compilar a versão padrão (`v1.9.0`):**
   ```bash
   ./scripts/build.sh
   ```

3. **Compilar uma versão ou tag específica do Zed (ex: v1.9.0):**
   ```bash
   ./scripts/build.sh --tag v1.9.0
   ```

4. **Apenas aplicar os patches e inspecionar o código (sem disparar cargo build):**
   ```bash
   ./scripts/build.sh --tag v1.9.0 --skip-build
   ```

5. **Auditar o código patcheado:**
   ```bash
   python3 scripts/audit_network.py --source .zed-upstream
   ```

O binário final compilado estará disponível em `.zed-upstream/target/release/muted`. Nenhum bundle `.app` é gerado no macOS.

O Muted guarda configurações, dados e cache em diretórios próprios (`APP_NAME = "Muted"`), separados de uma instalação oficial do Zed; as configurações do Zed não são importadas.

---

## 🛡️ Matriz de Auditoria de Chamadas de Rede

Consulte [`docs/network-audit.md`](docs/network-audit.md) para a lista completa dos crates auditados, portas e URLs mapeadas no Zed original e como cada uma foi tratada.

---

## 📜 Licença

Os patches e scripts deste repositório estão licenciados sob a licença [Apache 2.0](LICENSE). O código-fonte do Zed upstream é distribuído sob suas respectivas licenças (GPL-3.0 / Apache-2.0 / AGPL-3.0).

Muted não é afiliado, endossado nem mantido pela Zed Industries, Inc. "Zed" e o logo do Zed são marcas da Zed Industries, Inc., citadas aqui apenas para identificar a origem do código.
