"""`python -m engine setup` opens the Engine's port in the host firewall that is running, and leaves any other alone."""

from __future__ import annotations

from engine.setup import firewall_steps


def _tools(*names):
    return lambda n: f"/usr/sbin/{n}" if n in names else None


def _runner(answers):
    calls = []

    def run(argv):
        calls.append(argv)
        return answers.get(tuple(argv), (0, ""))

    run.calls = calls
    return run


def test_ufw_is_opened_as_root_asked_for_otherwise_and_left_alone_when_open_or_off():
    active = {("ufw", "status"): (0, "Status: active\n22/tcp ALLOW Anywhere")}
    run = _runner(active)
    assert firewall_steps(7400, _tools("ufw"), run, True) == ["firewall (ufw): opened 7400/tcp"] and ["ufw", "allow", "7400/tcp"] in run.calls
    run = _runner(active)
    assert "sudo ufw allow 7400/tcp" in firewall_steps(7400, _tools("ufw"), run, False)[0] and ["ufw", "allow", "7400/tcp"] not in run.calls
    already = _runner({("ufw", "status"): (0, "Status: active\n7400/tcp ALLOW Anywhere")})
    assert firewall_steps(7400, _tools("ufw"), already, True) == ["firewall (ufw): 7400/tcp is already open"]
    off = _runner({("ufw", "status"): (0, "Status: inactive")})
    assert "nothing was changed" in firewall_steps(7400, _tools("ufw"), off, True)[0] and ["ufw", "allow", "7400/tcp"] not in off.calls


def test_firewalld_is_opened_permanently_and_reloaded_and_nothing_else_is_touched():
    state = {("firewall-cmd", "--state"): (0, "running\n"), ("firewall-cmd", "--query-port", "7400/tcp"): (1, "no")}
    run = _runner(state)
    assert firewall_steps(7400, _tools("firewall-cmd"), run, True) == ["firewall (firewalld): opened 7400/tcp"]
    assert ["firewall-cmd", "--permanent", "--add-port", "7400/tcp"] in run.calls and ["firewall-cmd", "--reload"] in run.calls
    assert "sudo firewall-cmd --permanent --add-port=7400/tcp" in firewall_steps(7400, _tools("firewall-cmd"), _runner(state), False)[0]
    assert "nothing was changed" in firewall_steps(7400, _tools(), _runner({}), True)[0]           # nftables / iptables only: left alone, said so
