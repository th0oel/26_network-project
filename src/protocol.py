"""
protocol.py  —  구조화된 메시지(머리말 + 내용) 프레이밍

[왜 필요한가]
  평문 채팅(server.py/client.py)은 글자를 그대로 흘려보낸다.
  그런데 TCP는 '바이트 스트림'이다. 두 메시지가 한 번에 붙어서 오거나,
  한 메시지가 둘로 쪼개져 오는 일이 실제로 생긴다.
  받는 쪽은 "어디서 한 메시지가 끝나는지"를 알 방법이 없다.

[어떻게 해결하나]
  모든 메시지 앞에 고정 크기 '머리말(헤더)'을 붙인다.
  헤더에 본문 길이를 적어 두면, 받는 쪽은 '정확히 그 길이만큼' 읽어서
  메시지 경계를 되살린다. 헤더에는 길이뿐 아니라 종류와 보낸사람도 담는다.
  이것이 바로 수업에서 다룬 '캡슐화(상위 데이터에 헤더를 덧붙임)'의 축소판이고,
  HTTP, TLS 같은 실제 프로토콜이 하는 일의 출발점이다.

[와이어 포맷]  (숫자는 모두 빅엔디안)
   +--------+---------+------+---------+---------+ ....... + ....... +
   | MAGIC  | VERSION | TYPE | NAMELEN | BODYLEN |  NAME   |  BODY   |
   | 2바이트 | 1바이트  |1바이트| 1바이트  | 4바이트  | 이름길이 | 본문길이 |
   +--------+---------+------+---------+---------+ ....... + ....... +
   고정 헤더 = 9바이트, 그 뒤에 이름과 본문이 각자의 길이만큼 이어진다.
"""

import struct

MAGIC = b"NC"        # NetChat. '우리 프로토콜'임을 알리는 표식(아무 데이터나 들어오면 걸러냄)
VERSION = 1          # 프로토콜 판 번호. 나중에 형식을 바꾸면 올린다.

# ── 메시지 종류(TYPE) ──
T_CHAT = 1           # 일반 채팅
T_JOIN = 2           # 입장 알림
T_LEAVE = 3          # 퇴장 알림
T_SYS = 4            # 서버 공지

TYPE_NAME = {T_CHAT: "CHAT", T_JOIN: "JOIN", T_LEAVE: "LEAVE", T_SYS: "SYS"}

# struct 포맷:  '!' 빅엔디안,  2s=매직(2), B=버전, B=종류, B=이름길이, I=본문길이(4)
HEADER = struct.Struct("!2sBBBI")
HEADER_LEN = HEADER.size      # = 9 바이트


def encode(msg_type, sender, body):
    """종류 / 보낸사람 / 본문을 하나의 바이트 메시지(헤더 + 내용)로 포장한다."""
    name_b = sender.encode("utf-8")[:255]      # 이름 길이 필드가 1바이트(최대 255)
    body_b = body.encode("utf-8")
    header = HEADER.pack(MAGIC, VERSION, msg_type, len(name_b), len(body_b))
    return header + name_b + body_b


def _recv_exactly(sock, n):
    """소켓에서 '정확히' n 바이트를 다 모을 때까지 받는다.
       (TCP가 쪼개서 주더라도 전부 모은 뒤 돌려줌). 끊기면 None."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:                # 상대가 연결을 닫음
            return None
        buf.extend(chunk)
    return bytes(buf)


def recv_message(sock):
    """소켓에서 메시지 하나를 통째로 읽어 (종류, 보낸사람, 본문)으로 돌려준다.
       - 헤더 9바이트를 먼저 읽어 본문 길이를 알아낸 뒤, 딱 그만큼 더 읽는다.
       - 메시지가 여러 개 붙어 와도 한 번에 하나씩만 정확히 떼어낸다.
       - 연결이 끊기면 None, 우리 프로토콜이 아니면 ValueError."""
    head = _recv_exactly(sock, HEADER_LEN)
    if head is None:
        return None
    magic, version, msg_type, name_len, body_len = HEADER.unpack(head)
    if magic != MAGIC:
        raise ValueError("프로토콜이 아닌 데이터입니다(매직 불일치).")
    rest = _recv_exactly(sock, name_len + body_len)
    if rest is None:
        return None
    sender = rest[:name_len].decode("utf-8", "replace")
    body = rest[name_len:].decode("utf-8", "replace")
    return msg_type, sender, body
