from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import genanki, tempfile, os, json

app = Flask(__name__)
app.config["SERVER_NAME"] = None
CORS(app, resources={r"/*": {"origins": "*"}})

MODEL_ID = 1607392319
DECK_IDS = {"USMLE": 2059400110, "MCAT": 2059400111, "LSAT": 2059400112}

CARD_CSS = """
.card { font-family: 'Helvetica Neue', Arial, sans-serif; background: #fff; max-width: 620px; margin: 0 auto; }
hr { border: none; border-top: 1px solid #e5e7eb; margin: 16px 0; }
table { width: 100%; border-collapse: collapse; }
td { padding: 5px 10px 5px 0; font-size: 14px; vertical-align: top; }
.label { color: #9ca3af; width: 110px; font-size: 12px; }
.correct { color: #16a34a; font-weight: 700; }
.incorrect { color: #dc2626; font-weight: 700; }
"""

FRONT = """
<div style="padding:28px 24px 20px">
  <div style="font-size:10px;color:#c9a84c;letter-spacing:2px;text-transform:uppercase;margin-bottom:14px;font-weight:600">VIMA VIMA · {{Mode}}</div>
  <div style="font-size:19px;font-weight:600;color:#111;line-height:1.55">{{Front}}</div>
  <div style="margin-top:20px;font-size:11px;color:#d1d5db;text-align:right">tap to reveal ↓</div>
</div>"""

BACK = """
<div style="padding:24px">
  <div style="font-size:10px;color:#c9a84c;letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;font-weight:600">VIMA VIMA · {{Mode}}</div>
  <div style="font-size:16px;font-weight:600;color:#111;margin-bottom:14px;line-height:1.45">{{Front}}</div>
  <hr>
  <table>
    <tr><td class="label">Result</td><td class="{{ResultClass}}">{{Result}}</td></tr>
    {{#Concept}}<tr><td class="label">Concept</td><td>{{Concept}}</td></tr>{{/Concept}}
    {{#Subject}}<tr><td class="label">Subject</td><td>{{Subject}}</td></tr>{{/Subject}}
    {{#QType}}<tr><td class="label">Type</td><td>{{QType}}</td></tr>{{/QType}}
    {{#Why}}<tr><td class="label">Why</td><td>{{Why}}</td></tr>{{/Why}}
    {{#Resource}}<tr><td class="label">Review</td><td style="color:#3b82f6;font-weight:500">{{Resource}}</td></tr>{{/Resource}}
    {{#Notes}}<tr><td class="label">Notes</td><td style="font-style:italic">{{Notes}}</td></tr>{{/Notes}}
    {{#Session}}<tr><td class="label">Session</td><td style="color:#9ca3af;font-size:12px">{{Session}}</td></tr>{{/Session}}
  </table>
</div>"""

def make_model(mode):
    return genanki.Model(MODEL_ID, f"VIMA VIMA · {mode}",
        fields=[{"name": f} for f in ["Front","Result","ResultClass","Concept","Subject","QType","Why","Resource","Notes","Session","Mode"]],
        templates=[{"name": "Card", "qfmt": FRONT, "afmt": BACK}],
        css=CARD_CSS)

@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return r

@app.route("/", methods=["GET"])
def root():
    return jsonify({"status": "ok", "service": "VIMA VIMA Anki Export"})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "VIMA VIMA Anki Export"})

@app.route("/export/apkg", methods=["POST","OPTIONS"])
def export_apkg():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    try:
        data = request.get_json(force=True)
        deck_name = data.get("deck_name", "VIMA VIMA")
        mode = data.get("mode", "USMLE")
        cards = [q for q in data.get("questions", []) if q.get("ankiFront","").strip()]
        if not cards:
            return jsonify({"error": "No flashcards found."}), 400

        model = make_model(mode)
        deck = genanki.Deck(DECK_IDS.get(mode, 2059400110), f"VIMA VIMA · {deck_name}")
        for q in cards:
            ok = q.get("result") == "correct"
            deck.add_note(genanki.Note(model=model, fields=[
                q.get("ankiFront",""),
                "✓  Correct" if ok else "✗  Incorrect",
                "correct" if ok else "incorrect",
                q.get("concept",""), q.get("subject",""), q.get("qtype",""),
                q.get("correctReason","") if ok else q.get("wrongReason",""),
                q.get("resource",""), q.get("notes",""),
                q.get("session", deck_name), mode,
            ]))

        tmp = tempfile.NamedTemporaryFile(suffix=".apkg", delete=False)
        tmp.close()
        genanki.Package(deck).write_to_file(tmp.name)
        safe = deck_name.replace(" ","_").replace("/","-")
        return send_file(tmp.name, mimetype="application/octet-stream",
                        as_attachment=True, download_name=f"VIMAVIMA_{safe}.apkg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
