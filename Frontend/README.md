# HealthSync OS frontend

Plain HTML/CSS/JS, no build step. Based on the "HealthSync OS Dashboard Mockup" artifact.

Run (from this folder, e.g. in the PyCharm terminal):

    python -m http.server 5173

Then open http://localhost:5173

Files
- index.html  page structure and the two static SVG charts
- styles.css  styles
- data.js     mock data for the demo (swap for fetch() calls to FastAPI later)
- app.js      renders status, steps, supply and trace; handles Approve, Reset and nav

Demo flow: "Approve and submit" moves the pipeline to its submitted state; "Reset demo" returns to the start.
