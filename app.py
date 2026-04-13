from flask import Flask, render_template, request, send_file
import os
import zipfile
from extractor import processar_pdf

app = Flask(__name__)
UPLOAD_FOLDER = "/tmp"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    arquivos = request.files.getlist("files")

    caminhos_csv = []

    for arquivo in arquivos:
        caminho_pdf = os.path.join(UPLOAD_FOLDER, arquivo.filename)
        arquivo.save(caminho_pdf)

        caminho_csv = processar_pdf(caminho_pdf)
        caminhos_csv.append(caminho_csv)

    zip_path = os.path.join(UPLOAD_FOLDER, "resultado.zip")

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for caminho in caminhos_csv:
            zipf.write(caminho, os.path.basename(caminho))

    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
