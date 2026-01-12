const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 8080;
const BACKEND_URL = process.env.BACKEND_URL || '';

// Serve static files (CSS, JS, images)
app.use(express.static(__dirname, {
  setHeaders: (res, filepath) => {
    // Don't cache HTML files
    if (filepath.endsWith('.html')) {
      res.setHeader('Cache-Control', 'no-cache');
    }
  }
}));

// Inject BACKEND_URL into HTML files
app.get('*.html', (req, res) => {
  const filePath = path.join(__dirname, req.path);
  fs.readFile(filePath, 'utf8', (err, html) => {
    if (err) {
      return res.status(404).send('Not found');
    }
    
    // Inject BACKEND_URL as a window variable before other scripts
    const injectedHtml = html.replace(
      '<head>',
      `<head>\n    <script>window.BACKEND_URL = '${BACKEND_URL}';</script>`
    );
    
    res.setHeader('Content-Type', 'text/html');
    res.send(injectedHtml);
  });
});

// Special handling for root
app.get('/', (req, res) => {
  const filePath = path.join(__dirname, 'game.html');
  fs.readFile(filePath, 'utf8', (err, html) => {
    if (err) {
      return res.status(500).send('Error loading game');
    }
    
    // Inject BACKEND_URL
    const injectedHtml = html.replace(
      '<head>',
      `<head>\n    <script>window.BACKEND_URL = '${BACKEND_URL}';</script>`
    );
    
    res.setHeader('Content-Type', 'text/html');
    res.send(injectedHtml);
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`✓ Frontend server running on port ${PORT}`);
  console.log(`✓ Backend URL: ${BACKEND_URL || 'Not configured'}`);
});
