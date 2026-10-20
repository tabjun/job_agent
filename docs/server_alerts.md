# 서버 이메일 구독 (본인 전용 선택 모듈)

PC가 꺼져 있어도 공고 요약 메일을 받기 위한 서버 경로다. 운영자 한 명이 무료 플랜으로 가볍게 쓰는 것을 전제로 한다. 확장 계획은 없다.

## 두 단계 경계

1. **운영자 로컬 알림(`job_agent/alerts/service.py`)은 계속 공개 차단이다.** 운영자 Tavily 키·SMTP 계정·`result/job_alerts/`를 쓰므로 공유 방문자, `--public-demo`, Vercel 공개 웹에서 열지 않는다(`AGENTS.md` 4절 규칙 그대로).
2. **서버 구독(`alerts/cloud.py`, `hosting/alert_handler.py`, `deploy/alerts/*.sql`, `job-alerts.html`·`subscription.*`)은 별도 키·별도 동의의 선택 모듈이다.** 로컬 `.env`의 SMTP·Tavily 값을 읽지 않고, 이력서·프로필 데이터를 받지 않는다. 공개 빌드에는 기본으로 들어가지 않으며 `python -m job_agent.hosting.build --with-subscriptions`로만 내보낸다. 로컬 UI에는 이 화면으로 가는 링크를 두지 않는다(준비되면 다시 연다).

## 구조

Supabase Auth(이메일 코드) + Postgres(구독·발송 대기열, RLS) + Cron(5분마다) → Vercel 함수 `/api/alert-worker`(POST) → Resend 또는 SMTP. 무료 플랜: Vercel Hobby(비상업·개인), Supabase Free, Tavily 무료 월 1,000 크레딧.

## 본인 전용으로 막는 장치

- `ALERT_ALLOWED_EMAILS`(쉼표 구분) 밖의 주소는 코드 요청이 조용히 무시되고(성공과 같은 응답) 코드 확인·로그인 상태 확인이 거부된다. 주소는 환경변수와 Supabase Vault에만 둔다. 코드·문서·커밋에 쓰지 않는다.
- Supabase 쪽에서도 같은 목록을 Vault 비밀 `job_alert_allowed_emails`로 확인한다(`alert_save`). 사용자 계정은 대시보드에서 본인 것 하나만 만들고 공개 가입은 끈다. 서버는 `create_user: false`로 코드를 요청한다.
- 코드 확인 시도 제한: 주소별 시간당 5회, 방문자 IP별 20회, 전체 60회(`alert_reserve_code`). 모든 방문자가 서버 IP 하나를 공유하므로 Supabase 기본 IP 제한만으로는 부족하다.
- 비밀값은 용도별로 하나씩: `ALERT_WORKER_SECRET`(Cron→worker 호출), `ALERT_UNSUBSCRIBE_SECRET`(수신 해지 링크 서명, `v1.` 버전 표기, 교체 시 `ALERT_UNSUBSCRIBE_SECRET_PREVIOUS`로 이전 링크 유지), `ALERT_RATE_PEPPER`(횟수 제한 키 해시). 셋이 같거나 32자 미만이면 준비 안 됨으로 본다.
- 준비 판정: 환경변수 플래그(`ALERT_SERVICE_ENABLED`·`ALERT_SCHEDULER_READY`)에 더해 DB의 `alert_health()`가 스키마 버전·Cron 작업 활성·Vault 비밀 이름 3개를 확인해야 저장을 받는다.
- 보관: 발송 기록은 상태와 무관하게 생성 14일 뒤 삭제한다. 보낸 URL은 구독별 최근 1,000개.
- 발송 신뢰성: 메일 서버에 넘기기 전 오류는 재시도, SMTP로 넘긴 뒤 오류는 `unknown`(중복 발송 방지), Resend는 같은 Idempotency-Key로 재전송하며 이미 `sending`이던 건은 마감 재확인으로 취소하지 않는다. worker는 검증된 조건만 검색에 쓴다.

## 할 일 (사용자 확인 후, Codex 또는 사용자)

이 목록은 원격 작업이다. 이 저장소 세션에서는 실행하지 않았다. 키·비밀값·주소는 채팅·문서·로그에 쓰지 않고 각 대시보드에 직접 입력한다.

1. Supabase 읽기 전용 확인: 확장(`pg_cron`, `pg_net`, `supabase_vault`), `alert%` 테이블·RLS·정책, 함수의 `search_path`, 서비스 전용 함수에 `anon`/`authenticated` 실행 권한이 없는지, advisor 결과.
2. Auth 설정: 공개 가입 끄기, 본인 이메일 사용자 1명 생성, 커스텀 SMTP, 이메일 템플릿에 `{{ .Token }}`(`deploy/alerts/otp-template.html`), OTP 8자리·600초, Site URL·Redirect URL은 운영 주소만.
3. Vault 비밀 3개를 대시보드에서 생성: `job_alert_server_origin`, `job_alert_worker_secret`(= `ALERT_WORKER_SECRET`), `job_alert_allowed_emails`(= `ALERT_ALLOWED_EMAILS`).
4. 마이그레이션 적용: `001_subscriptions.sql` → `002_scheduler.sql`(둘 다 다시 실행 가능). 적용 후 `select public.alert_health();`가 `ready: true`인지 확인.
5. Vercel 환경변수(Production만, Preview는 서비스 플래그 false): `ALERT_SUPABASE_URL`, `ALERT_SUPABASE_ANON_KEY`, `ALERT_SUPABASE_SERVICE_KEY`, `ALERT_WORKER_SECRET`, `ALERT_UNSUBSCRIBE_SECRET`, `ALERT_RATE_PEPPER`, `ALERT_ALLOWED_EMAILS`, `ALERT_SERVER_SEARCH_KEY`, `ALERT_PUBLIC_ORIGIN`, `ALERT_SERVER_FROM`, `ALERT_RESEND_KEY` 또는 `ALERT_SERVER_SMTP_HOST`·`_USER`·`_PASSWORD`·`_PORT`, `ALERT_SERVICE_ENABLED`, `ALERT_SCHEDULER_READY`.
6. 배포는 `--with-subscriptions` export로만, 사용자가 공개 배포 보류를 풀었을 때. 배포 뒤 인증 → 저장 → 예약 발송 → 수신 해지 종단 확인.

## 남은 위험·미구현

- lease 토큰(S16)·같은 날 수정 시 그날 메일 누락(S17)은 1인 운영에서 영향이 작아 미구현. worker 최대 300초 < lease 6분 전제.
- Supabase 새 publishable/secret 키와 `Sb-Forwarded-For` 전환(S21)은 미확인. 코드는 `apikey` + `Bearer` 헤더 방식이다.
- 실제 Postgres에서 SQL·RLS·동시성 테스트는 아직 못 했다(로컬에 psql·docker 없음). Python 쪽은 `tests/test_cloud_alerts.py`가 모의 HTTP로 검증한다.
- 비용: 메일 한 통에 Tavily 최대 15회. 평일 1회 구독 1개면 월 약 330 크레딧.
