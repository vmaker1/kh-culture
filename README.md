# 경향 문화 멤버십 — 플랫폼 프로토타입

창간 80주년 기념 문화 멤버십 플랫폼의 프론트엔드 프로토타입과 공연·전시 데이터 수집기입니다.
빌드 도구 없이 정적 파일만으로 동작하며, GitHub Pages에 그대로 올라갑니다.

```
kh-culture/
├── index.html                  플랫폼 전체 (회원단 + 관리자단)
├── favicon.svg                 파비콘
├── .nojekyll                   GitHub Pages 원본 그대로 배포
├── data/
│   ├── events.json             수집된 공연·전시 (자동 갱신)
│   └── raw/                    원본 XML 보관
├── scripts/
│   └── collect.py              KOPIS + 문화포털 수집기
├── .github/workflows/
│   └── deploy.yml              매일 자동 수집 → Pages 배포
└── README.md
```

---

## 1. 깃허브에 올리기

### 방법 A — 웹 브라우저만으로 (git 설치 불필요, 권장)

1. github.com 로그인 → 우상단 **+** → **New repository**
2. Repository name에 `kh-culture` 입력
3. **Public** 선택 (Private은 Pages를 쓰려면 유료 플랜 필요)
4. **Add a README file 체크 해제** → **Create repository**
5. 다음 화면에서 **uploading an existing file** 링크 클릭
6. 내려받은 파일과 폴더를 **통째로 드래그**해서 올림
7. 아래 **Commit changes** 클릭

> **주의:** `.github` 폴더와 `.nojekyll` 파일은 이름이 점으로 시작해서
> 탐색기에서 숨김 처리될 수 있습니다. 숨김 파일 보기를 켜고 함께 올려주세요.
> 드래그가 안 되면 `Create new file`로 경로에 `.github/workflows/deploy.yml`을
> 직접 입력해 내용을 붙여넣어도 됩니다.

### 방법 B — 명령어로

```bash
cd kh-culture
git init
git add .
git commit -m "문화 멤버십 플랫폼 프로토타입"
git branch -M main
git remote add origin https://github.com/<계정>/kh-culture.git
git push -u origin main
```

---

## 2. GitHub Pages 켜기

1. 저장소 → **Settings** → 왼쪽 메뉴 **Pages**
2. Source를 **GitHub Actions** 로 변경
3. **Actions** 탭으로 이동 → 워크플로가 도는지 확인 (2~3분)
4. 완료되면 아래 주소로 접속

```
https://<계정>.github.io/kh-culture/
```

> 첫 배포에서 Actions가 자동으로 안 돌면
> **Actions → 수집 및 배포 → Run workflow** 를 눌러 수동 실행하세요.

---

## 3. API 키 등록 (실제 데이터 수집)

키를 넣기 전까지는 화면에 내장된 시드 데이터 48건이 표시됩니다.
상단 데이터 띠에 노란불이 뜨면 시드, 초록불이면 실제 수집 데이터입니다.

### 키 발급

| 수집원 | 대상 | 발급처 | 소요 |
|---|---|---|---|
| **KOPIS** | 연극·뮤지컬·클래식·무용·국악 | kopis.or.kr → OpenAPI 신청 | 1~2일 |
| **문화포털** | 전시·미술 | culture.go.kr 또는 data.go.kr | 즉시~1일 |

### 저장소에 등록

**Settings → Secrets and variables → Actions → New repository secret**

| Name | Secret |
|---|---|
| `KOPIS_KEY` | KOPIS 서비스키 |
| `CULTURE_KEY` | 문화포털 인증키 |

등록하면 매일 오전 6시(KST)에 자동 수집 후 배포됩니다.

---

## 4. 로컬에서 확인

```bash
cd kh-culture
python3 -m http.server 8000
# http://localhost:8000
```

`index.html`을 파일로 직접 열어도 동작합니다. 다만 브라우저 보안 정책상
`data/events.json`을 읽지 못해 내장 시드로 대체됩니다.

### 수집 직접 실행

```bash
export KOPIS_KEY="발급받은키"
export CULTURE_KEY="발급받은키"
python3 scripts/collect.py --days 120          # 향후 120일치
python3 scripts/collect.py --days 90 --sido 11 # 서울만
```

---

## 5. 데이터 형식

`data/events.json`

```json
{
  "updatedAt": "2026-08-13T06:00:12",
  "count": 1284,
  "events": [
    {
      "id": "kopis:PF266112",
      "source": "KOPIS",
      "genre": "연극",
      "title": "더 파더",
      "venue": "LG아트센터 서울",
      "region": "서울특별시",
      "start": "2026-08-02",
      "end": "2026-09-14",
      "poster": "http://www.kopis.or.kr/upload/...",
      "curated": false,
      "curationNote": "",
      "discount": null,
      "rating": 0.0,
      "reviewCount": 0
    }
  ]
}
```

**수집기는 사실 정보만 채웁니다.** `curated`, `curationNote`, `discount`는
관리자 편성 보드에서 직접 입력합니다. 선정 이유 없이는 노출되지 않도록 설계했습니다.

---

## 6. 실서비스 전 반드시 처리할 것

| 항목 | 내용 |
|---|---|
| **관리자 화면 분리** | 현재는 데모라 누구나 열림. `/admin` 별도 경로 + 로그인 권한 체크 필요 |
| **회원·인증** | Supabase Auth 또는 자체 SSO |
| **후기·포인트 저장** | 현재 브라우저 메모리에만 존재. DB 연동 필요 |
| **결제** | 기존 구독 결제 인프라 연동 가능 여부 확인 |
| **개인정보** | 관람 이력 수집에 대한 처리방침 개정 선행 |
| **포스터 저작권** | 이미지 직접 재배포 금지. 원본 링크 참조만 |
| **API 약관** | 수집 데이터의 상업적 이용 범위 법무 확인 |

---

## 7. 화면 구성

**회원단** — 홈(캐러셀·랭킹·오픈예정·할인·큐레이션) / 둘러보기 / 문화 광장 / 혜택 / 멤버십 가입·결제 / 내 기록

**관리자단** — 대시보드 / 편성 보드(수집함→검토중→노출중) / 수집 현황 / 회원·결제 / 제휴처 모니터링

편성 보드에서 **선정 이유를 20자 이상 쓰지 않으면 노출로 넘어가지 않습니다.**
이유가 곧 이 서비스가 파는 것이기 때문입니다.
