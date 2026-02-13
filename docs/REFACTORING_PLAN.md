# 🔧 Plan de Refactorización - game.js

**Fecha**: 2 de febrero de 2026  
**Archivo objetivo**: `frontend/game.js` (2971 líneas)  
**Objetivo**: Modularizar, reducir complejidad, mejorar mantenibilidad

---

## 📊 Análisis Actual

### Problemas Identificados
- ❌ **Monolítico**: 2971 líneas en un solo archivo
- ❌ **Funciones gigantes**: `playNextTrack()` tiene 90+ líneas
- ❌ **Duplicación**: 3 funciones diferentes para venue config
- ❌ **Estado global**: `gameState` mezclado con lógica
- ❌ **Sin separación de concerns**: UI + API + Audio + Business Logic
- ❌ **Difícil de testear**: Todo acoplado
- ❌ **Código muerto**: Funciones deprecated sin eliminar

### Métricas
```
Total líneas:          2971
Funciones:            ~80
Promedio por función: ~37 líneas
Funciones >50 líneas: 15
Imports/Dependencies: Mezclados con lógica
```

---

## 🎯 Objetivos de Refactorización

### Metas
1. ✅ **Reducir a <500 líneas** el archivo principal `game.js`
2. ✅ **Separar en 10 módulos** especializados
3. ✅ **Funciones <50 líneas** cada una
4. ✅ **100% testeable** con unit tests
5. ✅ **0 código duplicado** 
6. ✅ **Lazy loading** de módulos pesados

### Principios
- **Single Responsibility**: Cada módulo hace UNA cosa
- **DRY**: Don't Repeat Yourself
- **SOLID**: Especialmente Single Responsibility y Dependency Inversion
- **Progressive Enhancement**: Agregar módulos sin romper lo existente

---

## 📦 Fase 1: Separación en Módulos (Prioridad: ALTA)

### Estructura de Carpetas Propuesta
```
frontend/
├── game.html
├── game.js (orchestrator ~150 líneas)
├── config.js (existente)
└── js/
    └── modules/
        ├── state.js              # GameState management
        ├── audio.js              # Howler players (music, TTS, background)
        ├── api.js                # API calls al backend
        ├── storage.js            # localStorage operations
        ├── ui.js                 # DOM updates
        ├── announcements.js      # TTS + announcement generation
        ├── jingles.js            # Jingle playlist logic
        ├── session.js            # Session load/save
        ├── venue.js              # Venue config management
        └── keyboard.js           # Event listeners
```

### Módulo 1: `state.js` - Game State Management
```javascript
/**
 * Maneja todo el estado del juego
 * - Pool de canciones
 * - Canciones llamadas/restantes
 * - Track actual
 * - Flags (welcomeAnnounced, etc)
 */
export class GameState {
  constructor() {
    this.pool = [];
    this.remaining = [];
    this.called = [];
    this.currentTrack = null;
    this.isPlaying = false;
    this.venueName = '';
    this.sessionId = null;
    this.welcomeAnnounced = false;
    this.halfwayAnnounced = false;
  }

  reset() { }
  save() { }
  restore() { }
  getProgress() { }
  isComplete() { }
}
```

**Migrar desde game.js**:
- Líneas 31-50: gameState object
- Líneas 56-66: resetGameState()
- Líneas 1220-1242: saveGameState()
- Líneas 1247-1295: restoreGameState()

---

### Módulo 2: `audio.js` - Audio Management
```javascript
/**
 * Maneja todos los reproductores de audio
 * - Music player (Howler)
 * - TTS player (Howler)
 * - Background music
 */
export class AudioManager {
  constructor() {
    this.musicPlayer = null;
    this.ttsPlayer = null;
    this.backgroundMusic = null;
  }

  async playPreview(track) { }
  async playTTS(audioUrl) { }
  startBackground() { }
  stopBackground() { }
  fadeOut(player, duration) { }
  fadeIn(player, duration) { }
}
```

**Migrar desde game.js**:
- Líneas 219-223: Howler instances
- Líneas 1194-1208: startBackgroundMusic()
- Líneas 1710-1806: playSongPreview()
- Líneas 2165-2181: toggleBackgroundMusic()

---

