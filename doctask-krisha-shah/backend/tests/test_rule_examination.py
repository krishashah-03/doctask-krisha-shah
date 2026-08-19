import uuid

from app.db.models import Document, Fact, Finding, Rule, Run, RunEvent
from app.graph.nodes.examine_rules import examine_rules


def _make_document(db_session, pile, name="doc.txt"):
    document = Document(
        pile_id=pile.id,
        doc_type="contract",
        storage_path=f"piles/{pile.id}/dummy-{uuid.uuid4().hex}.txt",
        content_hash=f"test-{uuid.uuid4().hex}",
        original_filename=name,
        mime_type="text/plain",
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


def _make_fact(db_session, pile, document, fact_key, fact_value, char_start=10, char_end=20):
    fact = Fact(
        pile_id=pile.id,
        document_id=document.id,
        fact_key=fact_key,
        fact_value=fact_value,
        char_start=char_start,
        char_end=char_end,
        confidence=0.9,
        operation_id=f"test:{uuid.uuid4().hex}",
    )
    db_session.add(fact)
    db_session.commit()
    db_session.refresh(fact)
    return fact


def _make_rule(db_session, pile, rule_key, rule_spec):
    rule = Rule(pile_id=pile.id, rule_key=rule_key, description=f"test rule {rule_key}", rule_spec=rule_spec)
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


def _make_run(db_session, pile):
    run = Run(pile_id=pile.id, current_stage="examine_rules")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def test_rule_violation_produces_finding_with_correct_span(db_session, test_pile):
    document = _make_document(db_session, test_pile)
    fact = _make_fact(db_session, test_pile, document, "payment_term_days", "45", char_start=100, char_end=110)
    rule = _make_rule(db_session, test_pile, "payment_term_max_days", {"max_days": 30})
    run = _make_run(db_session, test_pile)

    outcome = examine_rules(pile_id=test_pile.id, run_id=run.id, db=db_session)

    assert len(outcome.findings) == 1
    finding = outcome.findings[0]
    assert finding.rule_id == rule.id
    assert finding.document_id == document.id
    assert finding.char_start == fact.char_start
    assert finding.char_end == fact.char_end
    assert finding.status == "pending"


def test_rule_with_no_violations_produces_zero_findings_and_logs_event(db_session, test_pile):
    document = _make_document(db_session, test_pile)
    _make_fact(db_session, test_pile, document, "payment_term_days", "45")
    _make_fact(db_session, test_pile, document, "payment_term_days", "60")
    rule = _make_rule(db_session, test_pile, "payment_term_max_days_lenient", {"max_days": 100})
    run = _make_run(db_session, test_pile)

    outcome = examine_rules(pile_id=test_pile.id, run_id=run.id, db=db_session)

    assert outcome.findings == []

    event = (
        db_session.query(RunEvent)
        .filter(RunEvent.run_id == run.id, RunEvent.stage_name == "examine_rules")
        .first()
    )
    assert event is not None
    assert event.payload["rule_id"] == str(rule.id)
    assert event.payload["status"] == "no_findings"


def test_rerunning_examine_rules_does_not_duplicate_findings(db_session, test_pile):
    document = _make_document(db_session, test_pile)
    _make_fact(db_session, test_pile, document, "payment_term_days", "45")
    _make_rule(db_session, test_pile, "payment_term_max_days", {"max_days": 30})
    run = _make_run(db_session, test_pile)

    first = examine_rules(pile_id=test_pile.id, run_id=run.id, db=db_session)
    assert len(first.findings) == 1

    second = examine_rules(pile_id=test_pile.id, run_id=run.id, db=db_session)
    assert second.findings == []  # rule already processed for this run — skipped, not re-run

    total = db_session.query(Finding).filter(Finding.pile_id == test_pile.id).count()
    assert total == 1
