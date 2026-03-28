param(
    [Parameter(Mandatory=$true)]
    [string]$Name,
    [string]$Description = "Une nouvelle compétence personnalisée pour Antigravity."
)

$SkillDir = ".agents/skills/$Name"
if (-not (Test-Path $SkillDir)) {
    New-Item -ItemType Directory -Path $SkillDir -Force | Out-Null
    $SkillFile = "$SkillDir/SKILL.md"
    
    $Content = @"
---
name: $Name
description: $Description
---

# $Name

## Quand utiliser cette skill
Décrivez ici les scénarios où cette compétence doit être activée.

## Instructions
Listez ici les consignes précises à suivre...
"@

    Set-Content -Path $SkillFile -Value $Content
    Write-Host "✅ Skill '$Name' créée avec succès dans $SkillDir" -ForegroundColor Green
} else {
    Write-Error "❌ Une skill avec ce nom existe déjà."
}
