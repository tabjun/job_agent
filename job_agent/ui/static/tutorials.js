"use strict";
(() => {
  const steps = {
    profile: [
      ["profile-template.jpg", "Word 빈 양식 받기", "파일 형식을 Word로 선택하고 빈 양식을 다운로드합니다. 작성한 표준 파일은 업로드할 수 있습니다."],
      ["profile-skills.jpg", "보유 기술을 항목별로 작성", "추가 버튼으로 기술을 등록하고 기술명·분류·사용 경험을 따로 입력합니다. 경력·자격증·프로젝트도 같은 방식입니다."],
      ["profile-review.jpg", "원문과 대조하고 검수", "사실과 일치하는 항목을 검수하고 공통 이력서에 반영합니다. 수정하면 해당 검수는 해제됩니다."]
    ],
    search: [
      ["search-input.jpg", "검색 조건과 공고 입력", "Python·SQL 키워드와 가상 공고를 입력한 화면입니다. 공고 탐색은 이력서 정리와 별도로 사용할 수 있습니다."],
      ["search-result.jpg", "실행 결과 확인", "실제로 실행한 가상 공고 비교 결과입니다. 실제 채용정보·기업 분석·합격 가능성을 검증한 자료가 아닙니다."]
    ],
    resume: [
      ["resume-input.jpg", "지원 직무와 키워드 입력", "검수된 공통 이력서에 가상 JD와 SQL 키워드를 입력합니다. 공통 원본은 유지됩니다."],
      ["resume-result.jpg", "정리 결과 검토 후 전환", "실제 정리 결과를 읽고 정리 결과로 플랫폼 전환을 누릅니다. 이 예시는 관련 항목 재배치이며 새 경력을 생성하지 않습니다."]
    ],
    prepare: [
      ["prepare-sites.jpg", "원하는 채용 플랫폼 선택", "검수한 정리 결과 또는 공통 이력서를 선택하고 캐치·잡코리아·사람인·원티드·인크루트 중 필요한 곳을 체크합니다."]
    ],
    platforms: [
      ["connection-transfer.jpg", "본인 PC 연결 창 열기", "공개 웹에서는 본인 PC 연결 도구를 실행한 뒤 출력된 주소를 입력합니다. 사진의 임시 포트는 예시이며 그대로 복사하지 마세요."],
      ["connection-approve.jpg", "로컬 창에서 가져오기 승인", "요청한 웹사이트와 전달할 이력서를 확인합니다. 비밀번호·OTP·쿠키는 웹으로 전달하지 않습니다."]
    ],
    sync: [
      ["sync-connected.jpg", "선택한 플랫폼의 연결 상태 확인", "로컬 테스트 양식에서 두 플랫폼의 연결 흐름을 실행한 화면입니다. 실제 사용 시 전용 브라우저에서 로그인·2차 인증 후 기존 이력서 편집 화면을 엽니다."],
      ["sync-review.jpg", "입력 항목과 저장 버튼 검수", "소개만 연결하고 이름·보유 기술은 업데이트하지 않도록 둔 테스트입니다. 전송할 값과 저장 동작을 확인하고 동의한 뒤 입력·저장을 실행합니다."],
      ["sync-saved.jpg", "저장 후 재접속 확인", "로컬 테스트 양식에 실제로 입력·저장하고 재접속해 선택한 소개 값이 유지되는지 확인했습니다. 실제 채용사이트 계정의 저장 성공이나 전체 이력서 완성을 인증하는 사진이 아닙니다."]
    ]
  };
  const dialog = document.createElement("dialog");
  dialog.id = "tutorial-dialog";
  dialog.setAttribute("aria-label", "사용 예시 화면 확대");
  const close = document.createElement("button");
  close.type = "button"; close.className = "tutorial-close";
  close.setAttribute("aria-label", "확대 화면 닫기"); close.title = "닫기";
  close.innerHTML = '<i data-lucide="x"></i>';
  const large = document.createElement("img");
  const caption = document.createElement("p");
  dialog.append(close, large, caption); document.body.append(dialog);
  close.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", event => { if (event.target === dialog) dialog.close(); });
  for (const [topic, images] of Object.entries(steps)) {
    const panel = document.getElementById(`example-${topic}`);
    if (!panel) continue;
    const section = document.createElement("section"); section.className = "tutorial-section";
    const heading = document.createElement("h3"); heading.textContent = "실제 실행 화면";
    const note = document.createElement("p"); note.className = "tutorial-note";
    note.textContent = "Codex 내 브라우저에서 가상 자료로 직접 수행한 화면입니다. 이미지에 개인정보·로그인 정보는 포함하지 않았습니다. 화면을 누르면 확대됩니다.";
    const gallery = document.createElement("div"); gallery.className = "tutorial-gallery";
    images.forEach(([file, title, description], index) => {
      const figure = document.createElement("figure");
      const button = document.createElement("button"); button.type = "button";
      button.className = "tutorial-shot"; button.title = `${title} 확대`;
      button.setAttribute("aria-label", `${title} 화면 확대`);
      const img = document.createElement("img"); img.src = `/tutorials/${file}`;
      img.alt = `${index + 1}단계 ${title} 실제 실행 화면`; img.loading = "lazy";
      img.width = 646; img.height = 633;
      button.append(img);
      button.addEventListener("click", () => {
        large.src = img.src; large.alt = img.alt; caption.textContent = description; dialog.showModal();
      });
      const text = document.createElement("figcaption");
      const label = document.createElement("strong"); label.textContent = `${index + 1}. ${title}`;
      const detail = document.createElement("p"); detail.textContent = description;
      text.append(label, detail); figure.append(button, text); gallery.append(figure);
    });
    section.append(heading, note, gallery); panel.prepend(section);
  }
  // The first-use overview is documentation, not a separate stored result.
  const guide = document.querySelector("#guide-view");
  if (guide) {
    const figure = document.createElement("figure"); figure.className = "tutorial-overview";
    const img = document.createElement("img"); img.src = "/tutorials/guide-overview.jpg";
    img.alt = "처음 사용하기에서 전체 서비스 흐름을 확인하는 실제 화면"; img.loading = "lazy";
    const caption = document.createElement("figcaption"); caption.textContent = "전체 흐름을 확인한 뒤 각 서비스의 사용 예시에서 단계별 실행 화면을 볼 수 있습니다.";
    figure.append(img, caption); guide.append(figure);
  }
  if (window.lucide) window.lucide.createIcons();
})();
