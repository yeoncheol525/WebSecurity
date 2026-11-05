# 설치 환경 설정

목표: **Kali VM이 요청하고, Ubuntu Server VM 안에서 웹서비스와 DB를 실행**한다.
Windows 호스트는 VMware를 실행한다. Docker Engine와 Compose는 Ubuntu VM 안에 설치한다.

## 1. VM 두 대 준비

Ubuntu Server VM과 Kali VM을 만든다. 현재 검증한 OS는 Ubuntu 24.04.5 LTS와 Kali 2026.3이다.
검증 환경의 자원 할당은 Ubuntu RAM 4GB·vCPU 2개, Kali RAM 2GB·vCPU 4개다.
OS 이미지의 패치 버전까지 반드시 같을 필요는 없지만, 재현 기준은 Ubuntu 24.04 LTS와 Kali 2026.3의
x86_64/amd64 이미지로 맞추는 것을 권장한다. 앱의 Python·Flask·PostgreSQL 등은 저장소에 고정한
컨테이너 이미지와 의존성 파일로 고정한다. Kali의 커널·그래픽 드라이버·VMware Tools 버전에 따라
마우스 등 VM 장치 동작은 달라질 수 있으므로 각자의 버전을 기록한다.
Kali는 [공식 VMware 이미지](https://www.kali.org/get-kali/#kali-virtual-machines)를 사용하고 SHA-256을 확인한다.
[공식 가져오기 절차](https://www.kali.org/docs/virtualization/import-premade-vmware/)에 따라 `.vmx`를 연다.

다운로드·설치에 사용할 NAT 연결과 두 VM이 공유할 Host-only NIC를 준비한다.
이미 사용하는 VM이면 기존 연결·파일·데이터를 보존하고 실험용 NIC를 추가한다.

## 2. Host-only 주소 결정

VMware Virtual Network Editor와 두 VM의 `ip -br address`를 확인한다.
같은 Host-only 서브넷에서 DHCP 범위·사용 중 주소를 피한 주소를 선택한다.
VMnet1의 192.168.67.0/24를 사용하는 주소 예시는 다음과 같다.

| VM | Host-only 주소 |
|---|---|
| Ubuntu | 192.168.67.20/24 |
| Kali | 192.168.67.10/24 |

VMnet1 서브넷에 맞는 주소를 사용한다.
Host-only NIC에는 외부 기본 게이트웨이를 추가하지 않는다.
Ubuntu netplan·Kali NetworkManager 설정 방식과 현재 설정은 [vm_setup.md](vm_setup.md)에 있다.

Ubuntu의 새 Host-only NIC가 `ens37`인 경우, `sudoedit /etc/netplan/90-minishop-lab.yaml`로
다음 설정을 추가한다. 기존 NAT용 파일은 유지하고, 이미 같은 이름의 파일이 있으면 내용을 먼저 확인한다.

```yaml
network:
  version: 2
  ethernets:
    ens37:
      dhcp4: false
      dhcp6: false
      link-local: []
      addresses: [192.168.67.20/24]
      optional: true
```

```sh
sudo chmod 600 /etc/netplan/90-minishop-lab.yaml
sudo netplan generate
sudo netplan apply
```

Kali의 새 Host-only NIC가 `eth1`인 경우:

```sh
sudo nmcli connection add type ethernet ifname eth1 con-name minishop-lab ipv4.method manual ipv4.addresses 192.168.67.10/24 ipv4.never-default yes ipv6.method disabled connection.autoconnect yes connection.autoconnect-priority 100
sudo nmcli connection up minishop-lab
```

NIC 이름과 IP는 각 PC에서 확인한 값으로 바꾼다. `minishop-lab` 프로필이 이미 있으면 새로 만들기 전에 기존 설정을 확인한다.

## 3. Ubuntu VM 안에서 저장소 받기

Git이 없는 새 Ubuntu에서는 먼저 `sudo apt-get update`와 `sudo apt-get install -y git`을 실행한다.
이미 GitHub에서 받은 파일이 Ubuntu에 있다면 해당 폴더로 들어가 4번부터 진행한다.
비공개 저장소이므로 GitHub 저장소 접근 권한과 인증이 필요하다.

```sh
git clone https://github.com/yeoncheol525/WebSecurity.git minishop
cd minishop
```

`docker-compose.yml`과 `scripts/`가 있는 디렉터리에서 실행한다.
Git에 `.env`나 `results/`, VM 디스크·비밀번호를 넣지 않는다.

## 4. 설치·환경 생성·정상 서비스 검증을 한 명령으로 실행

```sh
bash scripts/setup-ubuntu.sh
```

빠진 Python·Git·Docker Engine·Compose·Buildx를 설치하고 `.env`, 각 PC 전용 비밀번호,
DB·합성 데이터·컨테이너를 생성한다. Flask·Psycopg·PostgreSQL은 컨테이너 안에 설치한다.
관리자 권한이 필요하면 Ubuntu 사용자 sudo 비밀번호를 요청한다.
Docker 그룹에 사용자를 자동 추가하지 않으며 sudo 방식으로 같은 실행 안에서 계속 진행한다.
기존 Docker가 정상이면 그대로 사용하고, 충돌하는 다른 런타임은 자동 삭제하지 않는다.
공식 Docker 설치 근거는 [Docker Ubuntu 안내](https://docs.docker.com/engine/install/ubuntu/)이다.

T01~T12와 32개 검증이 통과하는지 확인한다. 검증은 MiniShop 컨테이너 4개를 재시작한다.
이후 같은 명령을 다시 실행해도 현재 비밀번호와 DB 볼륨은 유지된다.

## 5. 출력된 접속 주소 확인

설치 스크립트는 기본 인터넷 경로가 없는 전용 사설 NIC가 하나이면 그 IP를 자동 선택한다.
현재 구성에서는 다음 값이 선택된다.

```dotenv
BIND_ADDRESS=192.168.67.20
HTTP_PORT=18080
```

```sh
bash scripts/setup-ubuntu.sh --bind 192.168.67.20
curl http://192.168.67.20:18080/health/orders
```

위 명령은 NIC 후보가 여러 개이거나 `127.0.0.1`로 시작됐을 때 명시적으로 IP를 지정하는 방법이다.
일반적인 첫 실행에서는 자동 선택된 `Safe lab URL`을 그대로 사용한다.
VMware VM 생성과 Host-only NIC 추가·주소 할당은 1~2번의 준비 작업이며 서버 설치 스크립트가 바꾸지 않는다.
각 환경에 생성된 DB 비밀번호는 유지한다. 기존 볼륨이 있는 상태에서 `.env` 비밀번호만
바꿔도 DB 내부 비밀번호가 바뀌지는 않는다.

## 6. Kali VM에서 서버 접근 확인

```sh
curl -i http://192.168.67.20:18080/products
curl -i http://192.168.67.20:18080/health/orders
nc -vz -w 2 192.168.67.20 5432
```

HTTP는 200, DB 직접 접속은 실패해야 한다. Firefox에서 `http://192.168.67.20:18080/`를 연다.
`/shop`은 상품 검색, `/login`은 로그인, `/account/orders`는 본인 주문 화면이다.
Ubuntu에서 `python3 scripts/demo_credentials.py`로 user1/user2의 해당 환경 비밀번호를 확인한다.
Kali에서 한글이 사각형으로 보이면 다운로드용 NAT가 연결된 동안 다음을 한 번 실행한다.

```sh
sudo apt-get update
sudo apt-get install -y fonts-noto-cjk
```

Firefox를 다시 열면 한글 표시를 확인할 수 있다.
다운로드가 끝나면 Kali NAT 연결을 끊어 Host-only 경로로만 요청하는 상태를 만든다.
현재 Kali에서는 다음을 사용했다.

```sh
sudo nmcli connection modify 'Wired connection 1' connection.autoconnect no
sudo nmcli device disconnect eth0
ip route
```

프로필·인터페이스 이름은 해당 Kali에서 `nmcli connection show`로 확인한다.
현재 8개 자동 검사의 소스는 `scripts/verify_kali_client.py`이다.
Kali에서 대화형으로 실행하면 Ubuntu에서 확인한 테스트용 웹 비밀번호를 입력할 수 있다.

Kali에서 Ubuntu의 검증 스크립트를 받아 실행한다. `lab`은 Ubuntu 계정의 예시이며,
실제 Ubuntu 사용자 이름에 맞춰 변경한다.

```sh
scp lab@192.168.67.20:~/minishop/scripts/verify_kali_client.py ./verify_minishop.py
python3 verify_minishop.py --server 192.168.67.20
```

## 7. 평소 작업

Ubuntu에서:

```sh
cd ~/minishop
python3 scripts/demo_credentials.py         # 테스트 웹 계정 비밀번호
git pull --ff-only
bash scripts/setup-ubuntu.sh
sudo docker compose -f docker-compose.yml ps
sudo docker compose -f docker-compose.yml down  # 종료, DB 유지
bash scripts/setup-ubuntu.sh --skip-verify      # 기존 DB로 재실행
```

DB 스키마 변경은 별도 마이그레이션으로 적용한다. 최초 초기화 SQL은 기존 볼륨에 자동 재적용되지 않는다.
가상 데이터 재생성·안전 모드 복구 방법은 [README](../README.md)에 있다.
SQLite 버전의 갱신 절차는 [업데이트 안내](MIGRATION.md)를 따른다.

## Kali 마우스 포인터가 보이지 않는 경우

현재 Kali의 Xorg/modesetting 환경에서는 소프트웨어 커서를 적용해 로그인 화면에서 포인터 표시를 확인했다.
해당 증상은 Kali에서 다음 스크립트로 수정한다. 서버 계정·주소는 설치 환경에 맞게 지정한다.

```sh
scp lab@192.168.67.20:~/minishop/scripts/fix_kali_pointer.sh ./fix_kali_pointer.sh
sudo sh ./fix_kali_pointer.sh
```

작업을 저장한 뒤 Kali를 재부팅하면 적용된다. 설정 파일은
`/etc/X11/xorg.conf.d/99-minishop-software-cursor.conf`이며 현재 사용 중인 modesetting 드라이버의
`SWcursor` 옵션을 활성화한다. [드라이버 공식 옵션 설명](https://manpages.debian.org/testing/xserver-xorg-core/modesetting.4.en.html).
