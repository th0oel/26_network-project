"""
client_framed.py  —  구조화된 메시지(헤더) 채팅 클라이언트  [평문 client.py의 발전형]

접속하면 먼저 입장(JOIN) 메시지로 이름을 보내고, 이후 입력한 글은 CHAT 메시지로
포장(헤더 + 내용)해 보낸다. 받은 메시지는 종류에 따라 [이름], [입장], [퇴장]으로
구분해 출력한다.
"""

import socket
import threading
import os
import protocol as P

HOST = os.environ.get("SERVER_IP", "127.0.0.1")
PORT = int(os.environ.get("CHAT_PORT", "9999"))


def receive(sock):
    """일꾼 B: 들어오는 메시지를 '한 개씩 정확히' 받아 종류별로 출력."""
    while True:
        try:
            msg = P.recv_message(sock)
        except ValueError:
            continue                 # 깨진 데이터는 건너뜀
        if msg is None:
            print("\n[알림] 서버와 연결이 끊어졌습니다.")
            break
        mtype, sender, body = msg
        if mtype == P.T_CHAT:
            line = f"[{sender}] {body}"
        elif mtype == P.T_JOIN:
            line = f"[입장] {body}"
        elif mtype == P.T_LEAVE:
            line = f"[퇴장] {body}"
        else:
            line = f"[공지] {body}"
        # \r 로 현재 입력 줄을 지우고 상대 메시지를 깔끔히 출력
        print(f"\r{line}\n나 > ", end="")


def main():
    name = input("이름 입력: ").strip() or "익명"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    print(f"[접속] 서버 {HOST}:{PORT} 에 연결됨. 메시지 입력(끝내려면 /quit)")

    # 접속하자마자 입장(JOIN) 메시지로 이름을 알린다(서버와의 약속)
    sock.sendall(P.encode(P.T_JOIN, name, ""))

    threading.Thread(target=receive, args=(sock,), daemon=True).start()

    while True:
        try:
            text = input("나 > ")
        except (EOFError, KeyboardInterrupt):
            break
        if text == "/quit":
            break
        if text:
            sock.sendall(P.encode(P.T_CHAT, name, text))

    sock.close()
    print("[클라이언트] 종료했습니다.")


if __name__ == "__main__":
    main()
