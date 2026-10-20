import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import audit_network  # noqa: E402

PATCHED = {
    "assets/settings/default.json": """  "telemetry": {
    // Send debug info like crash reports.
    "diagnostics": false,
    // Send anonymized usage data like what languages you're using Zed with.
    "metrics": false,
  },
  "auto_update": false,
  "auto_install_extensions": {
    "html": false,
  },
""",
    "crates/telemetry/src/telemetry.rs": """pub fn send_event(_event: Event) {
}
pub fn init(_tx: mpsc::UnboundedSender<Event>) {
}
""",
    "crates/client/src/telemetry.rs": """pub static MINIDUMP_ENDPOINT: LazyLock<Option<String>> = LazyLock::new(|| None);
        // Privacy: Network flush is completely disabled.
        drop((json_bytes, request_body));
""",
    "crates/zed/src/reliability.rs": """    // Privacy: Remote minidump upload task disabled.
""",
    "crates/paths/src/paths.rs": """pub const APP_NAME: &str = "Muted";
""",
    "crates/extension_host/src/extension_host.rs": """            .join(",");
        if extension_ids.is_empty() {
            return Task::ready(Ok(Vec::new()));
        }
""",
    "crates/project/src/agent_registry_store.rs": """        let store = cx.new(|cx| Self::new(fs, http_client, cx));
        cx.set_global(GlobalAgentRegistryStore(store.clone()));

        store
    }
""",
    "crates/zed/src/zed/mac_only_instance.rs": """// Muted: offset the single-instance port range so it never hands off to Zed.
const MUTED_PORT_OFFSET: u16 = 4000;
    let port = MUTED_PORT_OFFSET
        + match *release_channel::RELEASE_CHANNEL {
""",
    "crates/zed/Cargo.toml": """[[bin]]
name = "muted"
path = "src/main.rs"

[package.metadata.bundle-stable]
identifier = "io.github.andermoreira.Muted"
name = "Muted"
osx_url_schemes = ["muted"]
""",
}


def audit(files: dict) -> bool:
    with tempfile.TemporaryDirectory() as root:
        for rel, content in files.items():
            path = Path(root, rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        with contextlib.redirect_stdout(io.StringIO()):
            return audit_network.run_audit(root)


class AuditNetworkTest(unittest.TestCase):
    def test_patched_tree_passes(self):
        self.assertTrue(audit(PATCHED))

    def test_unpatched_settings_fail(self):
        files = dict(PATCHED)
        files["assets/settings/default.json"] = files[
            "assets/settings/default.json"
        ].replace('"metrics": false', '"metrics": true')
        self.assertFalse(audit(files))

    def test_html_extension_auto_install_fails(self):
        files = dict(PATCHED)
        files["assets/settings/default.json"] = files[
            "assets/settings/default.json"
        ].replace('"html": false', '"html": true')
        self.assertFalse(audit(files))

    def test_upstream_app_name_fails(self):
        files = dict(PATCHED)
        files["crates/paths/src/paths.rs"] = 'pub const APP_NAME: &str = "Zed";\n'
        self.assertFalse(audit(files))

    def test_upstream_binary_name_fails(self):
        files = dict(PATCHED)
        files["crates/zed/Cargo.toml"] = files["crates/zed/Cargo.toml"].replace(
            'name = "muted"\npath', 'name = "zed"\npath'
        )
        self.assertFalse(audit(files))

    def test_upstream_bundle_identifier_fails(self):
        files = dict(PATCHED)
        files["crates/zed/Cargo.toml"] = files["crates/zed/Cargo.toml"].replace(
            "io.github.andermoreira.Muted", "dev.zed.Zed"
        )
        self.assertFalse(audit(files))

    def test_shared_single_instance_port_fails(self):
        files = dict(PATCHED)
        files["crates/zed/src/zed/mac_only_instance.rs"] = (
            "    let port = match *release_channel::RELEASE_CHANNEL {\n"
        )
        self.assertFalse(audit(files))

    def test_extension_update_check_without_extensions_fails(self):
        files = dict(PATCHED)
        files["crates/extension_host/src/extension_host.rs"] = "            .join(\",\");\n"
        self.assertFalse(audit(files))

    def test_registry_fetch_on_init_fails(self):
        files = dict(PATCHED)
        files["crates/project/src/agent_registry_store.rs"] += (
            "            if store.agents.is_empty() {\n                store.refresh(cx);\n"
        )
        self.assertFalse(audit(files))

    def test_missing_file_fails(self):
        files = dict(PATCHED)
        del files["crates/zed/src/reliability.rs"]
        self.assertFalse(audit(files))

    def test_flush_still_sending_fails_despite_marker(self):
        files = dict(PATCHED)
        files["crates/client/src/telemetry.rs"] += (
            "        let response = self.http_client.send(request).await?;\n"
        )
        self.assertFalse(audit(files))

    def test_minidump_upload_still_spawned_fails_despite_marker(self):
        files = dict(PATCHED)
        files["crates/zed/src/reliability.rs"] += (
            "            upload_previous_minidumps(client).await.warn_on_err();\n"
        )
        self.assertFalse(audit(files))

    def test_telemetry_queue_still_fed_fails_despite_marker(self):
        files = dict(PATCHED)
        files["crates/telemetry/src/telemetry.rs"] += (
            "        queue.unbounded_send(event).ok();\n"
        )
        self.assertFalse(audit(files))


if __name__ == "__main__":
    unittest.main()
