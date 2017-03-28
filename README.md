# sonaWatchd

sonaWatchd는 controller plan 및 compute plan에 대한 Monitoring 기능을 제공한다.

정보 수집에 필요한 SBAPI는 주로 SSH(key share)를 사용하고, 추가적인 방식(RESTful...)등 가능하다.
sonaWatchd의 동작에 적합한 환경은 Ubuntu, CentOS 및 Mac OSX에서 확인함

* 설치방법
ssh key 생성 및 배포를 위해서 setup tool을 사용한다.
  1. setup_tool 구성
    - setup_config.ini
    - ssh_key_setup.py
        
  2. setup_config.ini 설정
    : ssh public key 배포 대상 장비를 설정한다.
      * [BASE] section은 설정 대상을 한정한다.
      * 각 대상 section 내용
         - list: 대상 장비 IP 정보
         - auto_password: NO인 경우 직접 password를 넣어 인증하게 됨. "YES"(or etc)는 설정 파일에 있는 password를 사용함
         - username: sudoer에 포함되어 있는 OS의 account
  
  3. ssh_key_setup.py 실행함.


* Monitoring Tool 실행
  1. Server 실행/종료/재시작
     - start
         ./sonawatcher.py start
     - stop
         ./sonawatcher.py stop
     - restart
         ./sonawatcher.py restart

  2. CLI 