### Módulo 3: `api.js` - Backend API Calls
```javascript
/**
 * Centraliza todas las llamadas al backend
 * - Session endpoints
 * - TTS generation
 * - Config loading
 * - Venue config
 */
export class APIClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  async fetchSession(sessionId) { }
  async fetchSessionLegacy() { }
  async generateTTS(text, voiceId) { }
  async loadAnnouncements() { }
  async loadAIAnnouncements() { }
  async saveVenueConfig(venueName, config) { }
  async loadVenueConfig(venueName) { }
  async updateSessionStatus(sessionId, status) { }
  async trackJinglePlay(scheduleId, round) { }
  
  // Helper genérico
  async request(endpoint, options = {}) { }
}
```

**Migrar desde game.js**:
- Líneas 104-117: saveVenueConfigToDatabase()
- Líneas 123-163: loadVenueConfig()
- Líneas 935-1118: loadSongPool()
- Líneas 1125-1157: loadAnnouncements()
- Líneas 1163-1175: loadAIAnnouncements()
- Líneas 1689-1708: generateElevenLabsTTS()
- Líneas 2949-2970: updateSessionStatus()

---

### Módulo 4: `storage.js` - LocalStorage Operations
```javascript
/**
 * Maneja todo lo relacionado con localStorage
 * - Venue config
 * - Game state
 * - Session data
 */
export class StorageManager {
  // Venue Config
  saveVenueConfig(venueName, config) { }
  loadVenueConfig(venueName) { }
  
  // Game State
  saveGameState(state) { }
  loadGameState() { }
  clearGameState() { }
  
  // Session
  saveSessionId(sessionId) { }
  getSessionId() { }
  
  // Generic helpers
  set(key, value) { }
  get(key, defaultValue = null) { }
  remove(key) { }
}
```

**Migrar desde game.js**:
- Líneas 73-103: saveVenueConfig()
- Líneas 123-163: loadVenueConfig() - parte localStorage
- Líneas 1220-1242: saveGameState()
- Líneas 1247-1295: restoreGameState()
- Líneas 1301-1305: clearGameState()

---

### Módulo 5: `ui.js` - UI Updates
```javascript
/**
 * Maneja todas las actualizaciones del DOM
 * - Current track display
 * - Called songs list
 * - Stats counters
 * - Status messages
 */
export class UIManager {
  updateCurrentTrack(track) { }
  updateCalledList(songs) { }
  updateStats(called, remaining) { }
  updateStatus(message, isPlaying) { }
  updateAnnouncementsList(announcements) { }
  setButtonState(buttonId, enabled) { }
  showNotification(message, type) { }
  showLogoPreview(url) { }
  updateSocialPreview(platform, username) { }
}
```

**Migrar desde game.js**:
- Líneas 165-208: showGameNotification()
- Líneas 1898-1914: updateStatus()
- Líneas 1916-1956: updateCurrentTrackDisplay()
- Líneas 1962-1997: updateCalledList()
- Líneas 2003-2026: updateStats()
- Líneas 2032-2075: updateAnnouncementsList()
- Líneas 2112-2116: setButtonState()

---

### Módulo 6: `announcements.js` - TTS & Announcements
```javascript
/**
 * Genera y reproduce anuncios TTS
 * - Welcome announcements
 * - Halfway announcements
 * - Track announcements
 * - Custom announcements
 */
export class AnnouncementManager {
  constructor(apiClient, audioManager) {
    this.api = apiClient;
    this.audio = audioManager;
    this.announcementsData = null;
    this.announcementsAI = null;
  }

  async load() { }
  async loadAI() { }
  
  generateWelcomeText(venueName) { }
  generateHalfwayText() { }
  generateTrackText(track) { }
  
  async announceWelcome(venueName) { }
  async announceHalfway() { }
  async announceTrack(track) { }
  async announceCustom(text) { }
}
```

**Migrar desde game.js**:
- Líneas 1125-1157: loadAnnouncements()
- Líneas 1163-1175: loadAIAnnouncements()
- Líneas 1417-1431: generateWelcomeText()
- Líneas 1437-1451: generateHalfwayText()
- Líneas 1536-1628: generateAnnouncementText()
- Líneas 1434-1475: announceWelcome()
- Líneas 1481-1527: announceHalfway()
- Líneas 1634-1678: announceTrack()
- Líneas 2081-2105: playSpecificAnnouncement()

---

