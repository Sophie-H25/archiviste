# Image de démonstration — aucun paquet à installer, aucune dépendance.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CLASSEUR_RUNS=/data/runs \
    CLASSEUR_DONNEES=/data

WORKDIR /app

# Utilisateur non-root aligné sur l'utilisateur applicatif TrueNAS SCALE (568:568),
# pour que les fichiers écrits restent lisibles depuis l'hôte sans chmod.
RUN groupadd --gid 568 app \
 && useradd --uid 568 --gid 568 --home-dir /app --shell /usr/sbin/nologin app \
 && mkdir -p /data \
 && chown -R 568:568 /app /data

COPY --chown=568:568 . /app

USER 568:568

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"

# Le conteneur n'a besoin ni de configuration, ni de secret, ni de socket Docker.
# Un seul volume inscriptible : /data (runs, journal, procédures apprises).
CMD ["python", "-m", "classeur", "servir", "--hote", "0.0.0.0", "--port", "8080"]
