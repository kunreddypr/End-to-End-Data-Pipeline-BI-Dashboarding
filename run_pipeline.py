"""
run_pipeline.py — Master orchestrator.
Runs Ingest → Transform in sequence with timing & error handling.
"""
import sys
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PIPELINE] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def run_stage(name: str, module_path: str):
    import importlib.util, os
    log.info("━" * 55)
    log.info("▶  Stage: %s", name)
    t0 = time.time()
    spec = importlib.util.spec_from_file_location(name, module_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.run()
    log.info("✔  %s finished in %.1fs", name, time.time() - t0)


def main():
    import os
    base = os.path.dirname(os.path.abspath(__file__))

    stages = [
        ("Ingest",    os.path.join(base, "pipeline", "ingest",     "generate_data.py")),
        ("Transform", os.path.join(base, "pipeline", "transform",  "clean_transform.py")),
    ]

    log.info("━" * 55)
    log.info("  END-TO-END DATA PIPELINE  —  %s", __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("━" * 55)

    t_total = time.time()
    for stage_name, stage_path in stages:
        run_stage(stage_name, stage_path)

    log.info("━" * 55)
    log.info("🎉  Pipeline complete in %.1fs", time.time() - t_total)
    log.info("   Next step → python dashboard/app.py")
    log.info("━" * 55)


if __name__ == "__main__":
    main()
