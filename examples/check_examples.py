from __future__ import annotations

import importlib.util
import ipaddress
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def check_ctis151() -> None:
    source = (ROOT / "ctis151" / "sentinel_stats.c").read_text(encoding="utf-8")
    required = ("fgets", "strtol", "errno", "score == -1", "count = 0", "total = 0")
    assert all(token in source for token in required)
    assert re.search(r"\bgets\s*\(", source) is None
    assert re.search(r"\bscanf\s*\(", source) is None


def check_ctis163() -> None:
    data = json.loads((ROOT / "ctis163" / "relation.json").read_text(encoding="utf-8"))
    domain = data["domain"]
    pairs = [tuple(pair) for pair in data["pairs"]]
    assert {left for left, _ in pairs} == set(domain)
    assert all(sum(left == value for left, _ in pairs) == 1 for value in domain)
    assert tuple(data["counterexample"]) in pairs
    matrix_pairs = {
        (row, column)
        for row, values in zip(data["matrix_rows"], data["matrix"], strict=True)
        for column, present in zip(data["matrix_columns"], values, strict=True)
        if present == 1
    }
    assert matrix_pairs == set(pairs)


def check_ctis164() -> None:
    source = (ROOT / "ctis164" / "Source.cpp").read_text(encoding="utf-8")
    assert "#include <GL/glut.h>" in source
    assert sum(step in source for step in ("STEP #1:", "STEP #2:", "STEP #3:", "STEP #4:")) == 4
    assert "glutSwapBuffers(" in source
    timer = re.search(r"onTimer\s*\([^)]*\)\s*\{(.*?)\n\}", source, re.DOTALL)
    assert timer is not None
    assert "glutTimerFunc(" in timer.group(1)
    assert "glutSpecialUpFunc(" in source
    assert "winHeight / 2 - y" in source


def check_ctis166() -> None:
    script = (ROOT / "ctis166" / "pipeline.sh").read_text(encoding="utf-8")
    assert "LC_ALL=C" in script and "sort -u" in script
    assert '< "ctis166/input.txt"' in script
    expected = (ROOT / "ctis166" / "expected.txt").read_text(encoding="utf-8")
    words = re.findall(r"[a-z0-9]+", (ROOT / "ctis166" / "input.txt").read_text(encoding="utf-8").lower())
    assert "\n".join(sorted(set(words))) + "\n" == expected


