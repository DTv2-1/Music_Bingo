const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8080;
const BACKEND_URL = process.env.BACKEND_URL || '';

// Serve static files
app.use(express.static(__dirname));

// Inject BACKEND_URL into HTML files
app.get('*.html', (req, res) => {
  const filePath = path.join(__dirname, req.path);
  res.sendFile(filePath, { 
    headers: { 'Content-Type': 'text/html' }
  }, (err) => {
    if (!err) {
      // Inject script tag with BACKEND_URL
      console.log(`Serving ${req.path} with BACKEND_URL: ${BACKEND_URL}`);
    }
  });
});

// Special handling for root
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'game.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`✓ Frontend server running on port ${PORT}`);
  console.log(`✓ Backend URL: ${BACKEND_URL || 'Not configured'}`);
});
