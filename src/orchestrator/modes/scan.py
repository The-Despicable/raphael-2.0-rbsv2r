import json, os, sys
from ..scanners.pipeline import ScanPipeline
from ..proxy_guard import ProxyGuard, ProxyError


async def handle(target: str, ports: str = "1-1000",
                 nuclei_severity: str = None,
                 use_proxy: bool = True,
                 direct: bool = False) -> dict:
    # AM-4 W-12 (R3.0-P19) WELDED under Scope v0: the unbrokered scan pipeline
    # (incl. the --direct CLI bypass) is deleted as an executable path. Every
    # call proposes to the canonical Broker (fail-closed unless AUTHORIZED).
    from orchestrator.auth import enforce_broker_mediation
    enforce_broker_mediation(
        target=target,
        action_type="scan_execute",
        capability="modes.scan",
        method="handle",
        impact_estimate=8.0,
        argv=(target, ports),
        path_id="R3.0-P19",
        weld_ticket="W-12",
    )
    if direct:
        print("[scan] DIRECT MODE — scanning without proxy guard")
        os.environ["RAPHAEL_DEV_MODE"] = "1"
        pg = None
    else:
        pg = None
        if use_proxy:
            try:
                pg = ProxyGuard()
                pg.verify()
            except ProxyError as e:
                return {"error": f"Proxy verification failed: {e}",
                        "target": target, "note": "Run with use_proxy=False or --direct to skip proxy"}
        else:
            print("[scan] WARNING: Scanning without proxy. This will expose your real IP.")

    pipeline = ScanPipeline(pg)
    results = await pipeline.run(target, ports=ports, nuclei_severity=nuclei_severity)

    if pg:
        pg.abort()

    return results


if __name__ == "__main__":
    import asyncio

    if len(sys.argv) < 2:
        print("Usage: python -m orchestrator.modes.scan <target> [--ports N-M] [--nuclei-severity critical|high|medium|low]")
        sys.exit(1)

    target = sys.argv[1]
    ports = "1-1000"
    sev = None
    dev = os.getenv("RAPHAEL_DEV_MODE", "").lower() in ("1", "true", "yes")
    proxy = not dev
    if dev:
        print("[scan] WARNING: RAPHAEL_DEV_MODE=1 — scanning without proxy")

    direct = False
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--ports" and i + 1 < len(args):
            ports = args[i + 1]
        elif a == "--nuclei-severity" and i + 1 < len(args):
            sev = args[i + 1]
        elif a == "--direct":
            direct = True
            proxy = False

    result = asyncio.run(handle(target, ports=ports, nuclei_severity=sev, use_proxy=proxy, direct=direct))
    print(json.dumps(result, indent=2))
