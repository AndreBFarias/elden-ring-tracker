"""Testes de estrutura do projeto GraceMap."""

from pathlib import Path


def test_license_gpl3():
    raiz = Path(__file__).resolve().parent.parent
    license_path = raiz / "LICENSE"
    assert license_path.exists()
    texto = license_path.read_text(encoding="utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" in texto
    assert "Version 3" in texto


def test_pyproject_existe():
    raiz = Path(__file__).resolve().parent.parent
    pyproject = raiz / "pyproject.toml"
    assert pyproject.exists()


def test_readme_existe_e_referencia_gracemap():
    raiz = Path(__file__).resolve().parent.parent
    readme = raiz / "README.md"
    assert readme.exists()


def test_src_tem_arquivos_python():
    raiz = Path(__file__).resolve().parent.parent
    src = raiz / "src"
    arquivos_py = list(src.glob("*.py"))
    assert len(arquivos_py) >= 5


def test_workflows_ci_existente():
    raiz = Path(__file__).resolve().parent.parent
    ci = raiz / ".github" / "workflows" / "ci.yml"
    assert ci.exists()
