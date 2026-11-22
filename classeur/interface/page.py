"""Interface du Classeur : une page, aucun CDN, aucune dépendance.

Parti pris visuel : une chemise cartonnée et des feuilles posées dessus. Fond
papier, titres en serif, dates en monospace, tampons pour les statuts. Rien de
commun avec une interface de terminal : ici tout doit ressembler à un dossier
qu'on ouvre, pas à une console.
"""

INDEX_HTML = r'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Le Classeur — agent local d'échéances</title>
<style>
  :root{
    --papier:#f8f3e7; --carton:#e7dcc6; --bord:#cbbfa6; --encre:#28231d;
    --gris:#645a4c; --brique:#a5432a; --olive:#5f6b45; --bleu:#33556b;
    --mono:ui-monospace,"SFMono-Regular","DejaVu Sans Mono",monospace;
    --serif:"Iowan Old Style",Georgia,"Times New Roman",serif;
  }
  *{box-sizing:border-box}
  html,body{background:#ded4c0}
  body{
    margin:0;color:var(--encre);font:15px/1.6 ui-sans-serif,system-ui,"Segoe UI",Roboto,sans-serif;
    background-image:repeating-linear-gradient(0deg,rgba(120,100,70,.05) 0 1px,transparent 1px 4px);
  }
  .chemise{max-width:1180px;margin:26px auto 60px;background:var(--carton);border:1px solid var(--bord);
    border-radius:6px;box-shadow:0 18px 40px rgba(60,45,25,.18)}
  .onglet{display:flex;align-items:flex-end;gap:14px;padding:16px 26px 0}
  .onglet .titre{font-family:var(--serif);font-size:34px;line-height:1;margin:0;letter-spacing:.3px}
  .onglet .titre em{font-style:italic;color:var(--brique)}
  .onglet .sous{font-family:var(--mono);font-size:11.5px;text-transform:uppercase;letter-spacing:.16em;color:var(--gris);padding-bottom:4px}
  .cachet{margin-left:auto;transform:rotate(-6deg);border:2px solid var(--brique);color:var(--brique);
    border-radius:4px;padding:5px 12px;font-family:var(--mono);font-size:11px;letter-spacing:.18em;
    text-transform:uppercase;opacity:.85;text-align:center;line-height:1.3}
  .interieur{display:grid;grid-template-columns:minmax(300px,.9fr) minmax(380px,1.3fr);gap:22px;padding:20px 26px 28px;align-items:stretch}
  @media (max-width:940px){.interieur{grid-template-columns:1fr}}
  .legende{font-family:var(--mono);font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--gris);
    border-bottom:1px solid var(--bord);padding-bottom:6px;margin:0 0 12px;display:flex;gap:8px;align-items:baseline}
  .legende span{margin-left:auto;letter-spacing:0;text-transform:none;font-size:11px}

  .piece{position:relative;background:var(--papier);border:1px solid var(--bord);border-radius:4px;
    padding:14px 16px 14px 30px;margin-bottom:12px;box-shadow:0 2px 0 rgba(90,70,40,.07)}
  .piece::before,.piece::after{content:"";position:absolute;left:11px;width:9px;height:9px;border-radius:50%;
    background:var(--carton);border:1px solid var(--bord)}
  .piece::before{top:18px}
  .piece::after{bottom:18px}
  .piece h3{font-family:var(--serif);font-size:18px;margin:0 0 4px;font-weight:600}
  .piece p{margin:0 0 10px;font-size:13.5px;color:#4a4238}
  .fiche{display:flex;gap:14px;flex-wrap:wrap;font-family:var(--mono);font-size:11.5px;color:var(--gris);
    border-top:1px dotted var(--bord);padding-top:8px;margin-bottom:11px}
  .fiche b{color:var(--encre);font-weight:600}
  .boutons{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
  button{font:inherit;cursor:pointer;border-radius:3px;padding:7px 13px;font-size:13px;
    background:var(--papier);color:var(--encre);border:1px solid var(--encre)}
  button:hover{background:#fffdf6}
  button:focus-visible{outline:2px solid var(--brique);outline-offset:2px}
  button.fort{background:var(--encre);color:var(--papier);border-color:var(--encre);font-weight:600}
  button.fort:hover{background:#3a332a}
  button:disabled{opacity:.5;cursor:progress}
  button.discret{border-style:dashed;border-color:var(--gris);color:#5b5245;font-size:12.5px}

  .reglage{background:var(--papier);border:1px solid var(--bord);border-radius:4px;padding:10px 16px}
  .reglage summary{cursor:pointer;font-family:var(--mono);font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--gris)}
  .reglage p{font-size:13px;color:#4a4238;margin:10px 0}
  .champ{display:grid;grid-template-columns:84px 1fr;gap:8px;align-items:center;margin-bottom:7px}
  .champ label{font-family:var(--mono);font-size:11px;color:var(--gris)}
  input{width:100%;background:#fffdf6;border:1px solid var(--bord);border-radius:3px;color:var(--encre);
    padding:6px 8px;font-family:var(--mono);font-size:12px}
  input:focus-visible{outline:2px solid var(--brique);outline-offset:1px}

  .feuille{position:relative;background:var(--papier);border:1px solid var(--bord);border-radius:4px;
    padding:20px 22px 22px 34px;box-shadow:0 2px 0 rgba(90,70,40,.07);min-height:330px;display:flex;flex-direction:column}
  .feuille::before{content:"";position:absolute;left:22px;top:0;bottom:0;width:1px;background:rgba(165,67,42,.35)}
  .feuille h2{font-family:var(--serif);font-size:22px;margin:0 0 2px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
  .feuille .objectif{font-size:13.5px;color:#4a4238;margin:0 0 14px;max-width:62ch}
  .vide{color:var(--gris);font-size:13.5px;margin:auto 0;padding:60px 0;text-align:center}
  .tableau{border-top:1px solid var(--encre);border-bottom:1px solid var(--encre);padding:7px 0;margin-bottom:14px}
  .ligne{display:flex;align-items:baseline;font-family:var(--mono);font-size:12.5px;padding:1px 0}
  .ligne .pt{flex:1;border-bottom:1px dotted var(--bord);margin:0 8px 3px}
  .ligne b{font-weight:700}
  .tampon{transform:rotate(-4deg);border:2px solid var(--olive);color:var(--olive);border-radius:3px;
    padding:2px 9px;font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase}
  .tampon.ko{border-color:var(--brique);color:var(--brique)}
  .pieces-jointes{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 14px}
  .piece-j{font-family:var(--mono);font-size:11.5px;background:#fffdf6;border:1px solid var(--bord);border-radius:3px;
    padding:4px 9px;color:var(--bleu);text-decoration:none}
  .piece-j:hover{border-color:var(--bleu)}
  pre{font-family:var(--mono);font-size:12px;line-height:1.5;white-space:pre-wrap;word-break:break-word;margin:0}
  .lecteur{background:#fffdf6;border:1px solid var(--bord);border-radius:3px;padding:12px;max-height:36vh;overflow:auto}
  .etapes{display:flex;flex-direction:column;gap:0;margin-top:6px}
  .etape{display:grid;grid-template-columns:26px 1fr;gap:10px;padding:8px 0;border-bottom:1px dotted var(--bord)}
  .etape:last-child{border-bottom:0}
  .etape .num{font-family:var(--mono);font-size:11px;color:var(--gris);padding-top:2px;text-align:right}
  .etape .outil{font-family:var(--mono);font-size:11.5px;letter-spacing:.06em;color:var(--brique)}
  .etape .outil .passe{color:var(--gris);letter-spacing:0;margin-left:6px}
  .etape .pensee{font-size:12.5px;color:#5b5245;font-style:italic;font-family:var(--serif);margin:2px 0 4px}
  .etape pre{color:#3c352c;background:#f3ecdd;border-radius:3px;padding:6px 8px;max-height:132px;overflow:auto}
  .etape.ko pre{background:#f7e7e2;color:#7d2d18}
  .marge{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin:16px 0 6px}
  .marge .lg{font-family:var(--mono);font-size:10.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--gris)}
  .comparaison{font-family:var(--mono);font-size:12px;background:#fffdf6;border-left:3px solid var(--olive);
    padding:8px 10px;margin-bottom:14px}
  .note{border:1px dashed var(--bord);border-radius:3px;padding:10px 12px;font-size:12.5px;color:#5b5245;margin-top:14px;
    background:rgba(255,253,246,.6)}
  .note b{color:var(--encre)}
  footer{padding:6px 26px 22px;font-family:var(--mono);font-size:10.5px;color:var(--gris);letter-spacing:.04em}
  .erreur{border-left:3px solid var(--brique);background:#f7e7e2;padding:8px 10px;font-family:var(--mono);font-size:12px}
</style>
</head>
<body>
<div class="chemise">
  <div class="onglet">
    <div>
      <h1 class="titre">Le <em>Classeur</em></h1>
      <div class="sous">agent local · vos papiers ne sortent pas de la machine</div>
    </div>
    <div class="cachet">candidature<br>AI&nbsp;Entry</div>
  </div>

  <div class="interieur">
    <section aria-labelledby="t-pieces">
      <h2 class="legende" id="t-pieces">Pièces du dossier <span id="nb-pieces"></span></h2>
      <div id="pieces"><p class="vide">chargement…</p></div>

      <details class="reglage">
        <summary>Régler un serveur de modèle local</summary>
        <p>Sans réglage, l'agent suit une cassette enregistrée : les décisions sont rejouées, les outils s'exécutent pour de vrai. Avec un serveur compatible OpenAI (Ollama, LM Studio, vLLM), c'est le modèle qui choisit chaque étape.</p>
        <div class="champ"><label for="url">URL</label><input id="url" value="http://127.0.0.1:11434" spellcheck="false"></div>
        <div class="champ"><label for="modele">modèle</label><input id="modele" value="qwen2.5-coder:7b" spellcheck="false"></div>
        <div class="boutons" style="margin-top:10px">
          <button id="sonder" class="discret">Sonder le serveur</button>
          <span id="sonde" style="font-family:var(--mono);font-size:11.5px;color:var(--gris)"></span>
        </div>
      </details>

      <div class="note" id="procedures">
        <b>Procédures apprises.</b> L'agent écrit une procédure après une erreur, sur le disque, hors du dossier du run : elle est relue au run suivant. <span id="liste-procedures">Aucune pour l'instant.</span>
      </div>

      <div class="note">
        <b>Ce qu'il ne fait pas encore.</b> Pas d'OCR : un PDF scanné est refusé, pas deviné. Pas de surveillance continue, pas d'envoi de courriel : l'alerte est un fichier. Et rien n'est encore écrit pour Windows ou macOS.
      </div>
    </section>

    <section aria-labelledby="t-releve">
      <h2 class="legende" id="t-releve">Relevé</h2>
      <div class="feuille" id="feuille">
        <p class="vide">Ouvrez une pièce à gauche. Le run dure moins d'une seconde et écrit de vrais fichiers, consultables ici.</p>
      </div>
    </section>
  </div>

  <footer>Classeur · MIT · documents de démonstration synthétiques (identités inventées, domaines .invalid) · aucun appel sortant en mode cassette</footer>
</div>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const STATUT = {done: "terminé", budget: "budget atteint"};

async function api(chemin, options) {
  const reponse = await fetch(chemin, options);
  const texte = await reponse.text();
  try { return JSON.parse(texte); } catch (e) { return { error: texte || reponse.statusText }; }
}

function rendrePieces(donnees) {
  const boite = $("#pieces");
  const pieces = donnees.dossiers || donnees.scenarios || [];
  $("#nb-pieces").textContent = pieces.length ? pieces.length + " pièces" : "";
  if (!pieces.length) { boite.innerHTML = '<p class="vide">aucune pièce</p>'; return; }
  boite.innerHTML = pieces.map((s) => `
    <article class="piece">
      <h3>${esc(s.title)}</h3>
      <p>${esc(s.objective)}</p>
      <div class="fiche">
        <span>budget <b>${s.budget}</b> étapes</span>
        <span><b>${s.fixtures.length}</b> document(s)</span>
        ${s.learning ? "<span>deux passes</span>" : ""}
        <span>réf. <b>${esc(s.as_of || "du jour")}</b></span>
      </div>
      <div class="boutons">
        <button class="fort" data-ouvrir="${esc(s.slug)}">Ouvrir la pièce</button>
        <button class="discret" data-modele="${esc(s.slug)}">Confier au modèle local</button>
      </div>
    </article>`).join("");
  boite.querySelectorAll("[data-ouvrir]").forEach((b) => b.addEventListener("click", () => lancer(b.dataset.ouvrir, "cassette", b)));
  boite.querySelectorAll("[data-modele]").forEach((b) => b.addEventListener("click", () => lancer(b.dataset.modele, "modele", b)));
}

function rendreProcedures(liste) {
  const cible = $("#liste-procedures");
  if (!liste || !liste.length) { cible.textContent = "Aucune pour l'instant."; return; }
  cible.innerHTML = liste.map((p) => `<br>· <b>${esc(p.name)}</b> <span style="color:var(--gris)">(${esc(p.scenario)}, ${p.chars} car.)</span>`).join("");
}

async function lancer(slug, mode, bouton) {
  const etiquette = bouton ? bouton.textContent : "";
  if (bouton) { bouton.disabled = true; bouton.textContent = "en cours…"; }
  $("#feuille").innerHTML = '<p class="vide">le classeur est ouvert, l\'agent travaille…</p>';
  const corps = { scenario: slug, mode };
  if (mode === "modele") { corps.base_url = $("#url").value; corps.model = $("#modele").value; }
  const r = await api("/api/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) });
  if (r.error) { $("#feuille").innerHTML = `<div class="erreur">${esc(r.error)}</div>`; }
  else { rendreReleve(r); }
  if (bouton) { bouton.disabled = false; bouton.textContent = etiquette; }
  const frais = await api("/api/scenarios");
  rendreProcedures(frais.skills);
}

function ligne(cle, valeur) {
  return `<div class="ligne"><span>${esc(cle)}</span><span class="pt"></span><b>${esc(valeur)}</b></div>`;
}

function rendreReleve(r) {
  const deuxPasses = r.passes.length > 1;
  const etapes = r.steps.map((e) => `
    <div class="etape ${e.ok ? "" : "ko"}">
      <div class="num">${e.step}</div>
      <div>
        <div class="outil">${esc(e.tool)}<span class="passe">${esc(e.pass)}</span></div>
        <div class="pensee">${esc(e.thought)}</div>
        <pre>${esc(e.ok ? apercu(e.observation.result) : "✗ " + e.observation.error)}</pre>
      </div>
    </div>`).join("");
  const joints = r.artifacts.map((a) => `<a class="piece-j" href="#" data-piece="${esc(a.name)}">${esc(a.name)} — ${(a.bytes / 1024).toFixed(1)} ko</a>`).join("");
  const comparaison = deuxPasses ? `<div class="comparaison">${r.passes.map((p) => `${esc(p.label)} : <b>${p.steps}</b> étapes, <b>${p.errors}</b> erreur(s)`).join(" &nbsp;→&nbsp; ")}</div>` : "";
  $("#feuille").innerHTML = `
    <h2>${esc(r.title)} <span class="tampon ${r.status === "done" ? "" : "ko"}">${esc(STATUT[r.status] || r.status)}</span></h2>
    <p class="objectif">${esc(r.objective)}</p>
    <div class="tableau">
      ${ligne("mode", r.mode === "modele" ? "modèle local" : "cassette")}
      ${ligne("étapes", r.steps.length)}
      ${ligne("erreurs", r.errors)}
      ${ligne("date de référence", r.as_of)}
    </div>
    ${comparaison}
    <div class="marge"><span class="lg">pièces au dossier</span></div>
    <div class="pieces-jointes">${joints || '<span class="vide">aucune pièce écrite</span>'}</div>
    <div class="lecteur" id="lecteur"><pre>${esc(r.final || "(pas de conclusion)")}</pre></div>
    <div class="marge"><span class="lg">journal des étapes</span><span class="lg">${r.steps.length} ligne(s)</span></div>
    <div class="etapes">${etapes}</div>`;
  $("#feuille").querySelectorAll("[data-piece]").forEach((a) => a.addEventListener("click", async (ev) => {
    ev.preventDefault();
    const reponse = await fetch(`/api/artifact?run=${encodeURIComponent(r.run_id)}&name=${encodeURIComponent(a.dataset.piece)}`);
    $("#lecteur").innerHTML = `<pre>${esc(await reponse.text())}</pre>`;
    $("#lecteur").scrollTop = 0;
  }));
}

function apercu(resultat) {
  if (resultat === null || resultat === undefined) return "";
  if (typeof resultat !== "object") return String(resultat);
  return JSON.stringify(resultat, null, 1).slice(0, 900);
}

$("#sonder").addEventListener("click", async () => {
  $("#sonde").textContent = "…";
  const p = await api("/api/probe", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ base_url: $("#url").value }) });
  if (p.error) { $("#sonde").textContent = p.error; return; }
  $("#sonde").textContent = `${p.models.length} modèle(s) : ${p.models.slice(0, 3).join(", ")}`;
  if (p.models.length) $("#modele").value = p.models[0];
});

(async () => { const d = await api("/api/scenarios"); rendrePieces(d); rendreProcedures(d.skills); })();
</script>
</body>
</html>
'''
