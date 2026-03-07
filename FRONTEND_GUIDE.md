# Frontend Guide (React)

## Code Location
- App: `frontend/src/App.jsx`
- Styles: `frontend/src/styles.css`
- Entry: `frontend/src/main.jsx`
- Runtime config: `frontend/public/config.js`

## Local Run
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`.

## Configure API URL
File: `frontend/public/config.js`

```js
window.APP_CONFIG = {
  API_BASE_URL: "https://api.yourdomain.com"
};
```

- Same-domain deployment: use `""`
- Separate deployment: use backend full URL

## Build
```bash
cd frontend
npm install
npm run build
```
Build output is in `frontend/dist`.
