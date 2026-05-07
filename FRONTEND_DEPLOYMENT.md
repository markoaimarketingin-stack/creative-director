# Frontend Deployment Guide

## Local Development

1. **Serve the frontend locally:**
   ```bash
   cd frontend
   python -m http.server 3000
   ```

2. **Update `env-config.js` for local development:**
   - Default: `http://127.0.0.1:8000`
   - Make sure your backend is running on this port

3. **Access the app:**
   - Open `http://localhost:3000` in your browser

## Vercel Deployment

### Option 1: Deploy Static Frontend Only
```bash
vercel --prod
```
- Select `frontend` as the output directory when prompted
- Set `BACKEND_URL` environment variable to your API endpoint

### Option 2: Deploy with Environment Variables
```bash
vercel --prod --env BACKEND_URL=https://your-api.example.com
```

### Configuration
- `vercel.json` is configured to serve `index.html` for all routes
- CSS and JS files are served from root paths (`/styles.css`, `/app.js`, `/env-config.js`) so both Vercel and the FastAPI root page can load them
- `env-config.js` auto-detects backend URL based on environment

## Important Notes

1. **CSS & JS Paths**: The HTML uses root asset paths. FastAPI exposes matching routes, and Vercel serves the static files from the frontend output directory.
2. **API Configuration**: Auto-detects backend URL from:
   - Environment variable `BACKEND_URL`
   - Production domain (uses same origin)
   - Defaults to `http://127.0.0.1:8000` for local dev

3. **Cross-Origin**: If frontend and backend are on different domains, ensure CORS is configured on the backend

## Troubleshooting

### Styles not loading?
- Check browser DevTools Network tab for CSS file 404 errors
- Ensure `styles.css` is in the `frontend/` directory
- Clear browser cache and hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

### API calls failing?
- Check `env-config.js` is loaded first in the HTML head
- Open browser console and check `window.__APP_CONFIG__.BACKEND_URL`
- Ensure backend CORS allows requests from your frontend domain
- Check Network tab for failed API calls and error messages

### Blank page?
- Check browser console for JavaScript errors
- Ensure all script files loaded successfully
- Verify `./app.js` and `./env-config.js` are accessible
