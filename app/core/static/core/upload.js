/* Previa do arquivo escolhido, antes de enviar.
   Arquivo separado de proposito: a CSP nao permite script embutido. */
(function () {
  "use strict";
  var entrada = document.getElementById("id_arquivo");
  var caixa = document.getElementById("previa");
  if (!entrada || !caixa) return;

  var IMAGENS = ["png", "jpg", "jpeg", "gif", "webp"];

  entrada.addEventListener("change", function () {
    caixa.textContent = "";
    caixa.hidden = true;
    var arquivo = entrada.files && entrada.files[0];
    if (!arquivo) return;

    var ext = (arquivo.name.split(".").pop() || "").toLowerCase();
    var tamanho = arquivo.size < 1024 * 1024
      ? (arquivo.size / 1024).toFixed(1) + " KB"
      : (arquivo.size / 1024 / 1024).toFixed(1) + " MB";

    var linha = document.createElement("div");
    linha.className = "previa-linha";

    if (IMAGENS.indexOf(ext) !== -1) {
      var img = document.createElement("img");
      img.alt = "";
      img.src = URL.createObjectURL(arquivo);
      img.addEventListener("load", function () { URL.revokeObjectURL(img.src); });
      linha.appendChild(img);
    } else {
      var selo = document.createElement("span");
      selo.className = "previa-ext";
      selo.textContent = ext.toUpperCase().slice(0, 4) || "?";
      linha.appendChild(selo);
    }

    var texto = document.createElement("span");
    // textContent, nunca innerHTML: o nome vem do usuario
    texto.textContent = arquivo.name + " · " + tamanho;
    linha.appendChild(texto);

    caixa.appendChild(linha);
    caixa.hidden = false;
  });
})();
