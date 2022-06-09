.PHONY: setup run run-tray lint format clean db-reset tiles-check tiles-download deb appimage flatpak all-packages clean-packages

setup:
	bash setup.sh

run:
	bash run.sh

run-tray:
	bash run.sh --tray

lint:
	.venv/bin/ruff check src/

format:
	.venv/bin/ruff format src/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find logs/ -name "*.log" -mtime +30 -delete 2>/dev/null || true
	@echo "Limpeza concluída."

db-reset:
	@read -p "Remover tracker.db? [s/N] " confirm; \
	if [ "$$confirm" = "s" ] || [ "$$confirm" = "S" ]; then \
		rm -f data/tracker.db; \
		echo "Banco removido."; \
	else \
		echo "Cancelado."; \
	fi

tiles-check:
	.venv/bin/python3 scripts/download_tiles.py --check

tiles-download:
	.venv/bin/python3 scripts/download_tiles.py

deb:
	dpkg-buildpackage -us -uc -b

appimage:
	bash packaging/appimage/build-appimage.sh

flatpak:
	flatpak-builder --force-clean build-flatpak packaging/flatpak/com.github.andrefarias.EldenRingTracker.yml

all-packages: deb appimage flatpak

clean-packages:
	rm -rf build-flatpak .flatpak-builder flatpak-repo
	rm -f *.deb *.AppImage *.flatpak
	@echo "Artefatos de build removidos."
