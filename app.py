from flask import Flask, request, jsonify, render_template

app = Flask(
    __name__,
    template_folder="views/templates",
    static_folder="views/static"
)  

# ── Halaman Utama ──
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)