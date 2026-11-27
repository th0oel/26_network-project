# 🧪 GNS3 실행 가이드 — 평문 채팅 → MITM → 탐지 → TLS

이 문서는 만들어 둔 Docker 이미지(`cbnu-netlab`)를 GNS3 가상망에 올려
**평문 취약성 → MITM 공격 → 탐지 → TLS 방어**를 순서대로 시연하고,
보고서에 넣을 **증거 스크린샷**을 확보하는 절차다.

> ⚠️ 여기의 공격(mitm.py)은 **반드시 GNS3 격리망 안에서만** 실행한다.
> 실제·공용 네트워크에서 실행하면 불법이다.

---

## 0. 준비물
- GNS3 + **GNS3 VM**(VMware/VirtualBox) — Docker 노드 실행용
- WSL2 + Docker Desktop (이미지 빌드·업로드용)
- Docker Hub 계정 (이미지 배포용, 저장소는 **public**)
- Wireshark (GNS3에 내장, 링크 우클릭 캡처)

---

## 1. 이미지 빌드 & Docker Hub 업로드

> ✅ 이미 업로드됨: **`th0oel/cbnu-netlab:v2`** (public). 아래는 재빌드/재업로드가 필요할 때 참고용.

```bash
# 프로젝트 루트에서
docker build -t cbnu-netlab:v2 .
docker tag cbnu-netlab:v2 th0oel/cbnu-netlab:v2
docker login
docker push th0oel/cbnu-netlab:v2
```

- 이미지 하나에 7개 프로그램이 다 들어 있다. **노드마다 실행 명령만 바꿔** 역할을 준다.
- **보안:** 개인키를 이미지에 굽지 않는다. TLS 서버(server_tls.py)가 **컨테이너 시작 시 인증서를 현장 생성**하고, 클라이언트는 인증서 파일이 있으면 검증, 없으면 검증 없이 암호화만 수행한다(실습). → 공개 이미지에 개인키가 없다.

---

## 2. GNS3 토폴로지

```
        [서버 .10]        [탐지 .13 = 공격 .13]
            │                     │
            └───── (가상 스위치) ──┘
            ┌──────────┴──────────┐
      [ClientA .11]          [ClientB .12]
```

- **Ethernet switch** 1개에 노드 4대를 연결한다.
- ⚠️ ARP 공격은 **같은 스위치(같은 L2 브로드캐스트 영역)** 안에서만 성립한다. 반드시 한 스위치에 모은다.

### 2.1 Docker 템플릿 등록
GNS3 → Edit → Preferences → Docker containers → New →
이미지 `th0oel/cbnu-netlab:v2` 입력(자동으로 Docker Hub에서 pull) → Adapters 1개 → Console: telnet.

### 2.2 고정 IP 할당
각 노드 우클릭 → **Edit config** → `/etc/network/interfaces` 에:

```
# 서버 노드 예시 (.10). 노드마다 address 만 바꾼다.
auto eth0
iface eth0 inet static
    address 192.168.1.10
    netmask 255.255.255.0
```

| 노드 | IP |
|---|---|
| 서버 | 192.168.1.10 |
| ClientA | 192.168.1.11 |
| ClientB | 192.168.1.12 |
| 공격자/탐지 | 192.168.1.13 |

> 노드를 start 한 뒤 콘솔에서 `ip a` 로 IP 확인, `ping 192.168.1.10` 으로 L2 연결 먼저 확인.

---

## 3. 시나리오 A — 평문 취약성 (증거 ①)

1. **서버** 콘솔: `python server.py`
2. **ClientA** 콘솔: `SERVER_IP=192.168.1.10 python client.py`
3. **ClientB** 콘솔: `SERVER_IP=192.168.1.10 python client.py`
4. ClientA에서 `안녕 비밀번호는 1234` 입력 → ClientB에 도착 확인.
5. **Wireshark**: 서버↔스위치 링크 우클릭 → **Start capture** → 필터 `tcp.port == 9999`
   → 패킷 우클릭 → **Follow → TCP Stream**.

