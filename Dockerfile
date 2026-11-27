# Dockerfile — 채팅 노드용 이미지(도시락) 레시피  [v2: 공격·탐지·TLS 포함]
# server/client + mitm/detector + TLS(gen_cert/server_tls/client_tls) 를 담아
# GNS3 노드에서 실행할 수 있는 리눅스 컨테이너 이미지를 만든다.

# 1) 바탕: 파이썬 3.12가 미리 깔린 가벼운 리눅스(Debian slim)
FROM python:3.12-slim

# 2) 네트워크 실습 도구 + scapy 의존 도구 설치
#    - iproute2/iputils-ping/net-tools : GNS3 안에서 ip 확인·ping 테스트
#    - tcpdump/libpcap : scapy 가 패킷을 잡고 보낼 때 사용(ARP 공격·탐지)
#    - openssl : gen_cert.py 가 자체서명 인증서를 만들 때 사용
RUN apt-get update && apt-get install -y --no-install-recommends \
        iproute2 iputils-ping net-tools tcpdump libpcap0.8 openssl \
    && rm -rf /var/lib/apt/lists/*

# 3) 패킷 조작·분석 라이브러리 scapy 설치 (mitm.py / detector.py 용)
RUN pip install --no-cache-dir scapy

# 4) 파이썬 출력을 모아두지 않고 즉시 콘솔로 내보낸다
#    (없으면 GNS3 콘솔에서 print 가 늦게/안 보일 수 있음)
ENV PYTHONUNBUFFERED=1

# 5) 작업 폴더를 /app 으로 지정
WORKDIR /app

# 6) src 폴더의 모든 .py 파일을 이미지 안 /app 으로 복사
COPY src/*.py /app/

# 7) (보안) 인증서/개인키는 이미지에 굽지 않는다.
#    => 공개 Docker Hub 이미지에 개인키가 포함되지 않도록,
#       server_tls.py 가 '컨테이너 실행 시점'에 인증서를 현장 생성한다.
#       클라이언트는 인증서가 있으면 검증, 없으면 암호화만 수행한다.

# 8) 기본 실행 명령 (노드마다 GNS3에서 바꿔준다)
#    서버 노드: 그대로 / 클라이언트: "python client.py"
#    공격 노드: "python mitm.py --victim <IP> --gateway <IP>"
#    탐지 노드: "python detector.py"
#    TLS 서버 : "python server_tls.py"  /  TLS 클라: "python client_tls.py"
CMD ["python", "server.py"]
