"""Tiny Python script that runs inside the sandbox to relay a single
HTTP request to the gateway, plus the host-side constants that drive it
through :meth:`BackendBase.exec_shell`.

Flow: host spawns ``python3 -c <SHIM_SCRIPT> ...`` via ``exec_shell``;
the shim calls the gateway's loopback port using ``urllib.request`` and
emits one JSON envelope on stdout::

    {
        "status": <int>,                  # HTTP status, or -1 on error
        "body":   "<base64-of-bytes>",    # inline when small
        "body_file": "<sandbox-path>",    # spilled when > inline_limit
        "error":  "<short message>"       # only when status == -1
    }

The gateway listens only on the sandbox's loopback; the host has no
network reachability to it. The shim relies on ``python3`` (which the
gateway venv already needs) rather than ``curl`` because we cannot
assume ``curl`` on every backend image.
"""
from __future__ import annotations
BODY_INLINE_LIMIT = 4 * 1024 * 1024
SANDBOX_TMP_DIR = '/tmp'
SHIM_SCRIPT = '\nimport sys, json, base64, uuid, os\nimport urllib.request, urllib.error\n\nmethod = sys.argv[1]\nurl = sys.argv[2]\nbody_file = sys.argv[3]\ninline_limit = int(sys.argv[4])\ntmp_dir = sys.argv[5]\nauth_token = sys.argv[6] if len(sys.argv) > 6 else ""\n\nbody = None\nif body_file:\n    with open(body_file, "rb") as f:\n        body = f.read()\n\nreq = urllib.request.Request(url, data=body, method=method)\nif body is not None:\n    req.add_header("Content-Type", "application/json")\nif auth_token:\n    req.add_header("Authorization", "Bearer " + auth_token)\n\ntry:\n    with urllib.request.urlopen(req) as resp:\n        status = int(resp.status)\n        resp_body = resp.read()\nexcept urllib.error.HTTPError as e:\n    status = int(e.code)\n    try:\n        resp_body = e.read()\n    except Exception:\n        resp_body = b""\nexcept Exception as e:\n    json.dump(\n        {"status": -1, "error": type(e).__name__ + ": " + str(e)},\n        sys.stdout,\n    )\n    sys.exit(0)\n\nenv = {"status": status}\nif len(resp_body) > inline_limit:\n    p = os.path.join(tmp_dir, uuid.uuid4().hex + ".bin")\n    with open(p, "wb") as f:\n        f.write(resp_body)\n    env["body_file"] = p\nelse:\n    env["body"] = base64.b64encode(resp_body).decode("ascii")\njson.dump(env, sys.stdout)\n'