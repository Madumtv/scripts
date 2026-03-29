# 🏺 Project: The Archivist // Digital Curator

Ce document définit l'identité visuelle et le système de conception du futur panel d'administration VPS **The Archivist**. 

---

## 🛰️ Identity & Concept
- **Identity**: "The Archivist" // Conservateur Numérique.
- **Concept** : Une interface brute, documentaire et technique, conçue pour l'archivage et la gestion précise des données système.

---

## 🎨 Design System (Aesthetic)
- **Aesthetic**: Brutalist Technical Editorial.
- **Colors**:
  - **Bg**: `#f2f0e4` (Beige Papier/Archive)
  - **Ink**: `#000000` (Noir pur)
  - **Accent**: `#d90000` (Rouge Alerte/Technique)
- **Typography**:
  - **Headlines**: Serif "Newsreader" (Élégance éditoriale).
  - **Labels/Metadata**: Sans "Space Grotesk" (ALL-CAPS, aspect technique/monospacé).

---

## 📏 Design Rules & UI Kit
1. **0px Roundness**: Les coins arrondis sont bannis. Chaque bloc, bouton ou conteneur doit avoir des angles vifs et tranchants (Sharp Corners).
2. **Brutalist Borders**: Interdiction d'utiliser des bordures de 1px. Utilisez des **changements de tons de fond** (tonal background shifts) pour séparer les sections.
3. **Hard Offsets**: Pour l'élévation et le relief, utilisez des **ombres noires opaques** (Opaque black shadows, 100% opacity, no blur). Les blocs "flottent" via un décalage physique.
4. **Layout**: Mise en page asymétrique avec des gouttières larges (**spacing-24**).

---

## 🤖 Prompt Templates (For AI Generation)

### 🇫🇷 Version Française
> "Tu es une IA spécialisée dans le design 'The Archivist'. Génère une interface type 'Conservateur Numérique'. Utilise un fond beige (#f2f0e4), des titres en Newsreader, et des labels en monospacé/Space Grotesk. Bannis les arrondis et les bordures fines. Utilise des décalages de blocs pour la structure."

### 🇬🇧 English Version
> "You are an AI specialist in 'The Archivist' design system. Generate a 'Digital Curator' UI. Use a beige background (#f2f0e4), Newsreader for headlines, and Space Grotesk for uppercase labels. Prohibit rounded corners and thin borders. Use offset blocks for structure and hierarchy."

---

## 🛠️ Roadmap Implementation
- [ ] Création du fichier `index.css` avec les variables de tokens (Newsreader, Space Grotesk).
- [ ] Maquette de la page de login "The Archivist".
- [ ] Développement du Dashboard avec monitoring live intégré dans des blocs asymétriques.
