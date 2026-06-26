# zb-shared

Geteilte Bibliotheken für die Zitzelsberger-Apps — **eine Quelle statt kopierter Module**
(Konsolidierungsplan P2.2/P2.3, Entscheidung `[d-303]`). Kartografie: `wissen/kartografie.md` K6.

## Einbinden (pro App)

In die `requirements.txt` der App:

```
zb-shared @ git+https://github.com/Marketing-Zizzi/zb-shared@v0.1.0
```

(Version pinnen = reproduzierbar. Update = Tag erhöhen + neu deployen.)

## Module

### `zb_shared.ki_client` — kanonischer KI-Zugang (EU-Default)
Ersetzt die kopierten `vertex_embeddings.py` + per-App `ANTHROPIC_BACKEND`-Switches.

```python
from zb_shared import ki_client

vecs = ki_client.embed_batch_sync(["text"], kind="passage")   # Vertex 768, EU (europe-west3)
qv   = ki_client.embed_query("frage")
claude = ki_client.get_anthropic_async()   # AsyncAnthropic (direct/US) ODER AsyncAnthropicVertex (EU)
model  = ki_client.claude_model()          # passendes Modell je Backend (@version bei Vertex)
```

**Konfiguration (ENV, pro Dienst):**
- `ANTHROPIC_BACKEND` = `vertex` (EU) | `direct` (US, Default)
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` = kompletter Service-Account-JSON (Render-Secret) — **Pro-Dienst-Secret** statt geteilter Datei (P2.3)
- optional: `VERTEX_EMBED_LOCATION` (europe-west3), `VERTEX_CLAUDE_LOCATION` (europe-west1), `ANTHROPIC_MODEL_VERTEX`

### geplant (P2.2 Audit-Libs)
`stt` (Spracherkennung-Switcher), `exif` (Foto-Plausibilität), `vision` (Foto-KI), `mailer` (Resend + Logo), `pdf` — extrahiert aus Reklamation/QualiCheck/Objektaudit/Objektbesuch.

## Stand
v0.1.0 — `ki_client` fertig. Audit-Libs folgen Reihe-für-Reihe.
