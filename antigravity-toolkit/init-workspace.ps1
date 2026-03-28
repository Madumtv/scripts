param(
    [Parameter(Mandatory=$false)]
    [string]$ProjectName,
    [string]$GitHubUrl
)

# 1. Nom
if (-not $ProjectName) {
    $ProjectName = Read-Host "Project Name?"
}
if (-not $ProjectName) { return }

$NewDir = Join-Path (Get-Location) $ProjectName

# 2. Dossier
if (-not (Test-Path $NewDir)) {
    New-Item -ItemType Directory -Path $NewDir -Force | Out-Null
}

# 3. Git
Push-Location $NewDir
if (-not (Test-Path ".git")) {
    git init | Out-Null
}

# 4. GitHub
if (-not $GitHubUrl) {
    $GitHubUrl = Read-Host "GitHub URL?"
}
if ($GitHubUrl) {
    if (git remote) { git remote remove origin }
    git remote add origin $GitHubUrl
}

# 5. Structure
$AgentSkillsDir = ".agents\skills"
if (-not (Test-Path $AgentSkillsDir)) {
    New-Item -ItemType Directory -Path $AgentSkillsDir -Force | Out-Null
}

# 6. Copie
$ParentSkillsDir = "..\.agents\skills"
if (Test-Path $ParentSkillsDir) {
    $folders = Get-ChildItem -Path $ParentSkillsDir -Directory
    foreach ($f in $folders) {
        $Dest = Join-Path $AgentSkillsDir $f.Name
        Copy-Item -Path $f.FullName -Destination $Dest -Recurse -Force
        Write-Host "Skill imported: $($f.Name)"
    }
}

# 7. README
if (-not (Test-Path "README.md")) {
    $header = "# " + $ProjectName
    $header | Out-File -FilePath "README.md"
}

Pop-Location
Write-Host "Done! Project $ProjectName is ready."
