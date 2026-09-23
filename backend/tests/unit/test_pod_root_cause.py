from app.kubernetes.services.investigation.correlation import (
    PodRootCauseService,
)


def test_crash_loop_root_cause() -> None:
    service = PodRootCauseService()

    result = service.analyze(
        investigation={
            "pod": {
                "status": "CrashLoopBackOff",
            },
        },
        diagnostics={
            "issues": [
                {
                    "category": "container",
                    "title": "Container is in CrashLoopBackOff",
                    "severity": "critical",
                    "evidence": [
                        "Back-off restarting failed container"
                    ],
                },
                {
                    "category": "restarts",
                    "title": "Container has restarted repeatedly",
                    "severity": "warning",
                    "evidence": [
                        "Container restarted 12 times"
                    ],
                },
                {
                    "category": "logs",
                    "title": "Fatal application error detected",
                    "severity": "critical",
                    "evidence": [
                        "Fatal: database connection failed"
                    ],
                },
            ]
        },
    )

    assert result["root_cause_count"] >= 1

    root_cause = result["root_causes"][0]

    assert (
        root_cause["title"]
        == "Application is repeatedly crashing"
    )

    assert root_cause["category"] == "application"
    assert root_cause["severity"] == "critical"
    assert root_cause["confidence"] >= 90
    assert len(root_cause["evidence"]) >= 3


def test_oom_root_cause() -> None:
    service = PodRootCauseService()

    result = service.analyze(
        investigation={
            "pod": {
                "status": "Failed",
            },
        },
        diagnostics={
            "issues": [
                {
                    "category": "resources",
                    "title": "Container terminated with OOMKilled",
                    "severity": "critical",
                    "evidence": [
                        "Reason: OOMKilled"
                    ],
                }
            ]
        },
    )

    assert result["root_cause_count"] == 1

    root_cause = result["root_causes"][0]

    assert root_cause["category"] == "resources"
    assert root_cause["severity"] == "critical"
    assert root_cause["confidence"] == 85


def test_root_causes_are_ranked() -> None:
    service = PodRootCauseService()

    result = service.analyze(
        investigation={
            "pod": {
                "status": "Running",
            },
        },
        diagnostics={
            "issues": [
                {
                    "category": "logs",
                    "title": "Application timeout detected",
                    "severity": "warning",
                    "evidence": ["request timed out after 60 seconds"],
                },
                {
                    "category": "resources",
                    "title": "Container terminated with OOMKilled",
                    "severity": "critical",
                    "evidence": ["OOMKilled"],
                },
            ]
        },
    )

    causes = result["root_causes"]

    assert len(causes) == 2
    assert causes[0]["severity"] == "critical"
    assert causes[0]["confidence"] >= causes[1]["confidence"]