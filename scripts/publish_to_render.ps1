param(
    [string]$RepoUrl = ""
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Require-Command {
    param([string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Required command not found: $Name"
    }
}

function Ensure-Git {
    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    if ($gitCmd) {
        return
    }

    Write-Host "Git is not installed. Trying automatic install with winget..."
    $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
    if ($wingetCmd) {
        try {
            winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements | Out-Host
        } catch {
        }
    }

    # Refresh PATH for current process (machine + user)
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($machinePath -or $userPath) {
        $env:Path = (($machinePath, $userPath) -join ';')
    }

    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    if ($gitCmd) {
        Write-Host "Git installed successfully."
        return
    }

    Write-Host "Automatic Git install did not complete. Opening Git download page..."
    Start-Process "https://git-scm.com/download/win"
    throw "Git is still not available. Install Git from the page that opened, then run RUN_DEPLOY_RENDER.cmd again."
}

Ensure-Git

if (-not (Test-Path (Join-Path $root '.git'))) {
    git init | Out-Host
}

$gitUserName = git config user.name
$gitUserEmail = git config user.email

if (-not $gitUserName) {
    $name = Read-Host "Enter your Git user.name"
    if ($name) { git config user.name "$name" | Out-Host }
}
if (-not $gitUserEmail) {
    $email = Read-Host "Enter your Git user.email"
    if ($email) { git config user.email "$email" | Out-Host }
}

# Ensure main branch
try { git branch -M main | Out-Null } catch {}

git add .

$hasChanges = git status --porcelain
if ($hasChanges) {
    git commit -m "Prepare Render deployment" | Out-Host
} else {
    Write-Host "No new changes to commit."
}

$existingRemote = (& git remote get-url origin 2>$null)
if ($LASTEXITCODE -ne 0) {
    $existingRemote = $null
}
if (-not $RepoUrl -and -not $existingRemote) {
    $RepoUrl = Read-Host "Paste your GitHub repo URL (example: https://github.com/USERNAME/grades4.git)"
}

if ($RepoUrl) {
    if ($existingRemote) {
        git remote set-url origin "$RepoUrl" | Out-Host
    } else {
        git remote add origin "$RepoUrl" | Out-Host
    }
}

$remoteAfter = (& git remote get-url origin 2>$null)
if ($LASTEXITCODE -ne 0) {
    $remoteAfter = $null
}
if (-not $remoteAfter) {
    Write-Host "No origin remote set. I opened GitHub create-repo page for you."
    Start-Process "https://github.com/new"
    Write-Host "After creating repo, rerun: .\\scripts\\publish_to_render.ps1 -RepoUrl https://github.com/<USER>/<REPO>.git"
    exit 1
}

Write-Host "Pushing to GitHub..."
git push -u origin main | Out-Host

Write-Host "Opening Render Blueprint page..."
Start-Process "https://dashboard.render.com/select-repo?type=blueprint"

Write-Host "Done. In Render choose your repo and click Apply."
Write-Host "Set ADMIN_PASS in Render environment variables before first deploy."
