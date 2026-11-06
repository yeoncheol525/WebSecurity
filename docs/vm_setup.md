# 실제 VM 구성과 운영

2026-11-05에 두 VM의 실제 구성을 완료하고, Ubuntu 32/32·Kali API 8/8·Firefox 화면 8/8 검증을 통과했다.
위 검증은 E1~E4 분리 이전 버전의 이력이다. 현재 설치는 서비스를 시작하는 데서 끝난다.
초기 구성은 [설치 환경 설정](TEAM_SETUP.md), 별도 개발 검사는 [development_checks.md](development_checks.md)를 따른다.

## 현재 구성

| 구분 | Ubuntu 웹서버 | Kali 공격자 |
|---|---|---|
| OS | Ubuntu Server 24.04.5 LTS | Kali 2026.3 공식 VMware 이미지 |
| Host-only IP | 192.168.67.20/24 | 192.168.67.10/24 |
| 인터페이스 | ens37 | eth1 |
| 역할 | Nginx/Flask/Gunicorn/PostgreSQL Docker | Firefox/Burp/sqlmap/HTTP 검증 |
| 소스·검증 | /home/lab/minishop | /home/kali/verify_minishop.py |
| NAT | 기존 ens33 192.168.186.128 유지 | eth0 연결 해제·자동 연결 비활성화 |

VMnet1 호스트 주소는 192.168.67.1/24, DHCP 범위는 192.168.67.128~254이다.
실험용 고정 주소 10/20은 DHCP 범위 밖이다. Ubuntu 주소에 대해 ARP 중복 검사를 수행했고,
Kali는 NetworkManager의 중복 주소 검사를 거쳐 활성화했다.
Host-only 전용 NIC에는 기본 게이트웨이·DNS를 지정하지 않았다.

Ubuntu의 기존 NAT netplan 파일과 기존 웹서비스 5000은 보존했다.
별도 `/etc/netplan/90-minishop-lab.yaml`에 ens37만 추가했다.
두 VM의 변경 전 VMX와 라이브러리 등록 파일은 Windows 소스의 `results/vm/`에 백업했다.

## VMware에서 열기

- Ubuntu: VMware 라이브러리의 `MiniShop - Ubuntu (Web)`, 작업 폴더의 `vms/ubuntu/Ubuntu 64-bit.vmx`.
- Kali: VMware 라이브러리의 `MiniShop - Kali (Attacker)`, 작업 폴더의 `vms/kali/kali-linux-2026.3-vmware-amd64.vmx`.
- 작업 폴더 최상위의 `Ubuntu - Web Server.lnk`, `Kali - Attacker.lnk`로도 열 수 있다.
- Kali 기본 OS 로그인은 공식 이미지의 `kali` / `kali`. Host-only 실험용이다.
- Ubuntu 로그인은 OS 설치 시 생성한 계정을 사용한다. 아래 명령의 `lab`은 계정 예시다.
  비밀번호는 코드·문서·Git에 저장하지 않는다.

Windows 작업 폴더는 `Downloads/minishop`이며 소스는 `project`, VM은 `vms`, 설치 이미지는 `downloads` 아래에 배치했다.
기존 Ubuntu와 새 Kali의 전체 파일을 이동했고, 이동 전후 파일 수와 크기가 일치함을 확인했다.
기존 게스트 데이터와 UUID·MAC은 유지하고 VMware 라이브러리·ISO 경로를 갱신했다.
공식 Kali 이미지 SHA-256은 다운로드 후 검증했다.

## Ubuntu 서버 명령

```sh
cd /home/lab/minishop
sudo docker compose ps
python3 scripts/demo_credentials.py
sudo docker compose down
bash scripts/setup-ubuntu.sh
```

`down`은 데이터 볼륨을 유지한다. 안전 모드 복귀는 `python3 scripts/restore_safe.py`이다.
홈페이지 주소는 `http://192.168.67.20:18080/`이다. `/products`는 기본 JSON API이다.
Windows Docker Desktop은 이 서버 실행에 사용하지 않는다.

## Kali 확인

```sh
ip -br address
ip route
curl -i http://192.168.67.20:18080/products
curl -i http://192.168.67.20:18080/health/orders
nc -vz -w 2 192.168.67.20 5432
```

HTTP는 200, PostgreSQL 직접 접속은 실패해야 한다.
Kali 기본 경로가 없고 192.168.67.0/24 경로만 있어야 현재 실험용 연결 상태와 같다.
Firefox에서 서비스 주소를 열거나 Burp의 브라우저로 같은 주소를 요청한다.
2026-11-05 환경 검증에서 Burp/sqlmap/Firefox 실행 파일의 경로를 확인했다.
현재 조건별 구현은 [실행 조건](../README.md#실행-조건), Burp GUI 사용은 [브라우저 사용](../README.md#브라우저-사용--kali-desktop--windows)을 따른다.

패키지 다운로드가 필요할 때 Kali에서 기존 NAT 프로필을 일시적으로 활성화할 수 있다.

```sh
sudo nmcli connection up 'Wired connection 1'
# 다운로드를 마친 뒤 실험 상태로 복귀:
sudo nmcli connection modify 'Wired connection 1' connection.autoconnect no
sudo nmcli device disconnect eth0
```

## 실제 증거 위치

- Ubuntu: `results/20261105T180102_KST/`, `results/latest.json`.
- Windows 복사본: `results/vm/ubuntu-results/`, `results/vm/ubuntu-validation.json`.
- Kali 출발 검사: `results/vm/kali-validation.json`.
- 최종 환경 검증 개요: [validation.md](validation.md).

기존 Windows Docker의 검증 결과는 과거 기록이다. 최종 실행 대상은 위 Ubuntu VM이며,
VM 사이 HTTP·인가·DB 포트 검증은 Kali VM에서 실제 실행했다.

## Kali 커서 표시 수정

마우스 장치와 VMware Tools는 인식됐으나 로그인 화면에서 포인터가 보이지 않는 증상에 대해,
현재 Xorg/modesetting 드라이버의 소프트웨어 커서를 활성화했다.

- 설정: `/etc/X11/xorg.conf.d/99-minishop-software-cursor.conf`, `Option "SWcursor" "true"`.
- 실행 스크립트: `scripts/fix_kali_pointer.sh`.
- 현재 로그인 화면에는 LightDM 재시작으로 적용. 활성 사용자 데스크톱은 없는 상태에서 수행했다.
- Xorg 로그에서 옵션 적용을 확인하고, 실제 VM 캡처에서 화살표 커서 표시를 확인했다.
- 로컬 증거: `results/vm/kali-pointer-before.png`, `kali-pointer-after.png`.

설정은 다음 부팅에도 Xorg가 읽는다. 되돌리려면 해당 설정 파일을 `.conf.disabled`로 이름을 바꾸고
작업을 저장한 뒤 Kali를 재부팅한다. Ubuntu 웹서비스와 실험 네트워크 설정은 변경하지 않았다.