### Módulo 7: `jingles.js` - Jingle Playlist
```javascript
/**
 * Maneja la reproducción de jingles
 * - Load playlist settings
 * - Check scheduling
 * - Play jingles
 * - Track analytics
 */
export class JingleManager {
  constructor(apiClient, audioManager) {
    this.api = apiClient;
    this.audio = audioManager;
    this.playlist = [];
    this.enabled = false;
    this.interval = 3;
  }

  async load() { }
  async fetchActive() { }
  async checkAndPlay(songsPlayed) { }
  playAudio(filename) { }
  async trackPlay(scheduleId, round) { }
}
```

**Migrar desde game.js**:
- Líneas 2789-2801: jinglePlaylist object
- Líneas 2803-2817: loadJinglePlaylist()
- Líneas 2823-2850: fetchActiveJingles()
- Líneas 2855-2870: trackJinglePlay()
- Líneas 2876-2910: checkAndPlayJingle()
- Líneas 2916-2938: playJingleAudio()

---

### Módulo 8: `session.js` - Session Management
```javascript
/**
 * Maneja sesiones de juego
 * - Load session from URL
 * - Start game from session
 * - Save session config
 */
export class SessionManager {
  constructor(apiClient, storageManager) {
    this.api = apiClient;
    this.storage = storageManager;
  }

  async loadFromURL(sessionId) { }
  async startFromConfig(config) { }
  saveConfig(config) { }
  async updateStatus(status) { }
}
```

**Migrar desde game.js**:
- Líneas 256-340: loadSessionAndStart()
- Líneas 345-378: startGameFromConfig()
- Líneas 2949-2970: updateSessionStatus()

---

### Módulo 9: `venue.js` - Venue Configuration
```javascript
/**
 * Maneja configuración específica de venue
 * - Save venue config
 * - Load venue config
 * - Logo upload
 * - Social media URLs
 */
export class VenueManager {
  constructor(apiClient, storageManager) {
    this.api = apiClient;
    this.storage = storageManager;
  }

  async save(venueName, config) { }
  async load(venueName) { }
  async uploadLogo(file) { }
  getSocialMediaURL(platform, username) { }
  calculateOptimalSongs(numPlayers) { }
}
```

**Migrar desde game.js**:
- Líneas 73-117: saveVenueConfig() + saveVenueConfigToDatabase()
- Líneas 123-163: loadVenueConfig()
- Líneas 2622-2680: handleLogoUpload()
- Líneas 2762-2784: getSocialMediaURL()
- Líneas 2216-2229: calculateOptimalSongs()

---

### Módulo 10: `keyboard.js` - Event Listeners
```javascript
/**
 * Maneja atajos de teclado
 * - Space/Enter: Next track
 * - A: Announcement
 * - R: Reset
 * - M: Toggle music
 */
export class KeyboardManager {
  constructor(gameInstance) {
    this.game = gameInstance;
  }

  init() {
    document.addEventListener('keydown', this.handleKeydown.bind(this));
  }

  handleKeydown(e) { }
}
```

**Migrar desde game.js**:
- Líneas 2122-2156: keyboard event listener

---

## 🔄 Fase 2: Eliminar Duplicación (Prioridad: ALTA)

### Duplicaciones Identificadas

#### 1. Venue Config (3 funciones → 1 módulo)
```javascript
// ANTES
saveVenueConfig()              // localStorage
saveVenueConfigToDatabase()    // API
loadVenueConfig()              // localStorage + API

// DESPUÉS (venue.js)
class VenueManager {
  async save(venueName, config) {
    await this.storage.save(venueName, config);
    await this.api.save(venueName, config);
  }
  
  async load(venueName) {
    const dbConfig = await this.api.load(venueName);
    return dbConfig || this.storage.load(venueName);
  }
}
```

#### 2. Fetch Patterns (Repetido 15 veces → 1 helper)
```javascript
// ANTES (repetido en 15 lugares)
const response = await fetch(`${API_URL}/...`);
if (!response.ok) throw new Error('...');
const data = await response.json();

// DESPUÉS (api.js)
async request(endpoint, options = {}) {
  const response = await fetch(`${this.baseURL}${endpoint}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || `API Error: ${response.status}`);
  }
  
  return response.json();
}
```

#### 3. TTS Functions (4 funciones → 1 clase)
```javascript
// ANTES
announceWelcome()    // 40 líneas
announceHalfway()    // 40 líneas
announceTrack()      // 45 líneas
announceCustom()     // 25 líneas
// Total: 150 líneas con duplicación

