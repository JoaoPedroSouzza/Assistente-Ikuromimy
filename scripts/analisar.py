"""Verificações AST/symtable sem dependências; complementam o Ruff do CI."""
import ast
import builtins
import json
from pathlib import Path
import symtable
import sys

ROOT = Path(__file__).resolve().parents[1]


def analisar(path):
    texto = path.read_text(encoding="utf-8-sig")
    achados = []
    def registrar(linha, regra, mensagem):
        achados.append({"arquivo": path.relative_to(ROOT).as_posix(), "linha": linha,
                        "regra": regra, "mensagem": mensagem})
    try:
        tree = ast.parse(texto, filename=str(path), feature_version=(3, 10))
        tabela = symtable.symtable(texto, str(path), "exec")
    except SyntaxError as erro:
        registrar(erro.lineno, "SINTAXE", erro.msg)
        return achados
    globais = {s.get_name() for s in tabela.get_symbols() if s.is_assigned() or s.is_imported()}
    # Símbolo implícito criado pelo compilador do Python 3.14 (PEP 649).
    permitidos = globais | set(dir(builtins)) | {"__file__", "__name__", "__package__", "__class__", "__conditional_annotations__"}
    def simbolos(escopo):
        for simbolo in escopo.get_symbols():
            if simbolo.is_global() and simbolo.is_referenced() and simbolo.get_name() not in permitidos:
                registrar(escopo.get_lineno(), "NOME", f"Nome global não definido: {simbolo.get_name()}")
        for filho in escopo.get_children():
            simbolos(filho)
    simbolos(tabela)
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            registrar(node.lineno, "EXCEPT", "except sem tipo de exceção")
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
            registrar(node.lineno, "EXEC", "Execução dinâmica de código")
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in {"Popen", "run", "call", "check_output"}:
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        registrar(node.lineno, "SHELL", "shell=True não permitido")
            if node.func.attr == "urlopen":
                limites = [kw.value for kw in node.keywords if kw.arg == "timeout"]
                if not limites or any(isinstance(v, ast.Constant) and v.value is None for v in limites):
                    registrar(node.lineno, "TIMEOUT", "Requisição sem timeout finito explícito")
    return achados


def main():
    arquivos = [ROOT / "escravo.py", ROOT / "interface.py"]
    arquivos += sorted((ROOT / "core").rglob("*.py"))
    arquivos += sorted((ROOT / "ui").rglob("*.py"))
    achados = [a for path in arquivos for a in analisar(path)]
    relatorio = {"arquivos": len(arquivos), "achados": achados,
                 "escopo": "Sintaxe Python 3.10, nomes globais, except sem tipo, eval/exec, shell=True e timeout HTTP. Não substitui auditoria de segurança nem verificação de tipos."}
    destino = ROOT / "reports-pipeline" / "analise-estatica.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(relatorio, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(relatorio, indent=2, ensure_ascii=False))
    return bool(achados)


if __name__ == "__main__":
    sys.exit(main())
