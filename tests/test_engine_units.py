"""Unit tests for the pure logic already present in the scaffold."""

from engine.control.custom_actions import validate
from engine.flow.flows import has_cycle
from engine.flow.sync import modified_name
from engine.hierarchy.display_names import composed_fallback
from engine.hierarchy.traversal import can_traverse_to, relationship
from engine.resource.assistance import next_turn
from engine.resource.resource import allowed_tags_for, tag_allowed_on
from engine.task.verification import VerificationItem


def test_relationship_and_depth():
    assert relationship("super_user", "admin") == "vertical"
    assert relationship("admin", "admin") == "horizontal"
    assert relationship("worker", "admin") == "inferior"
    assert can_traverse_to("super_user", "admin_workstation")
    assert can_traverse_to("admin", "client_pc")
    assert not can_traverse_to("admin", "admin_workstation")
    assert not can_traverse_to("worker", "client_pc")


def test_cycle_prevention():
    edges = [("A", "B"), ("B", "C")]
    assert has_cycle(edges, ("C", "A"))
    assert not has_cycle(edges, ("C", "D"))
    assert has_cycle([], ("A", "A"))


def test_modified_name():
    assert modified_name("report.xlsx") == "report-modified.xlsx"
    assert modified_name("C:/x/notes").endswith("notes-modified")


def test_access_tags():
    assert tag_allowed_on("admin", "super_user_workstation", None)
    assert not tag_allowed_on("admin", "admin_workstation", 1)
    assert tag_allowed_on("restricted", "admin_workstation", 1)
    assert not tag_allowed_on("restricted", "client_pc", 1)
    assert tag_allowed_on("worker-dept-3", "client_pc", 3)
    assert not tag_allowed_on("worker-dept-3", "client_pc", 4)
    assert allowed_tags_for("worker", 2) == ["common", "worker-dept-2"]
    assert "admin" in allowed_tags_for("super_user", None)


def test_message_channel_turns():
    sup, sub = 10, 20
    assert next_turn(None, sup, sub) == sub
    assert next_turn(sub, sup, sub) == sup
    assert next_turn(sup, sup, sub) == sub


def test_verification_item_validation():
    assert VerificationItem("file", "create", "report.docx").validate() == []
    assert VerificationItem("file", "used", "x").validate()
    assert VerificationItem("program", "used_with_file", "excel").validate()
    assert VerificationItem("program", "used_with_file", "excel", linked_item_index=0).validate() == []


def test_composed_fallback_is_derived():
    assert composed_fallback(7, "PC-07", "Finance") == "PC-07-Finance-7"
    assert composed_fallback(7, None, None) == "account-7"


def test_custom_action_validation():
    assert validate("python", "import os, json\nprint(os.name)").ok
    r = validate("python", "import requests")
    assert not r.ok and "requests" in r.problems[0]
    assert not validate("python", "def (:").ok
    assert validate("powershell", "Get-Process | Select-Object -First 5").ok
    assert not validate("powershell", "Import-Module Az.Accounts").ok
