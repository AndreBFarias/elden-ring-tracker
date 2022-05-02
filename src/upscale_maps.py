import argparse
import logging
import sys
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
MAP_TILES_DIR = ASSETS_DIR / "map_tiles"
MODELS_DIR = ASSETS_DIR / "models"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elden_tracker.upscale")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    _handler = RotatingFileHandler(
        LOG_DIR / "tracker.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(_handler)

TARGET_SIZE = (3040, 3165)

REGION_CONFIG = {
    "underground": {
        "input": "base-underground.webp",
        "output": "underground_upscaled.png",
        "model_name": "RealESRGAN_x4plus.pth",
        "model_url": (
            "https://github.com/xinntao/Real-ESRGAN/releases/download"
            "/v0.1.0/RealESRGAN_x4plus.pth"
        ),
        "scale": 4,
        "target_size": TARGET_SIZE,
    },
    "surface": {
        "input": "base.png",
        "output": "surface_upscaled.png",
        "resize_only": True,
        "target_size": TARGET_SIZE,
    },
}


def _download_model(name: str, url: str) -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    dest = MODELS_DIR / name
    if dest.exists():
        logger.info("Modelo ja existe: %s", dest)
        return dest

    logger.info("Baixando modelo %s ...", name)
    tmp = dest.with_suffix(".tmp")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp, open(str(tmp), "wb") as out:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 1024
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded / total * 100
                    logger.info("  %.1f%% (%d / %d bytes)", pct, downloaded, total)
        tmp.rename(dest)
        logger.info("Download concluido: %s (%.1f MB)", name, dest.stat().st_size / 1024 / 1024)
    except Exception as exc:
        logger.error("Falha ao baixar modelo: %s", exc)
        if tmp.exists():
            tmp.unlink()
        raise

    return dest


def _load_model(model_path: Path, device: str):
    import spandrel
    import torch

    logger.info("Carregando modelo: %s (device=%s)", model_path.name, device)
    loader = spandrel.ModelLoader(device=torch.device(device))
    model_desc = loader.load_from_file(str(model_path))
    model = model_desc.model
    model.eval()

    if device == "cuda":
        model = model.half()

    return model


def _blend_tile(
    output: np.ndarray,
    weight_map: np.ndarray,
    tile: np.ndarray,
    y_start: int,
    x_start: int,
) -> None:
    th, tw = tile.shape[:2]
    y_end = y_start + th
    x_end = x_start + tw

    wy = np.hanning(th).astype(np.float32)
    wy = np.clip(wy, 0.01, 1.0)
    wx = np.hanning(tw).astype(np.float32)
    wx = np.clip(wx, 0.01, 1.0)

    weight = np.outer(wy, wx)

    if tile.ndim == 3:
        output[y_start:y_end, x_start:x_end] += tile.astype(np.float64) * weight[:, :, np.newaxis]
    else:
        output[y_start:y_end, x_start:x_end] += tile.astype(np.float64) * weight

    weight_map[y_start:y_end, x_start:x_end] += weight


