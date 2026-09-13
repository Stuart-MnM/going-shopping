# Going Shopping

A simple Flask shopping list app for home use. Build a list from a
shared "usual shop", then use it on your phone during the actual
shopping trip - checking items off and removing them works with
zero network connection, since that part runs entirely on the
phone until you're back online.

## Running it

1. Create and activate a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate   (Windows)
   source .venv/bin/activate   (Mac/Linux)
   ```

2. Install dependencies:
   ```
   pip install flask openpyxl
   ```

3. You'll need your own HTTPS certificate for local network access
   from a phone (e.g. via [mkcert](https://github.com/FiloSottile/mkcert)).
   Update the certificate filenames in `app.py`'s `ssl_context` to
   match your own, or run without `ssl_context` for local-only
   testing without a phone.

4. Run it:
   ```
   python app.py
   ```

## Notes

- `usual_shop.json`, `today_list.json`, `checked_items.json`, and
  `shopping_history.json` are created automatically on first run
  and are intentionally not tracked in git - they're your personal
  data, not part of the app.
- The one place JavaScript is used client-side (`static/app-offline.js`)
  handles the actual shopping trip - starting it, checking items
  off, removing them, and finishing up - entirely offline, syncing
  back to the server once there's a connection again. Everything
  else (managing the usual shop list, viewing history, exporting
  to Excel) is plain server-rendered pages that need a connection,
  by design - deliberately kept as simple as possible.