// DESPUÉS (announcements.js)
class AnnouncementManager {
  async announce(text, type = 'default') {
    const audioUrl = await this.api.generateTTS(text, this.voiceId);
    await this.audio.playTTS(audioUrl);
  }
}
// Total: ~50 líneas sin duplicación
```

---

## 🏗️ Fase 3: Mejorar Arquitectura (Prioridad: MEDIA)

### Arquitectura Actual (Procedural)
```javascript
// game.js - TODO mezclado con cómo
async function playNextTrack() {
  const track = gameState.remaining.shift();  // Mutar estado
  gameState.called.push(track);               // Mutar estado
  updateCurrentTrackDisplay(track);           // Update UI
  await announceTrack(track);                 // TTS
  await playSongPreview(track);               // Audio
  updateCalledList();                         // Update UI
  updateStats();                              // Update UI
  saveGameState();                            // Persistence
}
```

### Arquitectura Propuesta (OOP + Separation of Concerns)
```javascript
// game.js - Orquestador limpio
class MusicBingoGame {
  constructor() {
    this.state = new GameState();
    this.audio = new AudioManager();
    this.announcer = new AnnouncementManager(api, audio);
    this.jingles = new JingleManager(api, audio);
    this.ui = new UIManager();
  }

  async playNext() {
    // 1. Update state (isolated)
    const track = this.state.getNextTrack();
    
    // 2. Welcome (first time only)
    if (this.state.isFirstSong()) {
      await this.announcer.announceWelcome(this.state.venueName);
    }
    
    // 3. Jingles (scheduled)
    await this.jingles.checkAndPlay(this.state.called.length);
    
    // 4. Announce track
    await this.announcer.announceTrack(track);
    
    // 5. Play preview
    await this.audio.playPreview(track);
    
    // 6. Update UI
    this.ui.updateAll(this.state);
    
    // 7. Persist
    this.state.save();
  }
}
```

### Beneficios
- ✅ **Testeable**: Cada paso se puede mockear
- ✅ **Legible**: Flujo claro y secuencial
- ✅ **Mantenible**: Cambiar un paso no afecta otros
- ✅ **Extensible**: Agregar pasos es trivial

---

## 🧹 Fase 4: Cleanup (Prioridad: MEDIA)

### Código Muerto a Eliminar

#### 1. Función Deprecated
```javascript
// Línea 915 - Eliminar completamente
/**
 * Load venue configuration from backend (deprecated - now using localStorage)
 */
async function loadVenueConfig() { ... }
```

#### 2. Funciones Sin Uso
- `unlockAudio()` (línea 2196) - iOS Safari workaround ya no necesario
- `formatDuration()` (línea 2188) - No usado en ningún lugar

#### 3. Consolidar Inicialización
```javascript
// ANTES (3 funciones)
initializeGame()          // Línea 795
initializeSetupModal()    // Línea 383
completeSetup()           // Línea 669

// DESPUÉS (1 clase)
class GameInitializer {
  async init() {
    await this.loadConfig();
    await this.loadResources();
    this.setupUI();
  }
}
```

### Tipos Inconsistentes

#### Normalizar nombres de variables
```javascript
// ANTES (mezclados)
sessionId       // línea 240
session_id      // línea 948
currentSessionId // línea 261

// DESPUÉS (consistente)
sessionId       // Usar siempre camelCase
```

### Error Handling Repetitivo

#### Consolidar try-catch
```javascript
// ANTES (repetido 20+ veces)
try {
  const response = await fetch(...);
  if (!response.ok) throw new Error(...);
  return response.json();
} catch (error) {
  console.error('Error:', error);
  alert(`Failed: ${error.message}`);
}

// DESPUÉS (centralizado en api.js)
class APIClient {
  async request(endpoint, options) {
    try {
      // ... fetch logic
    } catch (error) {
      this.handleError(error, options.errorMessage);
      throw error;
    }
  }
  