def _upscale_tiled(
    model,
    image_np: np.ndarray,
    scale: int,
    tile_size: int,
    overlap: int,
    device: str,
) -> np.ndarray:
    import torch

    h, w, c = image_np.shape
    out_h = h * scale
    out_w = w * scale

    output = np.zeros((out_h, out_w, c), dtype=np.float64)
    weight_map = np.zeros((out_h, out_w), dtype=np.float64)

    step = tile_size - overlap
    tiles_y = max(1, (h - overlap + step - 1) // step)
    tiles_x = max(1, (w - overlap + step - 1) // step)
    total_tiles = tiles_y * tiles_x
    logger.info("Processando %d tiles (%dx%d grid)", total_tiles, tiles_x, tiles_y)

    processed = 0
    for iy in range(tiles_y):
        for ix in range(tiles_x):
            y0 = min(iy * step, h - tile_size) if h > tile_size else 0
            x0 = min(ix * step, w - tile_size) if w > tile_size else 0
            y1 = min(y0 + tile_size, h)
            x1 = min(x0 + tile_size, w)

            tile = image_np[y0:y1, x0:x1]
            tile_t = torch.from_numpy(tile.transpose(2, 0, 1)).float() / 255.0
            tile_t = tile_t.unsqueeze(0)

            if device == "cuda":
                tile_t = tile_t.half()

            tile_t = tile_t.to(device)

            with torch.no_grad():
                result = model(tile_t)

            result_np = result.squeeze(0).cpu().float().numpy()
            result_np = np.clip(result_np.transpose(1, 2, 0) * 255.0, 0, 255)

            out_y0 = y0 * scale
            out_x0 = x0 * scale

            _blend_tile(output, weight_map, result_np, out_y0, out_x0)

            processed += 1
            if processed % 10 == 0 or processed == total_tiles:
                logger.info("  Tile %d/%d (%.0f%%)", processed, total_tiles, processed / total_tiles * 100)

            del tile_t, result
            if device == "cuda":
                torch.cuda.empty_cache()

    weight_mask = weight_map > 0
    for ch in range(c):
        output[:, :, ch][weight_mask] /= weight_map[weight_mask]

    return np.clip(output, 0, 255).astype(np.uint8)


def _upscale_image(
    model,
    input_path: Path,
    output_path: Path,
    scale: int,
    tile_size: int,
    overlap: int,
    device: str,
    target_size: tuple[int, int] | None = None,
) -> None:
    logger.info("Abrindo imagem: %s", input_path)
    with Image.open(str(input_path)) as img:
        has_alpha = img.mode == "RGBA"

        if has_alpha:
            logger.info("Imagem RGBA detectada - separando canal alpha")
            alpha = img.split()[3].copy()
            rgb = img.convert("RGB")
        else:
            rgb = img.convert("RGB")
            alpha = None

        rgb_np = np.array(rgb)

    logger.info("Dimensoes de entrada: %dx%d", rgb_np.shape[1], rgb_np.shape[0])

    result_np = _upscale_tiled(model, rgb_np, scale, tile_size, overlap, device)
    logger.info("Dimensoes de saida: %dx%d", result_np.shape[1], result_np.shape[0])

    result_img = Image.fromarray(result_np)

    if has_alpha:
        new_size = (result_np.shape[1], result_np.shape[0])
        alpha_up = alpha.resize(new_size, Image.NEAREST)
        result_img.putalpha(alpha_up)
        logger.info("Canal alpha recomposto via NEAREST")

    if target_size:
        logger.info("Redimensionando para %dx%d via LANCZOS", target_size[0], target_size[1])
        result_img = result_img.resize(target_size, Image.LANCZOS)

    result_img.save(str(output_path), "PNG", optimize=True)
    size_mb = output_path.stat().st_size / 1024 / 1024
    logger.info("Salvo: %s (%.1f MB)", output_path, size_mb)


def _resize_image(
    input_path: Path,
    output_path: Path,
    target_size: tuple[int, int],
) -> None:
    Image.MAX_IMAGE_PIXELS = None
    logger.info("Redimensionando %s para %dx%d via LANCZOS", input_path.name, target_size[0], target_size[1])
    with Image.open(str(input_path)) as img:
        logger.info("Dimensoes de entrada: %dx%d", img.width, img.height)
        result = img.resize(target_size, Image.LANCZOS)
    result.save(str(output_path), "PNG", optimize=True)
    size_mb = output_path.stat().st_size / 1024 / 1024
    logger.info("Salvo: %s (%.1f MB)", output_path, size_mb)


def _lanczos_fallback(input_path: Path, output_path: Path, scale: int) -> None:
    logger.info("Fallback LANCZOS: %s (escala %dx)", input_path.name, scale)
    with Image.open(str(input_path)) as img:
        new_size = (img.width * scale, img.height * scale)
        result = img.resize(new_size, Image.LANCZOS)
    result.save(str(output_path), "PNG", optimize=True)
    size_mb = output_path.stat().st_size / 1024 / 1024
    logger.info("Fallback salvo: %s (%.1f MB)", output_path, size_mb)


def main() -> None:
    parser = argparse.ArgumentParser(description="Upscale neural dos mapas de Elden Ring")
    parser.add_argument(
        "--regions",
        nargs="+",
        choices=list(REGION_CONFIG.keys()),
        default=list(REGION_CONFIG.keys()),
        help="Regioes para processar (padrao: todas)",
    )
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="Usar LANCZOS em vez de upscale neural",
    )
    parser.add_argument(
        "--tile-size",
        type=int,
        default=512,
        help="Tamanho dos tiles para inferência (padrão: 512)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=32,
        help="Sobreposição entre tiles em pixels (padrão: 32)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocessar mesmo se a imagem upscaled já existe",
    )
    args = parser.parse_args()

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(console)

    device = "cpu"
    if not args.fallback:
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
                gpu_name = torch.cuda.get_device_name(0)
                vram = torch.cuda.get_device_properties(0).total_memory / 1024 / 1024 / 1024
                logger.info("GPU detectada: %s (%.2f GB VRAM)", gpu_name, vram)
            else:
                logger.warning("CUDA não disponível, usando CPU (será lento)")
        except ImportError:
            logger.warning("PyTorch não instalado, usando fallback LANCZOS")
            args.fallback = True

    loaded_models: dict[str, object] = {}

    for region_name in args.regions:
        config = REGION_CONFIG[region_name]
        input_path = MAP_TILES_DIR / config["input"]
        output_path = MAP_TILES_DIR / config["output"]

        if output_path.exists() and not args.force:
            logger.info("Imagem upscaled já existe: %s (use --force para reprocessar)", output_path)
            continue

        if not input_path.exists():
            logger.error("Imagem de entrada não encontrada: %s", input_path)
            continue

        logger.info("=== Processando região: %s ===", region_name)
        logger.info("Entrada: %s", input_path)
        logger.info("Saída: %s", output_path)

        if config.get("resize_only"):
            _resize_image(input_path, output_path, config["target_size"])
        elif args.fallback:
            _lanczos_fallback(input_path, output_path, config["scale"])
        else:
            logger.info("Escala: %dx", config["scale"])
            model_name = config["model_name"]
            if model_name not in loaded_models:
                model_path = _download_model(model_name, config["model_url"])
                loaded_models[model_name] = _load_model(model_path, device)

            model = loaded_models[model_name]
            _upscale_image(
                model,
                input_path,
                output_path,
                config["scale"],
                args.tile_size,
                args.overlap,
                device,
                target_size=config.get("target_size"),
            )

        if device == "cuda":
            import torch
            torch.cuda.empty_cache()

    logger.info("=== Upscale concluído ===")


if __name__ == "__main__":
    main()


# "A perfeição não é alcançada quando não há mais nada a acrescentar, mas quando não há mais nada a retirar." -- Antoine de Saint-Exupéry