def check_ctis255_256() -> None:
    html = (ROOT / "ctis255-256" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ctis255-256" / "app.js").read_text(encoding="utf-8")
    php = (ROOT / "ctis255-256" / "page.php").read_text(encoding="utf-8")
    assert all(token in html for token in ("<main>", "aria-live=", "aria-label=", "type=\"button\""))
    assert "code.jquery.com" in html
    assert "Math.max(1" in js and "Math.min(state.pageCount" in js
    assert re.search(r"\$\((?:document|#)", js) is not None
    assert re.search(r"\bdocument\.(?:querySelector|getElementById)\b", js) is None
    assert re.search(r"\.addEventListener\s*\(", js) is None
    assert re.search(r"\.(?:innerHTML|classList)\b", js) is None
    assert re.search(r"(?i)bootstrap|tailwind|foundation|bulma", html) is None
    assert "prepare(" in php and "bindValue(':offset'" in php
    assert "PDO::PARAM_INT" in php and "htmlspecialchars(" in php


def check_ctis259() -> None:
    connection = sqlite3.connect(":memory:")
    connection.executescript((ROOT / "ctis259" / "schema.sql").read_text(encoding="utf-8"))
    statements = [part.strip() for part in (ROOT / "ctis259" / "queries.sql").read_text(encoding="utf-8").split(";") if part.strip()]
    summary = connection.execute(statements[0]).fetchall()
    filtered = connection.execute(statements[1], {"state": "done", "minimum": 5}).fetchall()
    assert summary == [("Amber", 3, 10), ("Blue", 1, 8), ("Copper", 0, 0)]
    assert filtered == [("Amber",), ("Blue",)]
    assert connection.execute("SELECT COUNT(*) FROM work_item WHERE team_id IS NULL").fetchone() == (1,)


def validate_ctis262(data: dict[str, object]) -> None:
    vlans = data["vlans"]
    vlan_ids = {item["id"] for item in vlans}
    assert len(vlan_ids) == len(vlans)
    networks = {
        item["id"]: ipaddress.ip_network(item["subnet"], strict=True)
        for item in vlans
    }
    endpoints = data["endpoints"]
    endpoint_names = {item["name"] for item in endpoints}
    assert len(endpoint_names) == len(endpoints)
    endpoint_vlans: dict[str, int] = {}
    for endpoint in endpoints:
        assert endpoint["vlan"] in vlan_ids
        interface = ipaddress.ip_interface(endpoint["address"])
        gateway = ipaddress.ip_address(endpoint["gateway"])
        network = networks[endpoint["vlan"]]
        assert interface.network == network
        assert interface.ip in network and gateway in network
        assert gateway not in {network.network_address, network.broadcast_address}
        endpoint_vlans[endpoint["name"]] = endpoint["vlan"]

    trunks = data["trunks"]
    trunk_ids = {item["id"] for item in trunks}
    assert len(trunk_ids) == len(trunks)
    assert all(
        len(set(trunk["ends"])) == 2
        and set(trunk["allowed_vlans"]) == vlan_ids
        for trunk in trunks
    )
    routes = data["routes"]
    route_ids = {item["id"] for item in routes}
    assert len(route_ids) == len(routes)
    for route in routes:
        ipaddress.ip_network(route["destination"], strict=True)
        assert len(set(route["next_hops"])) >= 2
        assert all(ipaddress.ip_address(value) for value in route["next_hops"])

    evidence = data["evidence"]
    assert {item["check"] for item in evidence} == {
        "same-vlan",
        "inter-vlan",
        "primary-link-down",
    }
    assert len({item["id"] for item in evidence}) == len(evidence)
    for item in evidence:
        assert item["source"] in endpoint_names and item["target"] in endpoint_names
        assert item["trunk"] in trunk_ids
    same_vlan = next(item for item in evidence if item["check"] == "same-vlan")
    inter_vlan = next(item for item in evidence if item["check"] == "inter-vlan")
    failover = next(item for item in evidence if item["check"] == "primary-link-down")
    assert endpoint_vlans[same_vlan["source"]] == endpoint_vlans[same_vlan["target"]]
    assert same_vlan["expected"] == "reachable"
    assert endpoint_vlans[inter_vlan["source"]] != endpoint_vlans[inter_vlan["target"]]
    assert inter_vlan["expected"] == "reachable"
    assert failover["route"] in route_ids and failover["expected"] == "reachable-via-backup"


def check_ctis262() -> None:
    validate_ctis262(
        json.loads((ROOT / "ctis262" / "topology.json").read_text(encoding="utf-8"))
    )


def check_ctis264() -> None:
    path = ROOT / "ctis264" / "merge_ranges.py"
    spec = importlib.util.spec_from_file_location("merge_ranges_example", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.self_check()


def validate_ctis359(data: dict[str, object]) -> None:
    expected_citations = {
        "NIST-BRANCH-COVERAGE": "https://csrc.nist.gov/glossary/term/decision_or_branch_coverage",
        "ISO-29119-1-2022": "https://www.iso.org/standard/81291.html",
    }
    citations = data["citations"]
    citation_urls = {item["id"]: item["url"] for item in citations}
    assert citation_urls == expected_citations
    assert all(item["title"] and item["usage"] for item in citations)
    definitions = data["definitions"]
    assert set(definitions) == {"statement_coverage", "branch_coverage"}
    for definition in definitions.values():
        assert definition["text"] and definition["citation_ids"]
        assert set(definition["citation_ids"]) <= set(expected_citations)
    assert "NIST-BRANCH-COVERAGE" in definitions["branch_coverage"]["citation_ids"]
    edges = {tuple(edge) for edge in data["control_flow"]["edges"]}
    outcomes = {case["outcome"] for case in data["cases"]}
    traversed = {edge for case in data["cases"] for edge in zip(case["path"], case["path"][1:])}
    estimate = data["estimate"]
    assert outcomes == {"true", "false"} and traversed == edges
    assert estimate["expected"] == (estimate["optimistic"] + estimate["most_likely"] + estimate["pessimistic"]) / 3
    assert estimate["assumptions"] and estimate["limitation"]


def check_ctis359() -> None:
    validate_ctis359(
        json.loads((ROOT / "ctis359" / "analysis.json").read_text(encoding="utf-8"))
    )


def validate_ctis411(data: dict[str, object]) -> None:
    requirements = {item["id"] for item in data["requirements"]}
    work = {item["id"] for item in data["work"]}
    verifications = {item["id"] for item in data["verifications"]}
    assert len(requirements) == len(data["requirements"])
    assert len(work) == len(data["work"])
    assert len(verifications) == len(data["verifications"])
    assert all(re.fullmatch(r"REQ-\d{3}", value) for value in requirements)
    assert all(re.fullmatch(r"WBS-\d{3}", value) for value in work)
    assert all(re.fullmatch(r"CHECK-\d{3}", value) for value in verifications)
    assert all(item["requirement"] in requirements for item in data["work"])
    assert all(
        item["requirement"] in requirements and item["method"] and item["acceptance"]
        for item in data["verifications"]
    )
    traceability = data["traceability"]
    assert {item["requirement"] for item in data["traceability"]} == requirements
    assert {item["work"] for item in data["traceability"]} == work
    assert {item["verification"] for item in traceability} == verifications
    work_requirements = {item["id"]: item["requirement"] for item in data["work"]}
    verification_requirements = {item["id"]: item["requirement"] for item in data["verifications"]}
    for item in traceability:
        assert item["requirement"] in requirements
        assert item["work"] in work and work_requirements[item["work"]] == item["requirement"]
        assert item["verification"] in verifications
        assert verification_requirements[item["verification"]] == item["requirement"]
    risk_fields = {
        "probability", "impact", "trigger", "mitigation", "contingency", "owner",
        "target_date",
    }
    assert all(risk_fields <= set(risk) for risk in data["risks"])
    assert all(
        re.fullmatch(r"RISK-\d{3}", risk["id"])
        and date.fromisoformat(risk["target_date"])
        for risk in data["risks"]
    )
    assert data["changes"] == ["propose", "impact-review", "approve-or-reject", "implement", "verify", "release", "archive"]


def check_ctis411() -> None:
    validate_ctis411(
        json.loads((ROOT / "ctis411" / "project.json").read_text(encoding="utf-8"))
    )


def check_ctis465() -> None:
    source = (ROOT / "ctis465" / "Program.cs").read_text(encoding="utf-8")
    project = (ROOT / "ctis465" / "CatalogSlice.csproj").read_text(encoding="utf-8")
    config = (ROOT / "ctis465" / "NuGet.Config").read_text(encoding="utf-8")
    assert all(token in source for token in ("Request(", "Response(", "CancellationToken", "ThrowIfCancellationRequested", "HandleAsync", "ArgumentException"))
    assert "secret" not in source.casefold() and "password" not in source.casefold()
    assert "<Nullable>enable</Nullable>" in project and "<clear />" in config


def validate_ctis474(data: dict[str, object]) -> None:
    criteria = {item["id"] for item in data["criteria"]}
    assert criteria == set(data["engagement"]["criteria"])
    risks = {item["id"]: item for item in data["risks"]}
    assert len(risks) == len(data["risks"])
    assert all(item["criterion"] in criteria and item["description"] for item in data["risks"])
    questions = {item["id"]: item for item in data["questions"]}
    assert len(questions) == len(data["questions"])
    for question in data["questions"]:
        assert re.fullmatch(r"Q-\d{3}", question["id"])
        assert question["criterion"] in criteria and question["risk_id"] in risks
        assert risks[question["risk_id"]]["criterion"] == question["criterion"]
        assert question["question"] and question["expected_evidence"]
    required = {"id", "question", "risk_id", "observation", "criteria", "evidence", "evidence_limitation", "risk", "severity", "recommendation", "owner", "target_date", "follow_up_method", "closure_evidence", "status"}
    assert all(set(finding) == required for finding in data["findings"])
    for finding in data["findings"]:
        assert re.fullmatch(r"FIND-\d{3}", finding["id"])
        assert finding["question"] in questions and finding["risk_id"] in risks
        question = questions[finding["question"]]
        assert finding["criteria"] == question["criterion"]
        assert finding["risk_id"] == question["risk_id"]
        date.fromisoformat(finding["target_date"])
        text_fields = (
            "observation", "evidence", "evidence_limitation", "risk", "recommendation",
            "owner", "follow_up_method", "closure_evidence", "status",
        )
        assert all(finding[field].strip() for field in text_fields)
        assert finding["evidence"] != finding["evidence_limitation"]
        assert finding["evidence"] != finding["closure_evidence"]


def check_ctis474() -> None:
    validate_ctis474(
        json.loads((ROOT / "ctis474" / "audit.json").read_text(encoding="utf-8"))
    )


CHECKS = {
    "CTIS151": check_ctis151,
    "CTIS163": check_ctis163,
    "CTIS164": check_ctis164,
    "CTIS166": check_ctis166,
    "CTIS255-256": check_ctis255_256,
    "CTIS259": check_ctis259,
    "CTIS262": check_ctis262,
    "CTIS264": check_ctis264,
    "CTIS359": check_ctis359,
    "CTIS411": check_ctis411,
    "CTIS465": check_ctis465,
    "CTIS474": check_ctis474,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in CHECKS:
        return 2
    CHECKS[sys.argv[1]]()
    print(f"EXAMPLE_OK {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
