# PowerShell 5.1 ou superior. Envia main + tag, sem force push.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$tag = 'v1.19.0'
$repo = 'JoaoPedroSouzza/Assistente-Ikuromimy'
$title = 'IKUROMIMY v1.19.0 — Interface reativa e novo núcleo visual da IA'

function Invoke-GitChecked {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArgs)
    & git @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Git falhou: git $($GitArgs -join ' '). Nenhum force push será feito."
    }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Instale o Git antes de continuar.' }
$branch = (Invoke-GitChecked branch --show-current | Out-String).Trim()
if ($branch -ne 'main') { throw "Branch atual: $branch. Este script espera main." }
$origin = (Invoke-GitChecked remote get-url origin | Out-String).Trim().TrimEnd('/')
if ($origin -notin @("https://github.com/$repo", "https://github.com/$repo.git", "git@github.com:$repo.git")) {
    throw "O origin aponta para outro repositório: $origin"
}
$versionFile = Get-Content -LiteralPath 'ui/version.py' -Raw
if ($versionFile -notmatch 'VERSAO\s*=\s*"1\.19\.0"') { throw 'A versão do código não é 1.19.0.' }
$conflicts = @(Invoke-GitChecked diff --name-only --diff-filter=U)
if ($conflicts.Count -gt 0) { throw 'Existem conflitos de merge. Resolva-os antes de publicar.' }
if ((Test-Path -LiteralPath '.git/MERGE_HEAD') -or (Test-Path -LiteralPath '.git/rebase-merge') -or (Test-Path -LiteralPath '.git/rebase-apply')) {
    throw 'Há uma integração em andamento. Conclua-a antes de publicar.'
}

Invoke-GitChecked fetch origin
& git merge-base --is-ancestor origin/main HEAD
if ($LASTEXITCODE -ne 0) {
    throw 'O GitHub contém commits ainda não integrados nesta cópia. Pare aqui e envie a saída de git status -sb e git log --oneline --left-right HEAD...origin/main.'
}

# Aplica o .gitignore também a arquivos gerados que já estavam rastreados.
$ignored = @(Invoke-GitChecked ls-files -ci --exclude-standard)
foreach ($path in $ignored) { Invoke-GitChecked rm --cached -- $path }
Invoke-GitChecked add --all
Invoke-GitChecked diff --cached --stat
& git diff --cached --quiet
$diffExit = $LASTEXITCODE
if ($diffExit -eq 1) {
    Invoke-GitChecked commit -m 'feat: lança v1.19.0 com redesign reativo da interface'
} elseif ($diffExit -ne 0) {
    throw 'Falha ao verificar o conteúdo do commit.'
}

$localTag = @(Invoke-GitChecked tag --list $tag)
if ($localTag.Count -eq 0) {
    Invoke-GitChecked tag -a $tag -m $title
} else {
    $tagCommit = (Invoke-GitChecked rev-parse "$tag^{commit}" | Out-String).Trim()
    $headCommit = (Invoke-GitChecked rev-parse HEAD | Out-String).Trim()
    if ($tagCommit -ne $headCommit) { throw "A tag $tag já aponta para outro commit. Ela não será substituída." }
}

# Atualiza branch e tag juntas; uma rejeição impede o envio parcial.
Invoke-GitChecked push --atomic origin 'HEAD:refs/heads/main' "refs/tags/$tag"
Write-Host "Código e tag $tag enviados com sucesso."
Write-Host 'Acompanhe os testes e o build:'
Write-Host "https://github.com/$repo/actions"
Write-Host ''
Write-Host 'Crie a release com o título e a descrição de RELEASE-1.19.0.md:'
Write-Host "https://github.com/$repo/releases/new?tag=$tag"
Write-Host 'Espere o Actions concluir e anexe o EXE novo e SHA256.txt antes de publicar a release.'
