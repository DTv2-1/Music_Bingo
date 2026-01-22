const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 8080;
const BACKEND_URL = process.env.BACKEND_URL || '';

console.log('🚀 Server starting...');
console.log('   PORT:', PORT);
console.log('   BACKEND_URL from env:', process.env.BACKEND_URL);
console.log('   BACKEND_URL final:', BACKEND_URL);

// Inject BACKEND_URL into HTML
function injectBackendUrl(html) {
  return html.replace(
    '<head>',
    `<head>\n    <script>window.BACKEND_URL = '${BACKEND_URL}';</script>`
  );
}

// Helper function to serve HTML files
function serveHtmlFile(res, filename) {
  const filePath = path.join(__dirname, filename);
  console.log(`📂 Loading file: ${filePath}`);
  
  fs.readFile(filePath, 'utf8', (err, html) => {
    if (err) {
      console.error(`❌ Error loading ${filename}:`, err);
      return res.status(404).send('Page not found');
    }
    
    console.log(`✓ ${filename} loaded (${html.length} bytes)`);
    console.log(`🔗 Injecting BACKEND_URL: ${BACKEND_URL || '(empty)'}`);
    
    const injectedHtml = injectBackendUrl(html);
    res.setHeader('Content-Type', 'text/html');
    res.send(injectedHtml);
    
    console.log(`✓ ${filename} sent to client`);
  });
}

// Clean URL routes (without .html)
app.get('/', (req, res) => {
  console.log('📄 Request for / - serving game.html');
  serveHtmlFile(res, 'game.html');
});

app.get('/game', (req, res) => {
  console.log('📄 Request for /game - serving game.html');
  serveHtmlFile(res, 'game.html');
});

app.get('/jingle', (req, res) => {
  console.log('📄 Request for /jingle - serving jingle.html');
  serveHtmlFile(res, 'jingle.html');
});

app.get('/jingle-manager', (req, res) => {
  console.log('📄 Request for /jingle-manager - serving jingle-manager.html');
  serveHtmlFile(res, 'jingle-manager.html');
});

app.get('/index', (req, res) => {
  console.log('📄 Request for /index - serving index.html');
  serveHtmlFile(res, 'index.html');
});

app.get('/pub-quiz/register/:id', (req, res) => {
  console.log(`📄 Request for /pub-quiz/register/${req.params.id} - serving pub-quiz-register.html`);
  serveHtmlFile(res, 'pub-quiz-register.html');
});

// Support legacy .html?session=X format
app.get('/pub-quiz-register.html', (req, res) => {
  console.log(`📄 Request for /pub-quiz-register.html - serving with injection`);
  serveHtmlFile(res, 'pub-quiz-register.html');
});

app.get('/pub-quiz-host.html', (req, res) => {
  console.log(`📄 Request for /pub-quiz-host.html - serving with injection`);
  serveHtmlFile(res, 'pub-quiz-host.html');
});

app.get('/pub-quiz/host/:id', (req, res) => {
  console.log(`📄 Request for /pub-quiz/host/${req.params.id} - serving pub-quiz-host.html`);
  serveHtmlFile(res, 'pub-quiz-host.html');
});

// Legacy .html routes (redirect to clean URLs)
app.get('/game.html', (req, res) => {
  console.log('📄 Redirecting /game.html -> /game');
  res.redirect(301, '/game');
});

app.get('/jingle.html', (req, res) => {
  console.log('📄 Redirecting /jingle.html -> /jingle');
  res.redirect(301, '/jingle');
});

app.get('/jingle-manager.html', (req, res) => {
  console.log('📄 Redirecting /jingle-manager.html -> /jingle-manager');
  res.redirect(301, '/jingle-manager');
});

app.get('/index.html', (req, res) => {
  console.log('📄 Redirecting /index.html -> /index');
  res.redirect(301, '/index');
});

// Serve static files AFTER HTML routes (CSS, JS, images, etc)
app.use(express.static(__dirname, {
  setHeaders: (res, filepath) => {
    console.log(`📦 Serving static file: ${filepath}`);
    if (filepath.endsWith('.html')) {
      // This shouldn't be reached due to routes above
      res.setHeader('Cache-Control', 'no-cache');
    }
  }
}));

app.listen(PORT, '0.0.0.0', () => {
  console.log(`✓ Frontend server running on port ${PORT}`);
  console.log(`✓ Backend URL: ${BACKEND_URL || 'Not configured'}`);
  console.log(`✓ Clean URLs enabled:`);
  console.log(`  - / or /game -> game.html`);
  console.log(`  - /jingle -> jingle.html`);
  console.log(`  - /jingle-manager -> jingle-manager.html`);
  console.log(`  - /index -> index.html`);
  console.log(`✓ Legacy .html URLs redirect to clean URLs`);
});
