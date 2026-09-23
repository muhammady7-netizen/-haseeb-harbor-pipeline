### FINDING 28 — Dockerfile USER directive contradicts between platform PreQC and local QC
**Platform:** gen-g806 v10 PreQC QC1-2
**What:** Platform says "Keep the image as root (remove the final USER line)" when `USER app` is present. Local QC judge says "Add a non-root USER directive" when `USER app` is absent. These are CONTRADICTORY requirements.
**Lesson:** ALWAYS follow the platform PreQC guidance, not the local QC judge. If platform says remove USER, remove it. If platform says add USER, add it. The platform PreQC is the authority.
**Detection:** Check platform PreQC result. If it says "The Dockerfile ends as a non-root user" -> remove `USER app`. If it says "Dockerfile runs as root" -> add `USER app`.
**Rule:** Never add `USER app` unless the platform PreQC explicitly asks for it. Default: keep Dockerfile as root.
