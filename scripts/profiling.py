import argparse
import ast
import cProfile
import difflib
from functools import lru_cache
import json
from pathlib import Path
import re
import statistics
import time

parser = argparse.ArgumentParser(description='Mede a interpretação de comandos, sem executar ações do assistente.')
parser.add_argument('projeto', nargs='?', type=Path, default=Path(__file__).resolve().parents[1],
                    help='Pasta do projeto (padrão: pasta que contém este script).')
parser.add_argument('saida', nargs='?', type=Path,
                    help='Arquivo JSON de saída (padrão: reports-pipeline/benchmark-atual.json no projeto).')
args = parser.parse_args()
root = args.projeto.resolve()
output = (args.saida or root / 'reports-pipeline' / 'benchmark-atual.json').resolve()
source = root / 'core' / 'comandos.py'
if not source.exists():
    source = root / 'escravo.py'
if not source.is_file():
    parser.error(f'Projeto inválido: não encontrei core/comandos.py nem escravo.py em {root}')
tree = ast.parse(source.read_text(encoding='utf-8'))
names = {'contem_palavra', 'extrair_alvo', '_tentar_corrigir_comando', 'eh_comando_conhecido', '_corrigir_palavra'}
nodes = [node for node in tree.body if
         (isinstance(node, ast.FunctionDef) and node.name in names) or
         (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PALAVRAS_CHAVE_CONHECIDAS' for t in node.targets))]
scope = {'re': re, 'difflib': difflib, 'lru_cache': lru_cache}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), scope)
samples = ['play', 'abrir editor', 'abrri editor', 'pesqusiar gatos', 'uma conversa normal', 'banana']
def workload():
    return sum(scope['eh_comando_conhecido'](s) for _ in range(1000) for s in samples)
times = []
for _ in range(5):
    start = time.perf_counter()
    assert workload() == 4000
    times.append(time.perf_counter() - start)
output.parent.mkdir(parents=True, exist_ok=True)
prof = cProfile.Profile()
prof.runcall(workload)
prof.dump_stats(str(output.with_suffix('.prof')))
result = {'source': str(source.relative_to(root)), 'classifications_per_run': 6000,
          'runs_seconds': times, 'median_seconds': statistics.median(times),
          'scenario': 'Interpretação pura, 6 frases repetidas; não mede ações externas nem latência da UI.'}
output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(result))
