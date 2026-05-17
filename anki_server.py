"""
VIMA VIMA — Anki .apkg Generator Backend
Deploy on Railway or Render (free tier).

Install: pip install flask genanki flask-cors
Run:     python anki_server.py
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import genanki
import tempfile
import os
import json

app = Flask(__name__)
app.config["SERVER_NAME"] = None
CORS(app, origins="*", allow_headers=["Content-Type"], methods=["GET","POST","OPTIONS"])

# Stable IDs
MODEL_ID = 1607392319
DECK_IDS = {
    "USMLE": 2059400110,
    "MCAT":  2059400111,
    "LSAT":  2059400112,
}

CARD_CSS = """
.card {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  background: #ffffff;
  max-width: 620px;
  margin: 0 auto;
  padding: 0;
}
hr { border: none; border-top: 1px solid #e5e7eb; margin: 16px 0; }
table { width: 100%; border-collapse: collapse; }
td { padding: 5px 10px 5px 0; font-size: 14px; vertical-align: top; }
.label { color: #9ca3af; width: 110px; font-size: 12px; letter-spacing: 0.5px; }
.correct { color: #16a34a; font-weight: 700; }
.incorrect { color: #dc2626; font-weight: 700; }
"""

FRONT_TMPL = """
<div style="padding: 28px 24px 20px;">
  <div style="font-size: 10px; color: #c9a84c; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 14px; font-weight: 600;">
    VIMA VIMA &nbsp;·&nbsp; {{Mode}}
  </div>
  <div style="font-size: 19px; font-weight: 600; color: #111; line-height: 1.55;">
    {{Front}}
  </div>
  <div style="margin-top: 20px; font-size: 11px; color: #d1d5db; text-align: right;">
    tap to reveal ↓
  </div>
</div>
"""

BACK_TMPL = """
<div style="padding: 24px;">
  <div style="font-size: 10px; color: #c9a84c; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; font-weight: 600;">
    VIMA VIMA &nbsp;·&nbsp; {{Mode}}
  </div>
  <div style="font-size: 16px; font-weight: 600; color: #111; margin-bottom: 14px; line-height: 1.45;">
    {{Front}}
  </div>
  <hr>
  <table>
    <tr><td class="label">Result</td><td class="{{ResultClass}}">{{Result}}</td></tr>
    {{#Concept}}<tr><td class="label">Concept</td><td style="color:#111;">{{Concept}}</td></tr>{{/Concept}}
    {{#Subject}}<tr><td class="label">Subject</td><td style="color:#111;">{{Subject}}</td></tr>{{/Subject}}
    {{#QType}}<tr><td class="label">Type</td><td style="color:#111;">{{QType}}</td></tr>{{/QType}}
    {{#Why}}<tr><td class="label">Why</td><td style="color:#111;">{{Why}}</td></tr>{{/Why}}
    {{#Resource}}<tr><td class="label">Review</td><td style="color:#3b82f6;font-weight:500;">{{Resource}}</td></tr>{{/Resource}}
    {{#Notes}}<tr><td class="label">Notes</td><td style="color:#374151;font-style:italic;">{{Notes}}</td></tr>{{/Notes}}
    {{#Session}}<tr><td class="label">Session</td><td style="color:#9ca3af;font-size:12px;">{{Session}}</td></tr>{{/Session}}
  </table>
</div>
"""

def make_model(mode):
    return genanki.Model(
        MODEL_ID,
        f"VIMA VIMA · {mode}",
        fields=[
            {"name": "Front"}, {"name": "Result"}, {"name": "ResultClass"},
            {"name": "Concept"}, {"name": "Subject"}, {"name": "QType"},
            {"name": "Why"}, {"name": "Resource"}, {"name": "Notes"},
            {"name": "Session"}, {"name": "Mode"},
        ],
        templates=[{"name": "VIMA VIMA Card", "qfmt": FRONT_TMPL, "afmt": BACK_TMPL}],
        css=CARD_CSS,
    )

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "VIMA VIMA Anki Export"})

@app.route("/export/apkg", methods=["POST", "OPTIONS"])
def export_apkg():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        data = request.get_json(force=True)
        deck_name = data.get("deck_name", "VIMA VIMA Deck")
        mode = data.get("mode", "USMLE")
        questions = data.get("questions", [])
        cards = [q for q in questions if q.get("ankiFront", "").strip()]

        if not cards:
            return jsonify({"error": "No flashcards found."}), 400

        model = make_model(mode)
        deck = genanki.Deck(DECK_IDS.get(mode, 2059400110), f"VIMA VIMA · {deck_name}")

        for q in cards:
            is_correct = q.get("result") == "correct"
            why = q.get("correctReason", "") if is_correct else q.get("wrongReason", "")
            note = genanki.Note(model=model, fields=[
                q.get("ankiFront", ""),
                "✓  Correct" if is_correct else "✗  Incorrect",
                "correct" if is_correct else "incorrect",
                q.get("concept", ""), q.get("subject", ""), q.get("qtype", ""),
                why, q.get("resource", ""), q.get("notes", ""),
                q.get("session", deck_name), mode,
            ])
            deck.add_note(note)

        tmp = tempfile.NamedTemporaryFile(suffix=".apkg", delete=False)
        tmp_path = tmp.name
        tmp.close()
        genanki.Package(deck).write_to_file(tmp_path)

        safe_name = deck_name.replace(" ", "_").replace("/", "-")
        return send_file(tmp_path, mimetype="application/octet-stream",
                        as_attachment=True, download_name=f"VIMAVIMA_{safe_name}.apkg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            if 'tmp_path' in locals(): os.unlink(tmp_path)
        except: pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
