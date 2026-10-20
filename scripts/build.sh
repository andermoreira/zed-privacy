#!/usr/bin/env bash
set -euo pipefail

# Muted - Build Script
# Clones upstream Zed, applies privacy-first patches, audits, and builds.

UPSTREAM_REPO="https://github.com/zed-industries/zed.git"
DEFAULT_TAG="v1.9.0"
TARGET_TAG="${DEFAULT_TAG}"
SKIP_BUILD=false
CLEAN_BUILD=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
UPSTREAM_DIR="${ROOT_DIR}/.zed-upstream"
PATCHES_DIR="${ROOT_DIR}/patches"

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --tag <tag>       Zed git tag to checkout and patch (default: ${DEFAULT_TAG})"
    echo "  --skip-build      Only clone, apply patches, and audit (skips cargo build)"
    echo "  --clean           Remove existing .zed-upstream directory before starting"
    echo "  --help            Show this help message"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tag)
            if [[ $# -lt 2 || -z "$2" ]]; then
                echo "❌ Error: --tag requires a value." >&2
                exit 2
            fi
            TARGET_TAG="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ ! "${TARGET_TAG}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.]+)?$ ]]; then
    echo "❌ Error: Invalid tag '${TARGET_TAG}' (expected e.g. v1.9.0)." >&2
    exit 2
fi

echo "=========================================================="
echo "                 Muted - Build System                     "
echo "=========================================================="
echo "Target Tag:    ${TARGET_TAG}"
echo "Skip Build:    ${SKIP_BUILD}"
echo "Upstream Dir:  ${UPSTREAM_DIR}"
echo "Patches Dir:   ${PATCHES_DIR}"
echo "=========================================================="

# Check requirements
for cmd in git python3; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "❌ Error: '$cmd' is not installed or not in PATH."
        exit 1
    fi
done

if [[ "${SKIP_BUILD}" == "false" ]]; then
    for cmd in rustc cargo; do
        if ! command -v "$cmd" &>/dev/null; then
            echo "❌ Error: '$cmd' is required for building. Install Rust from https://rustup.rs"
            exit 1
        fi
    done
fi

if [[ "${CLEAN_BUILD}" == "true" && -d "${UPSTREAM_DIR}" ]]; then
    echo "🧹 Cleaning previous upstream directory..."
    rm -rf "${UPSTREAM_DIR}"
fi

# Clone upstream if not present
if [[ ! -d "${UPSTREAM_DIR}/.git" ]]; then
    echo "📥 Cloning Zed upstream tag ${TARGET_TAG} (shallow)..."
    git clone --depth 1 --branch "${TARGET_TAG}" "${UPSTREAM_REPO}" "${UPSTREAM_DIR}"
else
    echo "🔄 Updating existing upstream repository..."
    if ! git -C "${UPSTREAM_DIR}" rev-parse -q --verify "refs/tags/${TARGET_TAG}" >/dev/null; then
        git -C "${UPSTREAM_DIR}" fetch --depth 1 origin tag "${TARGET_TAG}"
    fi
fi

# Apply patches
echo "🩹 Applying privacy patches..."
cd "${UPSTREAM_DIR}"
git checkout -f "${TARGET_TAG}"
git clean -fd

for patch in "${PATCHES_DIR}"/*.patch; do
    if [[ -f "$patch" ]]; then
        patch_name="$(basename "$patch")"
        echo "   -> Applying patch: ${patch_name}"
        if ! git apply "$patch"; then
            echo "❌ Failed to apply patch cleanly: ${patch_name}" >&2
            exit 1
        fi
        echo "      ✅ Applied cleanly."
    fi
done

cd "${ROOT_DIR}"

# Run static audit
echo ""
echo "🔬 Running privacy audit..."
python3 "${SCRIPT_DIR}/audit_network.py" --source "${UPSTREAM_DIR}"

# Build binary
if [[ "${SKIP_BUILD}" == "true" ]]; then
    echo ""
    echo "✅ Setup and audit completed. Build skipped as requested (--skip-build)."
    exit 0
fi

echo ""
echo "⚙️  Compiling Muted release binary with Cargo (this may take several minutes)..."
cd "${UPSTREAM_DIR}"
cargo build --release --package zed

echo ""
echo "=========================================================="
echo "🎉 Build completed successfully!"
echo "Binary located at: ${UPSTREAM_DIR}/target/release/muted"
echo "=========================================================="
