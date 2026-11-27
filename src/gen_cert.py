"""
gen_cert.py  —  5단계 TLS용 '자체 서명 인증서' 생성 헬퍼

[목표] 서버가 자기 자신을 증명할 신분증(인증서)과 그 열쇠(개인키)를 만든다.
       공인기관(CA) 대신 내가 직접 서명한다 = '자체 서명(self-signed)'.
       실습용이라 이렇게 하고, 실제 서비스는 공인 CA의 인증서를 쓴다.

[수업 연결] 인증서는 "이 서버가 진짜다"를 증명하는 신분증(용어정리.md).
            TLS가 상대 확인(인증)에 이 인증서를 사용한다.
"""

import subprocess
import os

# 인증서(server.crt)와 개인키(server.key)를 server.py 들이 있는 폴더에 만든다.
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = os.path.join(HERE, "server.key")   # 개인키 (남에게 주면 안 됨)
CRT = os.path.join(HERE, "server.crt")   # 인증서 (클라이언트에게 배포)

# OpenSSL 한 방으로 키 + 자체서명 인증서를 동시에 생성한다.
#  -x509      : 인증서 요청(CSR)이 아니라 바로 자체서명 인증서를 만든다
#  -newkey rsa:2048 : 2048비트 RSA 키를 새로 만든다
#  -nodes     : 개인키에 암호를 걸지 않는다 (실습 편의, 서버가 자동 기동 가능)
#  -days 365  : 1년간 유효
#  -subj      : 질문 없이 주체 정보를 바로 넣는다 (CN=localhost)
cmd = [
    "openssl", "req", "-x509", "-newkey", "rsa:2048",
    "-keyout", KEY, "-out", CRT,
    "-days", "365", "-nodes",
    "-subj", "/C=KR/O=CBNU-NetLab/CN=localhost",
]


def ensure(verbose=True):
    """인증서가 없으면 생성한다. (이미지에 키를 굽지 않고 '실행 시' 만들기 위함)
       => 공개 Docker Hub 이미지에 개인키가 포함되지 않는다."""
    if os.path.exists(CRT) and os.path.exists(KEY):
        if verbose:
            print(f"[인증서] 기존 인증서 사용: {CRT}")
        return
    if verbose:
        print("[인증서] 자체 서명 인증서를 생성합니다...")
    subprocess.run(cmd, check=True)
    if verbose:
        print(f"[인증서] 개인키 : {KEY}")
        print(f"[인증서] 인증서 : {CRT}")


def main():
    ensure()
    print("[인증서] 완료. server_tls.py 가 이 파일들을 사용합니다.")


if __name__ == "__main__":
    main()
