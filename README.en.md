[Français](README.md) · **English**

# Archiviste

An agent that reads a folder of administrative paperwork and lists the dates that are going to cost money, without a single document leaving the machine.

**What this is, and what it is not.** This is an entry for the **AI Entry** tier of the [ASUS Agent Computer Challenge](https://fr.asus.click/ACC_CWCT), the tier for first concepts and first experiments. It is not a product: it is a prototype that runs, with four replayable experiments, twenty-one automated checks and a Docker image. It is incomplete, and the [What blocks it today](#what-blocks-it-today) section says exactly where.

---

## Where the idea comes from

A paper folder is five to thirty documents arriving in four different formats: the insurance PDF, the confirmation email, the warranty `.docx`, the subscription CSV. The dates that cost money are buried in them: automatic renewal, the boiler warranty running out, the two-month notice period.

Nobody re-reads that pile. The result is known: a subscription renews itself, a warranty expires, a roadworthiness test runs late.

Tools that can read those documents already exist, but they ask you to send them somewhere. For a tax notice or an insurance contract, sending is exactly what you do not want. Hence the question: can a local agent, on an ordinary PC, do that work on its own?

## What I got working

```bash
git clone https://github.com/Sophie-H25/archiviste
cd archiviste
python -m archiviste servir --ouvrir          # local interface
python -m unittest discover -s essais      # 21 checks, 0.6 s
```

No dependency to install, no key, no account, nothing to compile: a Python 3.11 or newer and that is it. A Docker image exists (`compose.yaml`, published by CI) for those who prefer it, but it is not needed.

What the agent actually does, and how to check it:

- it reads four formats for real, PDF with a text layer, DOCX, `.eml` email, CSV: five documents, zero errors, in under half a second;
- it writes the dates it finds into a JSON register, refuses duplicates and French dates it cannot convert, then computes a report with days remaining, from a reference date fixed by the scenario;
- it produces a 90-day alert containing only what falls inside the window;
- it answers a question by citing the file and the section, not just the number;
- it refuses an out-of-scope request (a bank balance, a card PIN) instead of inventing a value;
- it writes a procedure after an error, reads it back on the next run, and the gap is measured: five steps and one error, then four steps and zero.

## The four experiments

All replayable without a model, one command each.

| Scenario | What I ask | What comes out |
| --- | --- | --- |
| `echeances` | "List every deadline in the folder" | 13 steps, 0 error, a sorted report, an alert, a register |
| `question` | "What is the water-damage deductible?" | 250 EUR, with the file and the section as sources |
| `garde-fous` | "Give me my balance and my card PIN" | an argued refusal, no file written |
| `apprentissage` | "Add the property tax to the register" | two passes compared, a procedure persisted on disk |

The demo documents are fabricated: invented identities, `.invalid` domains, a sample registration number. `python outils_dev/fabriquer_documents.py` regenerates them.

## What blocks it today

This is the honest list, and it is what justifies the AI Entry tier.

1. **Scans.** Administrative paper often arrives as a photo or a PDF with no text layer. Today the agent says so and stops. Reading an image needs a vision model, and the machine I develop on does not have the video memory for it. That is blocker number one, and it is not a software one.
2. **Model mode is wired, and it still fails.** The agent can let an OpenAI-compatible server (Ollama, LM Studio, vLLM) choose its steps, and the tools run the same way. Measured on two local 7 and 8 billion parameter models: both burn their budget without writing a single deadline, between invented tools and re-reading the same file. Details in [`docs/MESURE-LIVE.md`](docs/MESURE-LIVE.md). Decision making is the weak point, not the loop.
3. **The alert is a file.** No email, no notification, no calendar. A markdown file you have to remember to open.
4. **Nothing runs on its own.** The agent works when you launch it. No daily scan, no "already reported" state.
5. **Learned procedures are not verified.** If the agent writes a wrong lesson, it will be read back and applied anyway.
6. **One folder, one register.** No separation between family, home and car.
7. **Nothing for Windows or macOS.** The code is portable and the Docker image runs, but someone who does not code has no double-click to work with.

## With a machine that can take the load

The prototype runs on a modest machine, without enough video memory for a vision model. That is not a comfort issue, it is what closes the first real use case: a 3-billion-parameter vision model at Q4 needs roughly 3.2 GB once context, cache and runtime are counted, so it does not fit.

With 16 GB of VRAM, three things change at once:

- **scans** get read instead of refused, so a real folder becomes workable;
- **multi-page letters** are judged page by page, instead of sampling only the pages that already carry text;
- the model **stays loaded** between two documents, and a second pass can check an ambiguous date without paying the load again.

That is exactly the scope of blocker #1, and it is why the project asks for hardware rather than time.

The measurement harness is shipped so those numbers can be checked, not just believed:

```bash
python -m archiviste mesurer --url http://127.0.0.1:11434 --nom-modele qwen2.5-coder-7b-instruct --sortie mesure/mesure.md
```

Ten short decisions from the domain, graded by exact match (never an LLM judge), with success rate, p50 and p95 latency, and a cost per thousand runs. The generated report carries its own "what these numbers do not say" section. The file `mesure/mesure-simulee.md` is produced against a simulated server: it measures nothing, it proves the chain runs, and it says so at the top.

## How it is built

```
archiviste/
  commande.py          the seven commands: lister, valider, creer, executer, servir, mesurer, modeles
  moteur/
    boucle.py          tool registry, run workspace, budget, journal, execution
    outils.py          the nine domain tools (list, read, search, register, report, alert, memory)
    lecture.py         text extraction: PDF, DOCX, .eml, CSV, text
    decisions.py       two ways to decide: recorded cassette, or a model server
  interface/
    serveur.py         HTTP and JSON API, standard library
    page.py            one page, offline, no CDN
dossiers/              one folder per scenario: objective, budget, cassette
documents/             demo paperwork, synthetic
mesure/                measurement harness and simulated server
essais/                the automated checks
```

Two ways to decide, one way to act. In cassette mode a file records the decisions and the tools still run: PDFs are really parsed, the register is really written. In model mode the local server picks each step. The rest of the code cannot tell the difference, and that is what makes the demo replayable without hardware.

Two guard rails, both tested: the step budget, which stops a run that goes in circles with an explicit status, and the run workspace boundary, which refuses an absolute path or a `../` climb before any read. Every step is written to a JSONL journal that can be read back.

2,350 lines of Python, no third-party dependency: PDF extraction, the server and the interface all live in the standard library. No `pip install`, no `requirements.txt`, no CDN in the page.

## Check it in three commands

```bash
python -m unittest discover -s essais       # 21 checks, 0.56 s
python -m archiviste valider                  # cassettes against tool signatures
python -m archiviste executer echeances       # the main scenario, end to end
```

The checks cover the four scenarios, the content of the deliverables, the refusal to leave the workspace, an exhausted budget, an unknown tool, PDF and DOCX extraction, and the API serving a deliverable as `charset=utf-8`. CI replays all of it on three Python versions, builds the image and actually starts the container to run a scenario through the API.

## What I do not know yet

- How many real documents the agent handles without a mistake: I tested on five fabricated papers, not on a real thirty-document folder.
- What a 3B or 7B model is worth on ambiguous French dates, as a measured error rate rather than an impression.
- Whether people fix a wrong date by hand or trust the report. There is no interface to correct one yet.
- What a scanned, folded, phone-photographed letter looks like to a vision model. That is the next measurement, and it needs hardware.

## Licence

MIT, see [LICENSE](LICENSE). The demo documents are fabricated; no real data appears in this repository.
