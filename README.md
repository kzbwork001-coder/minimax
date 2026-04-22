# minimax

Wrapper for Max API.

## Install

```bash
pip install mini-max-wrapper
```

You still `import minimax` in code — only the package name on PyPI differs.

## Run from source (without pip)

If you cloned the repo and want to run the examples without installing the
package, just put `src/` on `PYTHONPATH` so Python can find `minimax`.

First, install the runtime dependencies declared in `pyproject.toml`. Pick one:

```bash
# pip — read deps from pyproject.toml directly (no package install)
pip install $(python -c "import tomllib; print(' '.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))")

# or uv — same idea
uv pip install $(python -c "import tomllib; print(' '.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))")
```

Then run an example with `src/` on the path:

Linux / macOS:

```bash
PYTHONPATH=src python examples/socket_phone.py 79001234567
```

Windows (PowerShell):

```powershell
$env:PYTHONPATH = "src"
python examples\socket_phone.py 79001234567
```

Windows (cmd):

```cmd
set PYTHONPATH=src
python examples\socket_phone.py 79001234567
```

## Console examples

If you just want to try the library from a terminal — no browser, no WebSocket
server — the `examples/` folder has small scripts that prompt for input right
in the console:

- `socket_phone.py` — phone + SMS login. It asks you for the SMS code (and the
  2FA password, if needed) via `input()`.
- `socket_token.py` / `web_token.py` — log in using a token you already have.
- `web_qr.py` — QR login. The link is printed in the terminal; open it or
  paste it into a QR generator to scan.

Run them like this:

```bash
python examples/socket_phone.py 79001234567
python examples/socket_token.py 79001234567 YOUR_TOKEN
python examples/web_qr.py 79001234567
python examples/web_token.py 79001234567 YOUR_TOKEN
```

After login each script calls `dump_account(client)`, which prints your
contacts, chats, and recent messages to the terminal. Use these when you just
want to poke at the API. For real applications, use the bridge pattern below.

## Bridge examples

The `examples/` folder contains tiny end-to-end demos showing how to drive the
library from a browser through a WebSocket to your backend. Two flavors:

- `socket_ws_bridge.py` + `socket_ws_bridge.html` — phone + SMS login.
- `web_ws_bridge.py` + `web_ws_bridge.html` — QR code login.

### How to run

1. Start the backend:

   ```bash
   python examples/socket_ws_bridge.py
   # or
   python examples/web_ws_bridge.py
   ```

   It opens a WebSocket server on `ws://localhost:8765`.

2. Open the matching `.html` file in a browser (just double-click it).

3. Use the form:
   - **Socket**: enter your phone → click Connect → type the SMS code you
     receive → if asked, type your 2FA password.
   - **Web**: click Connect → scan the QR with the MAX mobile app → if asked,
     type your 2FA password.

4. After login, the backend logs your contacts, chats, and recent messages to
   the terminal (`dump_account`).

### What's actually happening

- The browser (**FE**) sends small JSON messages — phone, code, password — to
  your backend (**BE**) over one WebSocket.
- The **BE** runs the minimax library and drives the login flow. Whenever the
  library needs something (SMS code, 2FA password, QR link to display), the BE
  asks the FE and waits for the answer.
- Once login succeeds, the BE holds the authenticated session. Everything the
  user does on the FE is relayed through the BE to MAX.

This is the pattern any real app using this library should follow: the
library lives on the server, the browser only talks to your backend.
