# 채용 사이트 이력서 화면 조사

2026-10-06 사용자 로그인 세션의 실제 DOM에서 확인한 내용이다. 아래 selector는 확인 당시 화면의 예시이며, 매 실행 전 현재 DOM에서 유일성과 편집 가능 여부를 다시 확인한다. 개인 이름, 연락처, 이력서 번호, 원본 내용은 이 문서에 기록하지 않는다.

| 사이트 | 목록 화면 | 편집 흐름 | 저장 UI |
| --- | --- | --- | --- |
| 캐치 | `/Member/ResumeList` | 기존 이력서 제목 → `/Member/Resume/<id>`, 같은 탭 | `저장하기` |
| 잡코리아 | `/User/ResumeMng` | `수정` → `/User/Resume/Edit?RNo=<id>`, 새 창 | `이력서저장` |
| 사람인 | `/zf_user/resume/resume-manage` | `수정하기` → 섹션별 `수정하기`, 인라인 편집 폼 | 섹션 `저장`, 최종 `작성완료` |
| 원티드 | `/cv/list` | `계속 작성하기` → `/cv/<id>`, 같은 탭 | `작성 완료`; blur 자동저장 및 새로고침 유지 확인 |
| 인크루트 | `/resume/resumelist.asp` | 2단계 인증 후 `이력서 완성하기` → `/resume/resume.asp?rsm=<id>` | 섹션 `이 부분만 저장`, `모두 저장`, `작성 완료` |

## 캐치

| 항목 | 확인된 selector | 비고 |
| --- | --- | --- |
| 이력서 제목 | `#title` | 라벨은 RESUME, placeholder에 제목 설명 |
| 이름 | `#int_1` | 기본정보 |
| 연락처 | `#int_3` | 사용자가 확인한 값만 입력 |
| 이메일 | `#int_4` | 사용자가 확인한 값만 입력 |
| 회사명 | `#int_150` | 현재 경력 항목의 예시 |
| 부서 | `#int_170` | maxlength 24 |
| 담당업무 및 성과 | `textarea#int_21` | 최소 500자 이상 작성 안내, 추가 경력에서는 재수집 필요 |
| 스킬 검색 | `#skill_sch` | 입력만으로 태그 추가가 완료되는지는 미검증 |

## 잡코리아

- 제목: `#UserResume_M_Resume_Title`.
- 경력 회사명: `input[id^="Career_C_Name_"]`, 담당업무: `textarea[id^="Career_Prfm_Prt_"]`. 반복 항목에서는 prefix가 여러 개를 찾으므로 현재 항목으로 범위를 좁혀야 한다.
- 대학/대학원 학력의 전공 입력에서 중복 `id`를 확인했다. `#id`만으로 유일하다고 가정하지 않는다.
- 수상 입력의 `id`에는 생성 시점 값이 포함됐다. 이전 세션의 selector를 그대로 쓰기 전 재검증한다.
- 직무·스킬·근무조건은 버튼/선택 UI다. 일반 `fill()` 실행기로 자동 선택하지 않는다.

## 사람인

- 제목: `input#title`.
- 경력 수정 진입: `#career` 안의 `수정하기` 버튼. 목록 안내 팝업은 먼저 닫아야 할 수 있다.
- 경력 폼: `input[name="career_company_nm[]"]`, `input[name="career_dept_nm[]"]`, `textarea[name="career_contents[]"]`.
- 현재 인증 경력의 회사명·입사년월·재직년월은 readonly, 재직상태 checkbox는 disabled였다. 인증값을 덮어쓰지 않는다.
- 부서는 maxlength 25. 생성된 `id`에 시점 값이 있어 `name`과 섹션 범위를 함께 사용한다.
- 섹션의 저장과 최종 작성완료는 별도다. 열람 공개 설정도 별도이며 입력 실행기는 이를 조작하지 않는다.

## 원티드

- 이름·연락처·이메일: `input[name="name"]`, `input[name="mobile"]`, `input[name="email"]`. maxlength는 각각 50/20/100.
- 간단 소개 textarea: maxlength 5000, 소개 안내 placeholder로 식별 가능.
- 경력의 `job_role`, `business_title`, `title`은 다른 반복 항목에도 존재한다. name만으로 매칭하지 않는다.
- 경력 성과 설명 textarea: maxlength 5000. 학력 연구내용 textarea: maxlength 1000.
- 회사/학교/전공은 combobox, 기간은 날짜 버튼이다. 일반 텍스트 입력과 다른 처리 필요.
- blur 후 자동저장 및 새로고침 유지 확인(2026-10-06/07). 회사·전공 combobox에는 직접 입력 선택지가 있다. 날짜는 year → month → 확인, 종료일은 재직중 checkbox로 설정한다. 자동저장 시 재렌더링되므로 각 선택 후 현재 DOM을 확인한다.

## 인크루트 (2026-10-07)

- 이력서 제목: `#Resume_Title`, maxlength 50.
- 기존 경력 상세: `textarea#Work_Contents`, maxlength 속성 없음. 부서: `input[name="Work_Dept"]`, maxlength 25. 반복 항목에서는 현재 경력 범위로 제한한다.
- 대학원 입학월: 현재 항목 `#Ent_Mm1`. 수업/연구내용은 placeholder `수업명을 입력하세요`, `수업내용을 자세히 입력하세요`로 식별하며 항목 범위/유일성을 확인한다.
- 자기소개서는 STEP02로 별도 이동한다. 편집 중인 STEP01 내용을 잃지 않도록 최종 저장 없이 이동하지 않았다.
- 추천 스킬 팝업은 `다음에 추천받기`로 닫고, 사용자 기술을 임의 추가하지 않았다.

## 실행 범위

`job_agent/browser/mapper.py`로 현재 편집 화면을 수집하고, `job_agent/browser/connector.py`로 후보를 만든다. 검수한 mapping 항목에만 `"approved": true`를 추가한다. `job_agent/browser/filler.py`는 패키지 원문 값을 읽고 selector 유일성·편집 가능 여부·길이·중복 대상·iframe 위치를 검사한다. 기본은 검증만이며 `--apply`와 터미널의 `APPLY` 입력이 있어야 실제 값을 채운다. 저장/제출 클릭, 반복 항목 생성, custom combobox 선택은 이 실행기의 범위 밖이다.
