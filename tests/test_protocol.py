import pytest

from protocol import ErrorCode, Kind, ProtocolError, decode, encode, error_response, push, request, response


def test_request_roundtrip():
    env = request("hierarchy.traverse", {"pc_id": 7}, auth={"client_id": "abc"})
    out = decode(encode(env))
    assert out.kind is Kind.REQUEST
    assert out.id == env.id
    assert out.type == "hierarchy.traverse"
    assert out.payload == {"pc_id": 7}
    assert out.auth == {"client_id": "abc"}


def test_response_and_error_shapes():
    ok = decode(encode(response("r1", {"x": 1})))
    assert ok.ok is True and ok.result == {"x": 1} and ok.id == "r1"
    err = decode(encode(error_response("r2", ErrorCode.CONFLICT, "occupied")))
    assert err.ok is False and err.error == {"code": "conflict", "message": "occupied"}


def test_push_has_no_auth_field():
    d = push("session.ended", {"session_id": 3}).to_dict()
    assert "auth" not in d and d["kind"] == "push"


def test_one_line_framing():
    assert encode(push("x")).count(b"\n") == 1
    assert decode(encode(push("x", {"s": "a\nb"}))).payload == {"s": "a\nb"}


@pytest.mark.parametrize("raw", [b"not json\n", b"[1,2]\n", b'{"kind":"nope"}\n',
                                 b'{"kind":"request","type":"a"}\n', b'{"kind":"request","id":"1"}\n'])
def test_bad_messages_raise(raw):
    with pytest.raises(ProtocolError) as exc:
        decode(raw)
    assert exc.value.code is ErrorCode.BAD_MESSAGE