📸 **증거 ①**: Follow TCP Stream에 채팅 원문이 그대로 보이는 화면.

---

## 4. 시나리오 B — MITM 공격 + 탐지 (증거 ②③)

1. 공격 전 **ClientA**에서 ARP 테이블 확인: `ip neigh` (게이트웨이/서버의 정상 MAC 기록).
2. **탐지 노드**(.13) 콘솔: `python detector.py`  ← 먼저 켜 둔다.
3. **공격 노드**(.13, 다른 콘솔/탭) 콘솔:
   ```bash
   sysctl -w net.ipv4.ip_forward=1        # 중계가 끊기지 않도록 선적용
   python mitm.py --victim 192.168.1.11 --gateway 192.168.1.10
   # 경고 후 'LAB' 입력해야 실행됨
   ```
4. ClientA·ClientB가 평문 채팅을 주고받으면, 공격 노드 콘솔에 `[탈취 …] <메시지>` 가 출력된다.
5. **ClientA**에서 다시 `ip neigh` → 서버/게이트웨이 MAC이 **공격자 MAC으로 바뀜** 확인.
6. **탐지 노드** 콘솔에 `[경보] ARP Spoofing 의심! …` 출력 확인.
7. 공격 종료(Ctrl+C) 시 `[복원]` 로그와 함께 ARP 테이블이 원복된다.

📸 **증거 ②**: 공격 노드의 메시지 탈취 로그 + ClientA의 `ip neigh` 변조 전/후.
📸 **증거 ③**: 탐지 노드의 ARP Spoofing 경보.

---

## 5. 시나리오 C — TLS 방어 (증거 ④)

1. **서버** 콘솔: `python server_tls.py`
2. **ClientA/B** 콘솔: `SERVER_IP=192.168.1.10 python client_tls.py`
3. 채팅이 정상 동작하는지 확인(암호화됨).
4. 시나리오 B와 **똑같이** 공격 노드에서 `python mitm.py --victim … --gateway …` 실행.
5. 공격 노드의 `[탈취]` 출력과 Wireshark `tcp.port == 9999` Follow TCP Stream을 보면
   → **암호문(알아볼 수 없는 바이트)만** 보인다.

📸 **증거 ④**: 같은 공격인데 TLS에서는 암호문만 캡처되는 화면.

> 로컬 사전 검증 결과(참고): 평문은 42바이트가 `'…비밀번호는 secret1234'`로 노출,
> TLS는 `16 03 01…`(TLS 핸드셰이크) 암호문으로 비밀번호 미검출.

---

## 6. 트러블슈팅

| 증상 | 원인 / 조치 |
|---|---|
| MITM 중 피해자 인터넷/통신 끊김 | `sysctl -w net.ipv4.ip_forward=1` 선적용(중계 유지) |
| 탈취가 안 됨 | 공격자·피해자가 **같은 스위치**인지 확인(ARP는 라우터 못 넘음) |
| ARP 패킷이 스위치에서 안 보임 | GNS3 링크/인터페이스·브리지 설정 점검, `ping`으로 L2 선확인 |
| TLS 연결 실패 | 서버(server_tls.py)가 시작하며 인증서를 만든다. openssl 포함된 이미지인지, 서버가 먼저 떠 있는지 확인. 클라이언트는 인증서 없이도 암호화 접속됨 |
| 포트 막힘 | 노드 방화벽/iptables에서 9999 허용(인바운드 규칙은 포트로 통과 결정) |
| GNS3 콘솔에 print 안 뜸 | 이미지에 `PYTHONUNBUFFERED=1` 적용됨 — 재빌드 확인 |

---

## 7. 보고서용 증거 체크리스트
- [ ] ① 평문 Follow TCP Stream 원문 노출
- [ ] ② MITM 탈취 로그 + `ip neigh` 변조 전/후
- [ ] ③ detector ARP Spoofing 경보
- [ ] ④ TLS 재공격 시 암호문만 캡처
- [ ] 토폴로지 캡처(노드 4 + 스위치)
- [ ] 각 노드 IP(`ip a`) 캡처
