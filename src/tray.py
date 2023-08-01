import os
import signal
import subprocess
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from log import LOG_DIR, get_logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent

logger = get_logger("tray")

DASHBOARD_URL = "http://localhost:8501"
ICON_PATH = PROJECT_ROOT / "assets" / "icons" / "icon.png"

_streamlit_process: subprocess.Popen | None = None


def _load_icon():
    from PIL import Image, ImageDraw

    size = 64
    if ICON_PATH.exists():
        base = Image.open(str(ICON_PATH)).resize((size, size)).convert("RGBA")
    else:
        base = Image.new("RGBA", (size, size), (40, 42, 54, 255))

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)

    circular = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    circular.paste(base, mask=mask)
    return circular


def _open_dashboard(*_args) -> None:
    logger.info("Abrindo dashboard: %s", DASHBOARD_URL)
    webbrowser.open(DASHBOARD_URL)


def _wait_and_open_browser() -> None:
    for _ in range(120):
        try:
            urllib.request.urlopen(DASHBOARD_URL, timeout=1)
            _open_dashboard()
            return
        except Exception:
            time.sleep(1)
    logger.warning("Timeout aguardando streamlit iniciar (120s)")


def _start_streamlit() -> None:
    global _streamlit_process
    if _streamlit_process and _streamlit_process.poll() is None:
        logger.info("Streamlit ja em execucao (PID %d)", _streamlit_process.pid)
        return

    run_script = PROJECT_ROOT / "run.sh"
    if not run_script.exists():
        logger.error("run.sh nao encontrado: %s", run_script)
        return

    log_dir = LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "streamlit.log"
    with open(str(log_file), "a", encoding="utf-8") as lf:
        _streamlit_process = subprocess.Popen(
            ["bash", str(run_script), "--headless"],
            cwd=str(PROJECT_ROOT),
            stdout=lf,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
        )
    logger.info("Streamlit iniciado (PID %d)", _streamlit_process.pid)


def _stop_streamlit() -> None:
    global _streamlit_process
    if _streamlit_process and _streamlit_process.poll() is None:
        try:
            os.killpg(os.getpgid(_streamlit_process.pid), signal.SIGTERM)
            _streamlit_process.wait(timeout=10)
            logger.info("Streamlit encerrado")
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(os.getpgid(_streamlit_process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            logger.warning("Streamlit forcado a encerrar (SIGKILL)")
    _streamlit_process = None


def _restart_streamlit(*_args) -> None:
    logger.info("Reiniciando streamlit")
    _stop_streamlit()
    _start_streamlit()


def _quit_app(icon, *_args) -> None:
    logger.info("Encerrando aplicacao")
    _stop_streamlit()
    icon.stop()


def run_tray() -> None:
    import pystray

    logger.info("Iniciando system tray")

    _start_streamlit()
    threading.Thread(target=_wait_and_open_browser, daemon=True).start()

    icon_image = _load_icon()
    menu = pystray.Menu(
        pystray.MenuItem("Abrir Dashboard", _open_dashboard, default=True),
        pystray.MenuItem("Reiniciar", _restart_streamlit),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Fechar", _quit_app),
    )

    icon = pystray.Icon(
        name="elden-ring-tracker",
        icon=icon_image,
        title="Elden Ring Tracker",
        menu=menu,
    )

    def _cleanup(signum, frame):
        logger.info("Sinal %d recebido, encerrando", signum)
        _stop_streamlit()
        icon.stop()

    signal.signal(signal.SIGTERM, _cleanup)
    signal.signal(signal.SIGINT, _cleanup)

    logger.info("System tray ativo")
    icon.run()


if __name__ == "__main__":
    run_tray()


# "A liberdade e o oxigenio da alma." -- Moshe Dayan
