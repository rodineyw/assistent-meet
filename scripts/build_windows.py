import os
import shutil
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "build"
ASSETS_DIR = BUILD_DIR / "assets"
INSTALLER_DIR = ROOT / "dist-installer"


def load_project_metadata():
    pyproject_path = ROOT / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    project = data["project"]
    return {
        "name": project["name"],
        "version": project["version"],
        "display_name": "Assistente Meet",
        "publisher": "Assistente Meet",
        "app_id": "com.assistentmeet.desktop",
        "installer_guid": "1C57A4CA-3E10-4C3C-A1F3-CA6D34E8E0F3",
    }


def find_svg_icon():
    for name in ("icone.svg", "icon.svg"):
        path = ROOT / "ui" / name
        if path.exists():
            return path
    raise FileNotFoundError("Nenhum arquivo SVG de icone foi encontrado em ui/icone.svg ou ui/icon.svg.")


def ensure_clean_dirs():
    for path in (BUILD_DIR, INSTALLER_DIR):
        path.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def build_windows_icon(svg_path, ico_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    app = QGuiApplication.instance() or QGuiApplication(["build-icon", "-platform", "offscreen"])
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise RuntimeError(f"Falha ao carregar SVG do icone: {svg_path}")

    image = QImage(256, 256, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    if not image.save(str(ico_path)):
        raise RuntimeError(f"Falha ao gerar arquivo ICO em {ico_path}")

    return app


def find_pyinstaller():
    venv_candidate = ROOT / ".venv" / "Scripts" / "pyinstaller.exe"
    if venv_candidate.exists():
        return venv_candidate

    system_candidate = shutil.which("pyinstaller")
    if system_candidate:
        return Path(system_candidate)

    raise FileNotFoundError("PyInstaller nao encontrado. Rode `uv sync --dev` antes do build.")


def run_pyinstaller(pyinstaller_path, icon_path, display_name):
    cmd = [
        str(pyinstaller_path),
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        display_name,
        "--icon",
        str(icon_path),
        "--hidden-import",
        "PySide6.QtSvg",
        "--additional-hooks-dir",
        str(ROOT / "hooks"),
        "--add-data",
        f"{ROOT / 'ui'};ui",
        str(ROOT / "main.py"),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)


def write_inno_script(metadata, icon_path):
    script_path = BUILD_DIR / "AssistenteMeet.generated.iss"
    dist_dir = ROOT / "dist" / metadata["display_name"]
    output_name = f"Assistente-Meet-Setup-{metadata['version']}"

    script = textwrap.dedent(
        f"""
        #define MyAppName "{metadata['display_name']}"
        #define MyAppVersion "{metadata['version']}"
        #define MyAppPublisher "{metadata['publisher']}"
        #define MyAppExeName "{metadata['display_name']}.exe"

        [Setup]
        AppId={{{metadata['installer_guid']}}}
        AppName={{#MyAppName}}
        AppVersion={{#MyAppVersion}}
        AppPublisher={{#MyAppPublisher}}
        DefaultDirName={{localappdata}}\\Programs\\{{#MyAppName}}
        DefaultGroupName={{#MyAppName}}
        DisableProgramGroupPage=yes
        OutputDir={INSTALLER_DIR}
        OutputBaseFilename={output_name}
        SetupIconFile={icon_path}
        WizardStyle=modern
        Compression=lzma
        SolidCompression=yes
        ArchitecturesAllowed=x64compatible
        ArchitecturesInstallIn64BitMode=x64compatible
        PrivilegesRequired=lowest
        UninstallDisplayIcon={{app}}\\{{#MyAppExeName}}

        [Tasks]
        Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"

        [Files]
        Source: "{dist_dir}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

        [Icons]
        Name: "{{autoprograms}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
        Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

        [Run]
        Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "Iniciar {{#MyAppName}}"; Flags: nowait postinstall skipifsilent
        """
    ).strip() + "\n"

    script_path.write_text(script, encoding="utf-8")
    return script_path


def try_build_installer(script_path):
    iscc_path = shutil.which("iscc")
    if not iscc_path:
        print("Inno Setup nao encontrado. O app portatil foi gerado em dist/, mas o instalador nao foi compilado.")
        print(f"Para gerar o instalador, instale o Inno Setup e rode novamente este script.")
        print(f"O script pronto ficou em: {script_path}")
        return False

    subprocess.run([iscc_path, str(script_path)], cwd=ROOT, check=True)
    return True


def main():
    metadata = load_project_metadata()
    ensure_clean_dirs()

    svg_path = find_svg_icon()
    ico_path = ASSETS_DIR / "assistente-meet.ico"
    build_windows_icon(svg_path, ico_path)

    pyinstaller_path = find_pyinstaller()
    run_pyinstaller(pyinstaller_path, ico_path, metadata["display_name"])

    script_path = write_inno_script(metadata, ico_path)
    installer_built = try_build_installer(script_path)

    print(f"Build PyInstaller concluido: {ROOT / 'dist' / metadata['display_name']}")
    if installer_built:
        print(f"Instalador gerado em: {INSTALLER_DIR}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"Falha no build: {exc}", file=sys.stderr)
        raise SystemExit(exc.returncode)
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(1)
