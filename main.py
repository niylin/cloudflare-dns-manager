# main.py
import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Cloudflare DNS Manager")
    parser.add_argument("--cli", action="store_true",
                        help="Run in CLI mode")
    args = parser.parse_args()

    if args.cli:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cli_script = os.path.join(script_dir, "cli-manager.py")
        sys.exit(subprocess.call([sys.executable, cli_script]))
    else:
        import gi
        gi.require_version('Gtk', '4.0')
        gi.require_version('Adw', '1')
        from gi.repository import GLib, Adw
        from app_controller import AppController

        GLib.set_prgname("cloudflare-dns-manager")

        app = Adw.Application(
            application_id="org.niylin.cloudflare-dns-manager"
        )
        controller = AppController(app)
        sys.exit(app.run(None))


if __name__ == "__main__":
    main()