  handleError(error, customMessage) {
    console.error('API Error:', error);
    if (customMessage) alert(customMessage);
  }
}
```

---

## 🧪 Fase 5: Testing (Prioridad: BAJA)

### Test Suite Propuesta

```
tests/
├── unit/
│   ├── state.test.js           # GameState unit tests
│   ├── audio.test.js           # AudioManager unit tests
│   ├── api.test.js             # APIClient unit tests
│   ├── storage.test.js         # StorageManager unit tests
│   ├── announcements.test.js   # AnnouncementManager tests
│   ├── jingles.test.js         # JingleManager tests
│   └── venue.test.js           # VenueManager tests
├── integration/
│   ├── session-flow.test.js    # Session load → play → complete
│   ├── audio-flow.test.js      # TTS → Music → Background
│   └── ui-updates.test.js      # State changes → UI updates
└── e2e/
    └── game.spec.js            # Playwright/Cypress full flow
```

### Ejemplo: state.test.js
```javascript
import { GameState } from '../modules/state.js';

describe('GameState', () => {
  let state;

  beforeEach(() => {
    state = new GameState();
  });

  test('should initialize with empty arrays', () => {
    expect(state.pool).toEqual([]);
    expect(state.remaining).toEqual([]);
    expect(state.called).toEqual([]);
  });

  test('should get next track correctly', () => {
    state.remaining = [{ id: '1' }, { id: '2' }];
    const track = state.getNextTrack();
    
    expect(track.id).toBe('1');
    expect(state.remaining.length).toBe(1);
    expect(state.called.length).toBe(1);
  });

  test('should detect game completion', () => {
    state.remaining = [];
    expect(state.isComplete()).toBe(true);
    
    state.remaining = [{ id: '1' }];
    expect(state.isComplete()).toBe(false);
  });
});
```

---

## 📅 Timeline de Implementación

### Semana 1: Fase 1 - Módulos Base
- **Día 1-2**: Crear módulos `state.js`, `audio.js`, `api.js`
- **Día 3-4**: Crear módulos `storage.js`, `ui.js`, `announcements.js`
- **Día 5**: Crear módulos `jingles.js`, `session.js`, `venue.js`, `keyboard.js`

### Semana 2: Fase 2 - Migración
- **Día 1-2**: Migrar funciones a módulos sin romper game.js
- **Día 3-4**: Integrar módulos en game.js (imports + uso)
- **Día 5**: Testing manual de cada módulo

### Semana 3: Fase 3 - Refactor Arquitectura
- **Día 1-2**: Crear clase `MusicBingoGame` como orquestador
- **Día 3-4**: Migrar lógica a clase, eliminar funciones globales
- **Día 5**: Testing de integración

### Semana 4: Fase 4 & 5 - Cleanup + Tests
- **Día 1-2**: Eliminar código muerto, consolidar duplicados
- **Día 3-4**: Escribir unit tests básicos
- **Día 5**: Testing e2e + deployment

---

## 📊 Métricas de Éxito

### Antes de Refactorización
```
game.js:              2971 líneas
Funciones:            ~80
Complejidad:          Alta (funciones >90 líneas)
Cobertura de tests:   0%
Tiempo de carga:      ~200ms (todo en un archivo)
```

### Después de Refactorización
```
game.js:              ~150 líneas (orquestador)
Total módulos:        10 archivos (~250 líneas c/u)
Funciones:            ~100 (más pequeñas, especializadas)
Complejidad:          Baja (funciones <50 líneas)
Cobertura de tests:   >80%
Tiempo de carga:      ~150ms (lazy loading)
```

### KPIs
- ✅ **-80% líneas en game.js** (2971 → 150)
- ✅ **+25% funciones** pero más pequeñas (80 → 100)
- ✅ **-50% complejidad** ciclomática por función
- ✅ **+80% cobertura** de tests (0% → 80%)
- ✅ **-25% tiempo de carga** con lazy loading

---

## 🚀 Plan de Migración (Sin Downtime)

### Estrategia: Strangler Fig Pattern

#### 1. Coexistencia (Semanas 1-2)
```javascript
// game.js (ambos sistemas coexisten)
import { GameState } from './modules/state.js';

// OLD: gameState global object
let gameState = { ... };

// NEW: GameState class instance
const gameStateNew = new GameState();

// Usar OLD por defecto, NEW en funciones específicas
function playNextTrack() {
  // Usa gameState (OLD)
}

