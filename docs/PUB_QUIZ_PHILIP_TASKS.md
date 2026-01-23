# Pub Quiz - Philip's Feedback Tasks

**Date**: January 23, 2026  
**Priority**: High  
**Context**: Feedback from Philip Hill testing session

---

## ✅ Task 1: Anunciar la ronda (COMPLETED)

**Priority**: PRIORITARIO  
**Status**: ✅ COMPLETED (Jan 23, 2026)

### Requirement
El audio debe mencionar el tema/género antes de cada ronda.

### Example
- "Round 1: General Knowledge"
- "Round 2: Pop Music"
- "Round 3: 80s Nostalgia"

### Implementation
- Backend sends genre name with question data
- Frontend detects round changes
- TTS plays round announcement before first question
- UI displays genre in question badge

### Commit
`feat: Announce round genre before first question of each round` (d6ba028)

---

## 🔄 Task 2: Avance automático de preguntas

**Priority**: PRIORITARIO  
**Status**: ⏳ PENDING

### Requirement
Las preguntas deben avanzar automáticamente con un intervalo de tiempo entre cada una.

### Specifications
- **Timer**: ~15 segundos entre cada pregunta
- **Configurable**: El host debería poder ajustar el tiempo si es necesario
- **Visual feedback**: Mostrar cuenta regresiva en pantalla
- **Pausable**: El host puede pausar el avance automático si necesita más tiempo

### Implementation Notes
- Add timer setting in quiz configuration
- Display countdown timer on host panel
- Auto-trigger `nextQuestion()` when timer expires
- Add pause/resume controls for host
- Show timer on player screens (optional)

### Acceptance Criteria
- [ ] Questions advance automatically after 15 seconds
- [ ] Host can see countdown timer
- [ ] Host can pause/resume auto-advance
- [ ] Timer is configurable per session
- [ ] Visual indicator shows time remaining

---

## 📄 Task 3: Tarjetas de respuesta imprimibles

**Priority**: MEDIUM  
**Status**: ⏳ PENDING

### Requirement
Generar PDF con tarjetas para que los equipos respondan en papel (formato físico para personas mayores que prefieren no usar teléfonos).

### Specifications
- **Format**: Similar a las tarjetas de Music Bingo
- **Content**: 
  - Team name/number
  - Round numbers (1-6)
  - Question numbers per round (1-10)
  - Space for written answers
  - Multiple choice bubbles (A/B/C/D) for MC questions
- **Generation**: Host can print before quiz starts
- **Layout**: Optimized for standard A4/Letter paper

### Implementation Notes
- Create PDF generation endpoint
- Use library like ReportLab or WeasyPrint
- Include session details (venue, date)
- Generate one card per team or blank templates
- Add "Print Answer Cards" button in host panel

### Acceptance Criteria
- [ ] Host can generate PDF answer cards
- [ ] Cards include all rounds and questions
- [ ] Format is printer-friendly
- [ ] Cards have space for team name
- [ ] Layout matches Music Bingo style

---

## 📊 Task 4: Niveles de dificultad

**Priority**: MEDIUM  
**Status**: ⏳ PENDING

### Requirement
Agregar sistema de niveles de dificultad a las preguntas.

### Specifications
- **Levels**: Easy, Medium, Hard
- **Points**: Different point values based on difficulty
  - Easy: 5 points
  - Medium: 10 points (default)
  - Hard: 15 points
- **Display**: Show difficulty badge on question display
- **Generation**: AI should generate questions with varying difficulty
- **Balance**: Each round should have a mix of difficulties

### Implementation Notes
- Add difficulty field to QuizQuestion model (already exists)
- Update question generation prompt to specify difficulty distribution
- Display difficulty indicator on host and player screens
- Adjust point awards based on difficulty
- Allow host to see difficulty breakdown per round

### Acceptance Criteria
- [ ] Questions have difficulty levels (easy/medium/hard)
- [ ] Points are adjusted based on difficulty
- [ ] Host can see difficulty of each question
- [ ] AI generates balanced mix of difficulties
- [ ] Difficulty shown on player screens

---

## Notes

### Philip's Context (from conversation)
> "with the pub quiz all the questions are asked over the audio system of the pub, just like a person reading the questions"

### Hybrid Approach
- **Digital**: QR code registration and scoring (younger users)
- **Physical**: Printed answer cards (older users, traditional pub quiz feel)
- **Audio**: Questions read over pub PA system by AI voice

### Resources
- ElevenLabs Voice IDs document (shared by Philip)
- Perfect DJ website for photos/branding
- Dropbox folder: https://www.dropbox.com/scl/fo/kw18yrtfivqxrzqjz38gx/...

---

## Implementation Order

1. ✅ **Round announcements** (DONE)
2. 🔄 **Auto-advance questions** (NEXT - high impact)
3. 📊 **Difficulty levels** (Quick win - model field exists)
4. 📄 **Printable cards** (Larger task - good for traditional pubs)