function playNextTrackNew() {
  // Usa gameStateNew (NEW)
}
```

#### 2. Migración Gradual (Semanas 2-3)
```javascript
// Reemplazar función por función
function playNextTrack() {
  // MIGRATED: Ahora usa módulos
  const track = gameStateNew.getNextTrack();
  await announcerNew.announce(track);
  await audioNew.playPreview(track);
  uiNew.updateAll(gameStateNew);
}
```

#### 3. Eliminación de OLD (Semana 4)
```javascript
// Eliminar código viejo después de validar NEW
// git rm old-functions.js
// Solo queda NEW system
```

### Feature Flags (Opcional)
```javascript
const USE_NEW_MODULES = true; // Toggle para A/B testing

if (USE_NEW_MODULES) {
  await playNextTrackNew();
} else {
  await playNextTrack(); // Legacy
}
```

---

## 🎯 Quick Wins (Implementar Primero)

### Win 1: Extraer `api.js` (2 horas)
**Impacto**: Centraliza 15 fetch calls, elimina duplicación  
**Líneas reducidas**: ~150 líneas  
**Archivos afectados**: 1 (game.js)

### Win 2: Extraer `storage.js` (1 hora)
**Impacto**: Consolida localStorage operations  
**Líneas reducidas**: ~100 líneas  
**Archivos afectados**: 1 (game.js)

### Win 3: Extraer `ui.js` (3 horas)
**Impacto**: Separa lógica de presentación  
**Líneas reducidas**: ~200 líneas  
**Archivos afectados**: 1 (game.js)

### Total Quick Wins: 6 horas → -450 líneas

---

## ⚠️ Riesgos y Mitigación

### Riesgo 1: Breaking Changes
**Probabilidad**: Media  
**Impacto**: Alto  
**Mitigación**: 
- Mantener OLD y NEW en paralelo durante migración
- Testing exhaustivo después de cada módulo
- Feature flags para rollback rápido

### Riesgo 2: Performance Degradation
**Probabilidad**: Baja  
**Impacto**: Medio  
**Mitigación**:
- Lazy loading de módulos no críticos
- Benchmarking antes/después
- Profiling en Chrome DevTools

### Riesgo 3: Aumento de Complejidad (Over-engineering)
**Probabilidad**: Media  
**Impacto**: Medio  
**Mitigación**:
- Seguir KISS (Keep It Simple, Stupid)
- Solo abstraer cuando hay 3+ casos de uso
- Revisión de código por pares

---

## 📚 Referencias

### Patterns Usados
- **Strangler Fig**: Migración gradual sin downtime
- **Module Pattern**: Encapsulación y organización
- **Dependency Injection**: Testeable y desacoplado
- **Single Responsibility**: Cada módulo hace UNA cosa
- **Facade Pattern**: `MusicBingoGame` como interfaz simple

### Recursos
- [Refactoring.Guru - Patterns](https://refactoring.guru/design-patterns)
- [Clean Code - Robert Martin](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)
- [JavaScript Modules - MDN](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules)

---

## ✅ Checklist de Completitud

### Fase 1: Módulos
- [ ] `state.js` creado y funcional
- [ ] `audio.js` creado y funcional
- [ ] `api.js` creado y funcional
- [ ] `storage.js` creado y funcional
- [ ] `ui.js` creado y funcional
- [ ] `announcements.js` creado y funcional
- [ ] `jingles.js` creado y funcional
- [ ] `session.js` creado y funcional
- [ ] `venue.js` creado y funcional
- [ ] `keyboard.js` creado y funcional

### Fase 2: Migración
- [ ] Todas las funciones migradas a módulos
- [ ] Imports agregados a game.js
- [ ] Código viejo eliminado
- [ ] Sin funciones duplicadas

### Fase 3: Arquitectura
- [ ] Clase `MusicBingoGame` creada
- [ ] Lógica movida a clase
- [ ] Funciones <50 líneas cada una
- [ ] game.js <500 líneas

### Fase 4: Cleanup
- [ ] Código muerto eliminado
- [ ] Tipos consistentes (sessionId)
- [ ] Error handling centralizado
- [ ] Comentarios actualizados

### Fase 5: Testing
- [ ] Unit tests escritos (>50% coverage)
- [ ] Integration tests escritos
- [ ] E2E tests escritos
- [ ] CI/CD pipeline configurado

---

**Última actualización**: 2 de febrero de 2026  
**Estado**: 📝 Plan aprobado, pendiente implementación  
**Responsable**: Equipo de desarrollo
