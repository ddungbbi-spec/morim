let gameState = null;
let pending = null;
let forgeBusy = false;
let craftingBusy = false;
let utilityMode = null;
let equipmentMember = 0;
let craftingFamily = "sword";
let dismantleRarity = "all";
let dismantleFamily = "all";
let dismantleUnenhancedOnly = false;
let dismantleIncompatibleOnly = false;
let dismantleSelection = new Set();
let shopIndex = null;
let installPrompt = null;
let phaseAnnouncementTimer = null;
let soundEnabled = localStorage.getItem("undefined-legend-sound") !== "off";
let autoBattleEnabled = false;
let autoBattleTimer = null;
let autoRequestInFlight = false;
let battleSpeed = Number(localStorage.getItem("undefined-legend-battle-speed") || "1");
if (![1, 2, 3].includes(battleSpeed)) battleSpeed = 1;
const AUTO_BATTLE_DELAYS = {1: 900, 2: 450, 3: 300};
const SAVE_BACKUP_KEY = "undefined-legend-save-backups-v1";

const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
}[char]));

async function request(path, body = null) {
  const options = body ? {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body)
  } : {};
  const response = await fetch(path, options);
  const result = await response.json();
  const previousPhase = gameState?.phase;
  const previousTransitionId = gameState?.phase_transition_id;
  gameState = result.state || gameState;
  if (result.ok && result.backup && result.slot) {
    storeBrowserBackup(result.slot, result.backup);
  }
  if (!result.ok) {
    showError(result.error || "요청을 처리하지 못했습니다.");
    playTone("error");
  } else {
    showError("");
    playResponseTone(path, previousPhase, gameState?.phase);
  }
  pending = null;
  render();
  if (result.ok && previousTransitionId != null &&
      gameState?.phase_transition_id > previousTransitionId) {
    announceBossPhase(gameState.phase_transition_message);
  }
  return result;
}

function announceBossPhase(message) {
  const announcement = $("#phaseAnnouncement");
  if (!message) return;
  clearTimeout(phaseAnnouncementTimer);
  announcement.textContent = message;
  announcement.classList.remove("hidden");
  const stage = $(".stage");
  stage.classList.remove("phase-flash");
  void stage.offsetWidth;
  stage.classList.add("phase-flash");
  phaseAnnouncementTimer = setTimeout(() => {
    announcement.classList.add("hidden");
    stage.classList.remove("phase-flash");
  }, 2400);
}

function browserBackups() {
  try {
    const value = JSON.parse(localStorage.getItem(SAVE_BACKUP_KEY) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch (_error) {
    return {};
  }
}

function storeBrowserBackup(slot, backup) {
  const saves = browserBackups();
  saves[String(slot)] = backup;
  localStorage.setItem(SAVE_BACKUP_KEY, JSON.stringify(saves));
}

async function restoreBrowserBackups() {
  const saves = browserBackups();
  for (const [slot, backup] of Object.entries(saves)) {
    const serverSlot = gameState?.save_slots?.find((item) => String(item.slot) === slot);
    if (!serverSlot || serverSlot.exists) continue;
    try {
      const response = await fetch("/api/save", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({operation: "restore", slot: Number(slot), backup})
      });
      const result = await response.json();
      if (result.ok && result.state) gameState = result.state;
    } catch (_error) {
      // 서버 저장소가 일시적으로 준비되지 않아도 게임 시작은 계속 허용한다.
    }
  }
  render();
}

function percent(value, maximum) {
  return maximum > 0 ? Math.max(0, Math.min(100, value / maximum * 100)) : 0;
}

function characterCard(character, enemy = false) {
  const active = gameState.current_actor === character.name ? " active" : "";
  const fallen = character.alive ? "" : " fallen";
  const threats = character.targeted_by || [];
  const targeted = threats.some((threat) => !threat.aoe) ? " targeted" : "";
  const endangered = !targeted && threats.length ? " endangered" : "";
  const tags = [
    ...(character.guarding ? [{name: "방어", guard: true}] : []),
    ...(character.guarded_by ? [{name: `엄호: ${character.guarded_by}`, guard: true}] : []),
    ...threats.map((threat) => ({
      name: `${threat.aoe ? "광역" : "표적"}: ${threat.enemy} · ${threat.action}`,
      threat: !threat.aoe,
      aoe: threat.aoe
    })),
    ...character.statuses.map((status) => ({name: `${status.name} ${status.turns}턴`}))
  ];
  const elementNames = {fire: "화", ice: "냉", thunder: "뇌", wind: "풍"};
  const detail = enemy
    ? `<p class="weakness">약점 ${elementNames[character.weakness] || "없음"} · 저항 ${elementNames[character.resistance] || "없음"}</p>
      <p class="enemy-intent${character.intent.phase ? " phase-intent" : ""}">다음 행동 · ${escapeHtml(character.intent.action)} → ${escapeHtml(character.intent.target)}${character.intent.phase ? " · 체력 구간 전용기" : ""}</p>`
    : "";
  return `<article class="character-card${active}${fallen}${targeted}${endangered}${enemy ? " enemy-card" : ""}">
    <div class="card-head"><strong>${escapeHtml(character.name)}</strong><span>Lv.${character.level} ${escapeHtml(character.job)}</span></div>
    <div class="meter-row"><span>HP</span><div class="meter"><i style="width:${percent(character.hp, character.max_hp)}%"></i></div><span>${character.hp}/${character.max_hp}</span></div>
    <div class="meter-row"><span>MP</span><div class="meter mp"><i style="width:${percent(character.mp, character.max_mp)}%"></i></div><span>${character.mp}/${character.max_mp}</span></div>
    ${detail}
    <div class="tags">${tags.map((tag) => `<span class="tag${tag.guard ? " guard" : ""}${tag.threat ? " threat" : ""}${tag.aoe ? " aoe" : ""}">${escapeHtml(tag.name)}</span>`).join("")}</div>
  </article>`;
}

function render() {
  if (!gameState) return;
  document.body.className = document.body.className.replace(/phase-\S+/g, "").trim();
  document.body.classList.add(`phase-${gameState.phase}`);
  $("#soundButton").textContent = soundEnabled ? "음향 켜짐" : "음향 꺼짐";
  $("#goldBadge").textContent = `${gameState.gold} G`;
  $("#inventoryLabel").textContent = `아이템 ${gameState.inventory_count} · 장비 ${gameState.equipment_count}`;
  $("#turnLabel").textContent = gameState.phase === "battle" ? `${gameState.turn}턴` : "대기 중";
  $("#partyCards").innerHTML = gameState.party.length
    ? gameState.party.map((member) => characterCard(member)).join("")
    : `<p class="muted-copy">아직 편성된 파티가 없습니다.</p>`;
  $("#enemyCards").innerHTML = gameState.phase === "battle"
    ? gameState.enemies.map((enemy) => characterCard(enemy, true)).join("") : "";
  $("#battleLog").innerHTML = gameState.logs.map((line) =>
    `<div class="log-entry${line.startsWith("★ ") ? " boss-phase-entry" : ""}">${escapeHtml(line)}</div>`
  ).join("");
  $("#battleLog").scrollTop = $("#battleLog").scrollHeight;

  const labels = {setup: "편성", explore: "탐험", dialogue: "대화", battle: "전투", victory: "승리", defeat: "전멸", fled: "도주", ending: "완료"};
  $("#phaseBadge").textContent = labels[gameState.phase] || gameState.phase;
  $("#stageTitle").textContent = gameState.phase === "setup" ? "원정대 편성"
    : gameState.phase === "battle" ? `${gameState.current_actor || "적"}의 차례`
    : gameState.location.name;

  const timeline = $("#turnTimeline");
  if (gameState.phase === "battle") {
    const timelineRow = (label, entries) => `<div><strong>${label}</strong><div>${entries.map((entry, index) =>
      `<span class="turn-chip ${entry.side}${entry.current ? " current" : ""}"><b>${index + 1}</b>${escapeHtml(entry.name)}<small>속도 ${entry.speed}${entry.intent ? ` · ${escapeHtml(entry.intent)}` : ""}</small></span>`
    ).join("") || `<span class="muted-copy">남은 행동 없음</span>`}</div></div>`;
    timeline.innerHTML = timelineRow("이번 턴 남은 순서", gameState.turn_timeline.current_round)
      + timelineRow("다음 턴 예상", gameState.turn_timeline.next_round);
    timeline.classList.remove("hidden");
  } else {
    timeline.classList.add("hidden");
    timeline.innerHTML = "";
  }

  renderWorld();
  renderCommands();
  scheduleAutoBattle();
}

function renderWorld() {
  $("#encounterPicker").classList.add("hidden");
  const setupPanel = $("#setupPanel");
  const locationPanel = $("#locationPanel");
  const dialoguePanel = $("#dialoguePanel");
  if (gameState.phase === "setup") {
    setupPanel.classList.remove("hidden");
    const fields = gameState.setup.defaults.map((member, index) => `
      <div class="setup-member">
        <label for="memberName${index}">파티원 ${index + 1} 이름</label>
        <input id="memberName${index}" maxlength="12" value="${escapeHtml(member.name)}" autocomplete="off">
        <label for="memberJob${index}">직업</label>
        <select id="memberJob${index}">${gameState.setup.jobs.map((job) => `<option value="${job.id}"${job.id === member.job ? " selected" : ""}>${escapeHtml(job.label)}</option>`).join("")}</select>
      </div>`).join("");
    const saves = gameState.save_slots.filter((slot) => slot.exists && slot.summary).map((slot) => `
      <button class="utility-card" onclick="loadSlot(${slot.slot})"><strong>슬롯 ${slot.slot} 불러오기</strong><span>${escapeHtml(slot.summary)}</span></button>`).join("");
    setupPanel.innerHTML = `<p class="setup-intro">세 명의 이름과 직업을 정하세요. 같은 직업을 여러 명 선택할 수도 있습니다.</p>
      <div class="setup-members">${fields}</div>
      <div class="setup-actions"><button onclick="submitPartySetup()">이 구성으로 모험 시작</button></div>
      ${saves ? `<div class="setup-saves"><p>기존 모험 이어하기</p><div class="utility-list">${saves}</div></div>` : ""}`;
  } else {
    setupPanel.classList.add("hidden");
    setupPanel.innerHTML = "";
  }
  const worldVisible = gameState.phase !== "battle" && gameState.phase !== "setup";
  locationPanel.classList.toggle("hidden", !worldVisible || gameState.phase === "dialogue");
  if (worldVisible) {
    const statuses = {available: "미수락", active: "진행 중", ready: "보상 가능", completed: "완료", locked: "미발견"};
    const region = gameState.maps.region;
    locationPanel.innerHTML = `
      <p class="location-copy">${escapeHtml(gameState.location.description)}</p>
      <div class="map-summary">
        <div><span>현재 지역</span><strong>${escapeHtml(region.name)}</strong><small>${region.visited_count}/${region.total_count} 장소 발견</small></div>
        <div class="map-shortcuts">
          <button onclick="openUtility('region_map')">지역 맵</button>
          <button onclick="openUtility('world_map')">전체 맵</button>
        </div>
      </div>
      <div class="quest-strip">${gameState.quests.filter((quest) => quest.status !== "locked").map((quest) => `<div class="quest-line"><strong>${escapeHtml(quest.title)}</strong><span>${escapeHtml(statuses[quest.status] || quest.status)}</span></div>`).join("")}</div>`;
  }

  if (gameState.phase === "dialogue" && gameState.dialogue) {
    dialoguePanel.classList.remove("hidden");
    const actions = gameState.dialogue.choices.length
      ? gameState.dialogue.choices.map((choice) => `<button onclick="advanceDialogue(${choice.index})">${escapeHtml(choice.label)}</button>`).join("")
      : `<button onclick="advanceDialogue(null)">계속</button>`;
    dialoguePanel.innerHTML = `${gameState.dialogue.lines.map((line) => `<p class="dialogue-line">${escapeHtml(line)}</p>`).join("")}<div class="dialogue-actions">${actions}</div>`;
  } else {
    dialoguePanel.classList.add("hidden");
    dialoguePanel.innerHTML = "";
  }
}

function renderCommands() {
  const battleEnabled = gameState.phase === "battle" && gameState.current_actor;
  const exploreEnabled = gameState.phase === "explore";
  if (battleEnabled) {
    utilityMode = null;
    $("#commandTitle").textContent = `${gameState.current_actor}의 명령`;
    const combo = gameState.combo;
    const chainHint = combo?.next_bonus
      ? `<p class="stat-line">연계 기회 · ${escapeHtml(gameState.enemies[combo.target].name)}을(를) 물리 공격하면 위력 +${combo.next_bonus}${combo.finisher ? ` · 3타 마무리: ${escapeHtml(combo.finisher)}` : ""}</p>`
      : `<p class="stat-line">서로 다른 파티원이 같은 적을 이어 공격하면 연계 위력이 증가합니다. 무기 착용 필요 · 턴마다 초기화</p>`;
    const manualDisabled = autoBattleEnabled ? " disabled" : "";
    const speedButtons = [1, 2, 3].map((speed) =>
      `<button class="speed-button${battleSpeed === speed ? " selected" : ""}" onclick="setBattleSpeed(${speed})">${speed}×</button>`
    ).join("");
    $("#commandButtons").innerHTML = `
      <div class="auto-battle-controls">
        <button class="auto-battle-toggle${autoBattleEnabled ? " active" : ""}" onclick="toggleAutoBattle()">${autoBattleEnabled ? "자동 전투 중지" : "자동 전투 시작"}</button>
        <div class="speed-controls"><span>전투 배속</span>${speedButtons}</div>
        <small>${autoBattleEnabled ? `${battleSpeed}× 속도로 상황 판단 중` : "회복·강화·약점·연계를 판단합니다"}</small>
      </div>
      ${chainHint}
      <button class="command-button" onclick="selectAttack()"${manualDisabled}>공격</button>
      <button class="command-button" onclick="selectSkill()"${manualDisabled}>스킬</button>
      <button class="command-button" onclick="selectItem()"${manualDisabled}>아이템</button>
      <button class="command-button" onclick="sendAction({type:'defend'})"${manualDisabled}>방어</button>
      <button class="command-button" onclick="selectProtect()"${manualDisabled}>아군 엄호</button>
      <button class="command-button danger" onclick="sendAction({type:'flee'})"${manualDisabled}>도주</button>`;
    renderChoicePanel();
  } else if (exploreEnabled) {
    $("#commandTitle").textContent = gameState.location.id === "abyss_dungeon"
      ? `심연 ${gameState.dungeon.depth}/${gameState.dungeon.max_depth} · ${gameState.dungeon.modifier} · 임시 ${gameState.dungeon.reward_bank}G/${gameState.dungeon.shard_bank}조각`
      : "이동";
    const moves = gameState.location.exits.map((exit) => {
      const encoded = encodeURIComponent(exit.label);
      const lock = exit.locked ? ` · 🔒 ${escapeHtml(exit.lock_reason || exit.required_item)}` : "";
      const returnClass = exit.target_id === "village" && gameState.location.id !== "village" ? " utility" : "";
      const action = exit.target_id === "abyss_dungeon" && !exit.locked
        ? "dungeonRequest('enter')" : `moveTo('${encoded}')`;
      return `<button class="command-button${returnClass}" onclick="${action}">${escapeHtml(exit.label)}${lock}</button>`;
    }).join("");
    const utilities = `${gameState.shop ? `<button class="command-button utility" onclick="openUtility('shop')">상점</button>` : ""}
      ${gameState.inn ? `<button class="command-button utility" onclick="innRequest()">여관 · 전원 회복</button>` : ""}
      ${gameState.blacksmith ? `<button class="command-button utility" onclick="openUtility('blacksmith')">대장간 · 장비 강화</button>` : ""}
      ${gameState.crafting ? `<button class="command-button utility" onclick="openUtility('crafting')">분해 · 합성 · 재련</button>` : ""}
      ${gameState.boss_retry?.available ? `<button class="command-button danger" onclick="bossRetry()">보스에게 다시 도전</button>` : ""}
      ${gameState.tower?.can_retry ? `<button class="command-button utility" onclick="towerRetry()">도전의 탑 ${gameState.tower.next_tier}단계 개방</button>` : ""}
      ${gameState.location.id === "abyss_dungeon" && gameState.dungeon.active ? `<button class="command-button danger" onclick="dungeonRequest('advance')">다음 층 도전 · ${gameState.dungeon.depth + 1}/${gameState.dungeon.max_depth} · 누적 조각 ${gameState.dungeon.shard_bank}개 위험</button>` : ""}
      <button class="command-button utility" onclick="openUtility('equipment')">장비</button>
      ${gameState.quest_board ? `<button class="command-button utility" onclick="openUtility('quest')">이야기 의뢰 게시판</button>` : ""}
      ${gameState.advancement_service ? `<button class="command-button utility" onclick="openUtility('advancement')">전직 교관 · 2차 직업</button>` : ""}
      ${gameState.village?.travel?.length ? `<button class="command-button utility" onclick="openUtility('travel')">방문한 마을로 이동</button>` : ""}
      ${gameState.village?.npc ? `<button class="command-button utility" onclick="openUtility('commission')">${escapeHtml(gameState.village.npc)}의 무작위 의뢰</button>` : ""}
      <button class="command-button utility" onclick="openUtility('save')">저장·불러오기</button>`;
    $("#commandButtons").innerHTML = moves + utilities;
    pending = null;
    if (utilityMode) renderUtilityPanel();
    else $("#choicePanel").classList.add("hidden");
  } else {
    utilityMode = null;
    $("#commandTitle").textContent = gameState.phase === "dialogue" ? "이야기" : "원정 상태";
    $("#commandButtons").innerHTML = gameState.result_message
      ? `<p class="location-copy">${escapeHtml(gameState.result_message)}</p>` : "";
    pending = null;
    $("#choicePanel").classList.add("hidden");
  }
}

function renderUtilityPanel() {
  const panel = $("#choicePanel");
  panel.classList.remove("hidden");
  if (utilityMode === "world_map") {
    const regions = gameState.maps.world.map((region) => {
      const state = region.current ? "현재 지역"
        : region.locked ? `🔒 ${region.lock_reason}`
        : region.visited ? `${region.visited_count}/${region.total_count} 발견`
        : "미발견";
      return `<article class="world-map-card${region.current ? " current" : ""}${region.locked ? " locked" : ""}">
        <span class="map-status">${escapeHtml(state)}</span>
        <strong>${escapeHtml(region.name)}</strong>
        <p>${escapeHtml(region.description)}</p>
      </article>`;
    }).join("");
    panel.innerHTML = utilityShell("전체 맵", `
      <p class="stat-line">세계의 권역별 탐험 진행과 해금 상태입니다. 지도에서 바로 이동하지는 않습니다.</p>
      <div class="world-map-grid">${regions}</div>`);
  } else if (utilityMode === "region_map") {
    const region = gameState.maps.region;
    const byId = Object.fromEntries(region.locations.map((location) => [location.id, location]));
    const nodes = region.locations.map((location) => {
      const state = location.current ? "현재 위치"
        : location.locked ? `🔒 ${location.lock_reason || "잠긴 경로"}`
        : location.visited ? (location.boss_defeated ? "방문 · 위험 제거" : "방문")
        : location.visible ? "인접 미발견" : "미발견";
      return `<article class="region-map-node${location.current ? " current" : ""}${location.visited ? " visited" : ""}${location.locked ? " locked" : ""}">
        <i></i><div><strong>${escapeHtml(location.name)}</strong><span>${escapeHtml(state)}</span></div>
      </article>`;
    }).join("");
    const links = region.links.map((link) => {
      const from = byId[link.from];
      const to = byId[link.to];
      if (!from || !to) return "";
      return `<div class="region-map-link"><span>${escapeHtml(from.name)}</span><b>→</b><span>${escapeHtml(to.name)}</span>${link.locked ? `<em>🔒 ${escapeHtml(link.lock_reason)}</em>` : ""}</div>`;
    }).join("");
    panel.innerHTML = utilityShell(`${region.name} · 지역 맵`, `
      <p class="stat-line">${escapeHtml(region.description)} · ${region.visited_count}/${region.total_count} 장소 발견</p>
      <div class="region-map-layout"><div class="region-map-nodes">${nodes}</div>
      <div class="region-map-routes"><p>확인된 연결 경로</p>${links || `<span class="muted-copy">아직 확인된 경로가 없습니다.</span>`}</div></div>`);
  } else if (utilityMode === "shop") {
    if (!gameState.shop) return clearUtility();
    if (shopIndex === null || !gameState.shop.shops[shopIndex]) {
      const shops = gameState.shop.shops.map((shop) => shop.available
        ? utilityButton(shop.name, shop.description || "판매 목록 보기", `selectShop(${shop.index})`)
        : `<div class="utility-card disabled"><strong>${escapeHtml(shop.name)} · 🔒</strong><span>${escapeHtml(shop.unlock_description)}</span></div>`
      ).join("");
      panel.innerHTML = utilityShell("시작 마을 상점가", utilitySection("방문할 상점", shops));
      return;
    }
    const shop = gameState.shop.shops[shopIndex];
    if (!shop.available) { shopIndex = null; return renderUtilityPanel(); }
    const buyItems = shop.items.map((item) => utilityButton(
      `${item.name} · ${item.price}G`, item.description,
      `shopRequest('buy_item',${item.index})`
    )).join("");
    const buyEquipment = shop.equipment.map((item) => equipmentButton(item,
      `${item.display_name} · ${item.price}G`, item.description,
      `shopRequest('buy_equipment',${item.index})`
    )).join("");
    const sellItems = gameState.shop.sell_items.map((item) => utilityButton(
      `${item.name} 판매 · ${item.price}G`, item.description,
      `shopRequest('sell_item',${item.index})`
    )).join("");
    const sellEquipment = gameState.shop.sell_equipment.map((item) => equipmentButton(item,
      `${item.display_name} 판매 · ${item.price}G`,
      `${item.description} · 분해 시 조각 ${item.shard_yield}개${item.can_dismantle_here ? "" : " (시작 마을 공방)"}`,
      `shopRequest('sell_equipment',${item.index})`
    )).join("");
    panel.innerHTML = utilityShell(shop.name, `
      <button class="command-button utility" onclick="selectShop(null)">다른 상점 보기</button>
      ${shop.discount_description ? `<p class="stat-line">${escapeHtml(shop.discount_description)}</p>` : ""}
      ${utilitySection("아이템 구매", buyItems)}
      ${utilitySection("장비 구매", buyEquipment)}
      ${utilitySection("판매", sellItems + sellEquipment)}`);
  } else if (utilityMode === "blacksmith") {
    if (!gameState.blacksmith) return clearUtility();
    const equipment = gameState.blacksmith.equipment.map((item) => {
      const detail = item.enhancement_level >= gameState.blacksmith.max_level
        ? "최대 강화 단계"
        : `${item.preview} · ${item.cost}G · 미강화 재료 ${item.materials}개 보유${item.locked ? " · 🔒 잠금 보호(강화 가능)" : ""}${item.reason ? ` · ${item.reason}` : ""}`;
      const action = item.can_upgrade ? `blacksmithRequest(${item.index})` : "";
      const duplicate = action
        ? equipmentButton(item, `${item.display_name} · 동일 장비 강화`, detail, action)
        : equipmentDisabledCard(item, item.display_name, detail);
      if (!gameState.blacksmith.star_unlocked) return duplicate;
      const starDetail = item.enhancement_level >= gameState.blacksmith.max_level
        ? "최대 강화 단계"
        : `${item.preview} · ${item.cost}G · 성운석 ${item.star_ore_cost}개 소비${item.star_reason ? ` · ${item.star_reason}` : ""}`;
      const star = item.can_star_upgrade
        ? equipmentButton(item, `${item.display_name} · 성운석 강화`, starDetail, `blacksmithRequest(${item.index},'star_ore')`)
        : equipmentDisabledCard(item, `${item.display_name} · 성운석 강화`, starDetail);
      return duplicate + star;
    }).join("");
    panel.innerHTML = utilityShell("마을 대장간", `
      <p class="stat-line">동일한 이름의 미강화(+0) 장비 1개와 골드를 사용해 최대 +${gameState.blacksmith.max_level}까지 확정 강화합니다.</p>
      <p class="stat-line">${gameState.blacksmith.star_unlocked
        ? `별빛 강화 개방 · 성운석 ${gameState.blacksmith.star_ore_count}개 보유. 동일 장비 대신 다음 강화 단계만큼의 성운석을 사용할 수 있습니다. 별의 균열 보스 승리마다 3개를 얻습니다.`
        : "검은 별의 잔재를 처치하면 동일 장비가 필요 없는 별빛 강화가 열립니다."}</p>
      ${utilitySection("강화할 장비", equipment)}`);
  } else if (utilityMode === "crafting") {
    if (!gameState.crafting) return clearUtility();
    const familyIds = gameState.crafting.families.map((family) => family.id);
    if (!familyIds.includes(craftingFamily)) craftingFamily = familyIds[0] || "sword";
    const family = gameState.crafting.families.find((entry) => entry.id === craftingFamily);
    const familyTabs = gameState.crafting.families.map((entry) => `
      <button class="mini-tab${entry.id === craftingFamily ? " selected" : ""}" onclick="selectCraftingFamily('${entry.id}')">${escapeHtml(entry.name)}</button>`).join("");
    const recipes = gameState.crafting.recipes.map((recipe) => {
      const preview = recipe.previews[craftingFamily];
      const compatible = preview.compatible_members.map((member) => `${member.name}(${member.job})`).join(" · ") || "현재 파티에 없음";
      const optionText = preview.options_random ? `무작위 부가 옵션 ${preview.option_count}개` : "부가 옵션 없음";
      const detail = `장비 조각 ${recipe.shard_cost}개 · ${recipe.gold_cost}G${recipe.reason ? ` · ${recipe.reason}` : ""}\n예상 Lv.${preview.level} · ${preview.stat_text}\n${optionText} · 장착 가능: ${compatible}`;
      const item = {rarity: recipe.rarity};
      return recipe.can_synthesize
        ? equipmentButton(item, `${recipe.rarity_name} ${family?.name || "무기"} 합성`, detail,
            `craftingRequest('synthesize',null,'${recipe.rarity}','${craftingFamily}','${recipe.quotes[craftingFamily]}')`)
        : equipmentDisabledCard(item, `${recipe.rarity_name} ${family?.name || "무기"} 합성`, detail);
    }).join("");
    const reforge = gameState.crafting.reforge.map((item) => {
      const lockOptions = [`<option value="">옵션 고정 없음</option>`, ...item.affixes.map((affix) =>
        `<option value="${escapeHtml(affix)}">${escapeHtml(affix)} 고정 · 비용 2배</option>`)].join("");
      return `<div class="utility-card reforge-card ${rarityClass(item.rarity)}">
        <strong>${escapeHtml(item.display_name)}</strong>
        <span>현재 옵션: ${escapeHtml(item.affixes.join(" · "))}</span>
        <span>기본 비용 ${item.base_shard_cost}조각 · ${item.base_gold_cost}G / 고정 시 ${item.lock_shard_cost}조각 · ${item.lock_gold_cost}G</span>
        <div><select id="reforgeLock${item.index}" aria-label="고정할 옵션">${lockOptions}</select>
        <button onclick="reforgePreviewRequest(${item.index},'${item.quote}')" ${item.can_reforge ? "" : "disabled"}>결과 미리보기</button></div>
        ${item.reason ? `<small>${escapeHtml(item.reason)}</small>` : ""}
      </div>`;
    }).join("");
    const dismantleItems = gameState.crafting.dismantle;
    const currentIndices = new Set(dismantleItems.filter((item) => item.bulk_eligible).map((item) => item.index));
    dismantleSelection = new Set([...dismantleSelection].filter((index) => currentIndices.has(index)));
    const filteredDismantle = dismantleItems.filter((item) => {
      if (dismantleRarity !== "all" && item.rarity !== dismantleRarity) return false;
      if (dismantleFamily !== "all" && item.weapon_family !== dismantleFamily) return false;
      if (dismantleUnenhancedOnly && item.enhancement_level !== 0) return false;
      if (dismantleIncompatibleOnly && item.compatible_with_party) return false;
      return true;
    });
    const selectedItems = dismantleItems.filter((item) => dismantleSelection.has(item.index));
    const selectedShards = selectedItems.reduce((sum, item) => sum + item.shard_yield, 0);
    const rarityNames = {common:"일반", uncommon:"고급", rare:"희귀", epic:"영웅", legendary:"전설"};
    const rarityOptions = [`<option value="all">전체 등급</option>`, ...Object.entries(rarityNames).map(([id, name]) =>
      `<option value="${id}"${dismantleRarity === id ? " selected" : ""}>${name}</option>`)].join("");
    const familyOptions = [`<option value="all">전체 무기 계열</option>`, ...gameState.crafting.families.map((entry) =>
      `<option value="${entry.id}"${dismantleFamily === entry.id ? " selected" : ""}>${escapeHtml(entry.name)}</option>`)].join("");
    const dismantle = filteredDismantle.map((item) => {
      const selected = dismantleSelection.has(item.index);
      const detail = [item.description, item.special_effect,
        `판매 ${item.sale_price}G / 분해 ${item.shard_yield}조각`,
        item.bulk_eligible ? "" : `일괄 분해 제외 · ${item.bulk_exclusion_reason}`]
        .filter(Boolean).join(" · ");
      return `<label class="dismantle-select-card ${rarityClass(item.rarity)}${selected ? " selected" : ""}${item.bulk_eligible ? "" : " excluded"}">
        <input type="checkbox" ${selected ? "checked" : ""} ${item.bulk_eligible ? "" : "disabled"}
          onchange="toggleDismantleSelection(${item.index},this.checked)">
        <span><strong>${escapeHtml(item.display_name)}</strong><small>${escapeHtml(detail)}</small></span>
      </label>`;
    }).join("");
    const safeVisibleCount = filteredDismantle.filter((item) => item.bulk_eligible).length;
    const dismantleControls = `<div class="dismantle-toolbar">
      <select onchange="setDismantleFilter('rarity',this.value)">${rarityOptions}</select>
      <select onchange="setDismantleFilter('family',this.value)">${familyOptions}</select>
      <label><input type="checkbox" ${dismantleUnenhancedOnly ? "checked" : ""} onchange="setDismantleFilter('unenhanced',this.checked)"> 미강화만</label>
      <label><input type="checkbox" ${dismantleIncompatibleOnly ? "checked" : ""} onchange="setDismantleFilter('incompatible',this.checked)"> 파티 직업 비호환만</label>
    </div>
    <div class="dismantle-summary">
      <strong>${selectedItems.length}개 선택 · 예상 조각 ${selectedShards}개</strong>
      <span>전설·강화·잠금 장비는 일괄 분해에서 자동 제외됩니다.</span>
      <div><button onclick="selectVisibleDismantle()" ${safeVisibleCount ? "" : "disabled"}>보이는 장비 선택</button>
      <button onclick="clearDismantleSelection()" ${selectedItems.length ? "" : "disabled"}>선택 해제</button>
      <button class="bulk-dismantle" onclick="bulkDismantleRequest()" ${selectedItems.length ? "" : "disabled"}>선택 장비 분해</button></div>
    </div>`;
    panel.innerHTML = utilityShell("분해 · 합성 · 재련 공방", `
      <p class="stat-line">보유 장비 조각 ${gameState.crafting.shards}개 · ${gameState.gold}G</p>
      <p class="stat-line">미착용 장비를 분해·합성하고, 희귀 이상 생성 장비의 옵션을 결과 확인 후 재련합니다.</p>
      <p class="stat-line">강화 분해 보너스: ${gameState.crafting.enhancement_bonuses.map((entry) => `+${entry.level} ${entry.shards}개`).join(" · ")}</p>
      <div class="mini-tabs">${familyTabs}</div>
      ${utilitySection(`${family?.name || "무기"} 합성`, recipes)}
      ${utilitySection("희귀 이상 장비 옵션 재련", reforge || `<span class="muted-copy">재련 가능한 미착용 장비가 없습니다.</span>`)}
      ${utilitySection("미착용 장비 다중 분해", `${dismantleControls}<div class="dismantle-grid">${dismantle || `<span class="muted-copy">조건에 맞는 장비가 없습니다.</span>`}</div>`)}`);
  } else if (utilityMode === "equipment") {
    equipmentMember = Math.max(0, Math.min(equipmentMember, gameState.party.length - 1));
    const member = gameState.party[equipmentMember];
    const memberTabs = gameState.party.map((character, index) => `
      <button class="mini-tab${index === equipmentMember ? " selected" : ""}" onclick="selectEquipmentMember(${index})">${escapeHtml(character.name)}</button>`).join("");
    const worn = Object.entries(member.equipment).map(([slot, item]) => item
      ? equipmentProtectionRow(item, `${item.slot_name}: ${item.display_name}`, item.description,
          `equipmentRequest('unequip',${equipmentMember},null,'${slot}')`, true,
          `equipmentRequest('${item.locked ? "unlock" : "lock"}',${equipmentMember},null,'${slot}')`)
      : `<div class="empty-slot">${{weapon:"무기",armor:"방어구",accessory:"장신구"}[slot]}: 없음</div>`).join("");
    const allowedWeapons = member.allowed_weapon_families || [];
    const allowedIds = new Set(allowedWeapons.map((family) => family.id));
    const inventory = gameState.equipment_inventory.map((item) => {
      const compatible = item.slot !== "weapon" || !item.weapon_family || allowedIds.has(item.weapon_family);
      const detail = [item.description, item.special_effect, compatible ? "" : `${member.base_job || member.job} 장착 불가`]
        .filter(Boolean).join(" · ");
      return equipmentProtectionRow(
        item, `${item.slot_name}: ${item.display_name}`, detail,
        `equipmentRequest('equip',${equipmentMember},${item.index},null)`, compatible,
        `equipmentRequest('${item.locked ? "unlock" : "lock"}',${equipmentMember},${item.index},null)`
      );
    }).join("");
    panel.innerHTML = utilityShell("장비 관리", `
      <div class="mini-tabs">${memberTabs}</div>
      <p class="stat-line">공격 ${member.stats.attack} · 방어 ${member.stats.defense} · 속도 ${member.stats.speed}</p>
      <p class="stat-line">사용 가능 무기: ${allowedWeapons.map((family) => escapeHtml(family.name)).join(" · ") || "없음"}</p>
      ${utilitySection("착용 장비 · 누르면 해제", worn)}
      ${utilitySection("보유 장비 · 누르면 착용", inventory)}`);
  } else if (utilityMode === "quest") {
    const statusNames = {available:"수락 가능",active:"진행 중",ready:"보상 가능",completed:"완료",locked:"미발견"};
    const quests = gameState.quests.map((quest) => {
      if (quest.status === "locked") return "";
      let action = "";
      if (quest.status === "available") action = `questRequest('accept','${quest.id}')`;
      if (quest.status === "ready") action = `questRequest('claim','${quest.id}')`;
      const bonus = quest.bonus_gold_reward ? ` · 호위 시 +${quest.bonus_gold_reward}G` : "";
      const detail = `${quest.objective} · 기본 ${quest.gold_reward}G${bonus}`;
      return action
        ? utilityButton(`${quest.title} · ${statusNames[quest.status]}`, detail, action)
        : `<div class="utility-card disabled"><strong>${escapeHtml(quest.title)} · ${statusNames[quest.status]}</strong><span>${escapeHtml(detail)}</span></div>`;
    }).join("");
    panel.innerHTML = utilityShell("의뢰 게시판", utilitySection("퀘스트", quests));
  } else if (utilityMode === "travel") {
    const destinations = gameState.village.travel.map((village) => utilityButton(
      village.name, "한 번 방문한 마을은 이동로로 즉시 오갈 수 있습니다.",
      `travelRequest('${village.id}')`
    )).join("");
    panel.innerHTML = utilityShell("마을 간 이동", utilitySection("방문한 마을", destinations));
  } else if (utilityMode === "commission") {
    const npc = gameState.village.npc;
    const commission = gameState.village.commission;
    if (!commission) {
      panel.innerHTML = utilityShell(`${npc}의 의뢰`, utilitySection(
        "지역 의뢰", utilityButton("새 의뢰를 요청한다", "지역에 맞는 의뢰가 무작위로 배정됩니다.", "commissionRequest('offer')")
      ));
    } else {
      const statusNames = {offered:"제안됨",active:"진행 중",ready:"보상 가능"};
      const rewards = [`${commission.gold_reward}G`, ...commission.item_rewards.map((item) => `${item.name}×${item.count}`)].join(" · ");
      let action = `<div class="utility-card disabled"><strong>${escapeHtml(commission.title)} · ${statusNames[commission.status]}</strong><span>${escapeHtml(commission.objective)} · ${commission.progress}/${commission.required} · 보상 ${escapeHtml(rewards)}</span></div>`;
      if (commission.status === "offered") action = utilityButton(
        `${commission.title} · 수락`, `${commission.objective} · 보상 ${rewards}`, "commissionRequest('accept')"
      );
      if (commission.status === "ready") action = utilityButton(
        `${commission.title} · 보상 받기`, `${commission.objective} · 보상 ${rewards}`, "commissionRequest('claim')"
      );
      panel.innerHTML = utilityShell(`${npc}의 의뢰`, `<p class="stat-line">${escapeHtml(commission.description)}</p>${utilitySection("지역 의뢰", action)}`);
    }
  } else if (utilityMode === "advancement") {
    const members = gameState.advancement.map((member) => {
      const choices = member.options.map((job) => utilityButton(
        `${job.name} · ${job.skill}`, job.description,
        `advancementRequest(${member.member},'${job.id}')`
      )).join("");
      return `<section class="utility-section"><p>${escapeHtml(member.name)} · ${escapeHtml(member.job)} · Lv.${member.level}</p>
        ${member.advanced_job_id ? `<span class="muted-copy">전직 완료 · ${escapeHtml(member.job)}</span>` :
          member.eligible ? `<div class="utility-list">${choices}</div>` :
          `<span class="muted-copy">Lv.${member.required_level}부터 전직 가능</span>`}</section>`;
    }).join("");
    panel.innerHTML = utilityShell("전직 교관", `<p class="stat-line">5레벨 이상 파티원마다 공격·방어·지원 성향의 3가지 계열 중 하나를 선택합니다. 전직은 되돌릴 수 없습니다.</p>${members}`);
  } else if (utilityMode === "save") {
    const slots = gameState.save_slots.map((slot) => `<div class="save-row">
      <div><strong>슬롯 ${slot.slot}</strong><span>${escapeHtml(slot.summary || (slot.exists ? "손상된 저장" : "비어 있음"))}</span></div>
      <div><button onclick="saveSlot(${slot.slot},${slot.exists})">저장</button>${slot.exists && slot.summary ? `<button onclick="loadSlot(${slot.slot})">불러오기</button>` : ""}</div>
    </div>`).join("");
    panel.innerHTML = utilityShell("저장·불러오기", `<div class="save-list">${slots}</div>`);
  }
}

function utilityShell(title, content) {
  return `<div class="utility-head"><strong>${escapeHtml(title)}</strong><button onclick="clearUtility()">닫기</button></div>${content}`;
}

function utilitySection(title, content) {
  return `<section class="utility-section"><p>${escapeHtml(title)}</p><div class="utility-list">${content || `<span class="muted-copy">항목이 없습니다.</span>`}</div></section>`;
}

function utilityButton(title, detail, onclick) {
  return `<button class="utility-card" onclick="${onclick}"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span></button>`;
}

function rarityClass(rarity) {
  return ["common", "uncommon", "rare", "epic", "legendary"].includes(rarity) ? `rarity-${rarity}` : "";
}

function equipmentButton(item, title, detail, onclick) {
  return `<button class="utility-card ${rarityClass(item.rarity)}" onclick="${onclick}"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span></button>`;
}

function equipmentDisabledCard(item, title, detail) {
  return `<div class="utility-card disabled ${rarityClass(item.rarity)}"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span></div>`;
}

function equipmentProtectionRow(item, title, detail, onclick, enabled, lockOnclick) {
  const lockLabel = item.locked ? "🔓 잠금 해제" : "🔒 잠금";
  const card = enabled
    ? equipmentButton(item, `${item.locked ? "🔒 " : ""}${title}`, detail, onclick)
    : equipmentDisabledCard(item, `${item.locked ? "🔒 " : ""}${title}`, detail);
  return `<div class="equipment-protection-row">${card}<button class="protection-toggle${item.locked ? " active" : ""}" onclick="${lockOnclick}">${lockLabel}</button></div>`;
}

function openUtility(mode) { utilityMode = mode; if (mode === "shop") shopIndex = null; renderUtilityPanel(); }
function clearUtility() { utilityMode = null; shopIndex = null; $("#choicePanel").classList.add("hidden"); }
function selectShop(index) { shopIndex = index; renderUtilityPanel(); }
function selectEquipmentMember(index) { equipmentMember = index; renderUtilityPanel(); }
function selectCraftingFamily(family) { craftingFamily = family; renderUtilityPanel(); }
function setDismantleFilter(kind, value) {
  if (kind === "rarity") dismantleRarity = value;
  if (kind === "family") dismantleFamily = value;
  if (kind === "unenhanced") dismantleUnenhancedOnly = Boolean(value);
  if (kind === "incompatible") dismantleIncompatibleOnly = Boolean(value);
  renderUtilityPanel();
}
function toggleDismantleSelection(index, selected) {
  if (selected) dismantleSelection.add(index); else dismantleSelection.delete(index);
  renderUtilityPanel();
}
function filteredBulkDismantleItems() {
  return (gameState.crafting?.dismantle || []).filter((item) => item.bulk_eligible)
    .filter((item) => dismantleRarity === "all" || item.rarity === dismantleRarity)
    .filter((item) => dismantleFamily === "all" || item.weapon_family === dismantleFamily)
    .filter((item) => !dismantleUnenhancedOnly || item.enhancement_level === 0)
    .filter((item) => !dismantleIncompatibleOnly || !item.compatible_with_party);
}
function selectVisibleDismantle() {
  filteredBulkDismantleItems().forEach((item) => dismantleSelection.add(item.index));
  renderUtilityPanel();
}
function clearDismantleSelection() { dismantleSelection.clear(); renderUtilityPanel(); }
function shopRequest(operation, index) {
  if (operation === "sell_equipment") {
    const item = gameState.shop?.sell_equipment.find((entry) => entry.index === index);
    if (!item || !confirm(`${item.display_name}\n판매: ${item.price}G\n분해: 장비 조각 ${item.shard_yield}개${item.can_dismantle_here ? "" : " (시작 마을 공방)"}\n\n이 장비를 판매할까요? 판매 후에는 분해할 수 없습니다.`)) return;
  }
  request("/api/shop", {operation, index, shop: shopIndex});
}
async function blacksmithRequest(equipment, material = "duplicate") {
  if (forgeBusy) return;
  const item = gameState.blacksmith?.equipment.find((entry) => entry.index === equipment);
  if (!item) return;
  const materials = material === "star_ore" ? `성운석 ${item.star_ore_cost}개` : "같은 미강화(+0) 장비 1개";
  if (confirm(`${item.display_name}\n${item.preview}\n${materials}와 ${item.cost}G를 사용해 강화할까요?`)) {
    forgeBusy = true;
    document.querySelectorAll('#choicePanel button').forEach(button => button.disabled = true);
    try {
      const quote = material === "star_ore" ? item.star_quote : item.quote;
      await request("/api/blacksmith", {equipment, material, quote});
    } catch (_error) {
      showError("처리 결과를 확인하지 못했습니다. 목록을 새로고침한 뒤 확인하세요.");
    } finally {
      forgeBusy = false;
      render();
    }
  }
}
async function craftingRequest(operation, equipment, rarity, family, quote) {
  if (craftingBusy) return;
  let message;
  if (operation === "dismantle") {
    const item = gameState.crafting?.dismantle.find((entry) => entry.index === equipment);
    if (!item) return;
    const warning = item.protection_warning ? `\n⚠ ${item.protection_warning}` : "";
    message = `${item.display_name}${warning}\n장비 조각 ${item.shard_yield}개로 분해할까요?\n분해한 장비는 복구할 수 없습니다.`;
  } else {
    const recipe = gameState.crafting?.recipes.find((entry) => entry.rarity === rarity);
    const familyName = gameState.crafting?.families.find((entry) => entry.id === family)?.name;
    if (!recipe || !familyName) return;
    const preview = recipe.previews[family];
    const compatible = preview.compatible_members.map((member) => `${member.name}(${member.job})`).join(" · ") || "현재 파티에 없음";
    const optionText = preview.options_random ? `무작위 부가 옵션 ${preview.option_count}개` : "부가 옵션 없음";
    message = `${recipe.rarity_name} ${familyName} · 예상 Lv.${preview.level}\n${preview.stat_text}\n${optionText}\n장착 가능: ${compatible}\n\n장비 조각 ${recipe.shard_cost}개와 ${recipe.gold_cost}G를 사용해 합성할까요?`;
  }
  if (!confirm(message)) return;
  craftingBusy = true;
  document.querySelectorAll('#choicePanel button').forEach(button => button.disabled = true);
  try {
    await request("/api/crafting", {operation, equipment, rarity, family, quote});
  } catch (_error) {
    showError("처리 결과를 확인하지 못했습니다. 목록을 새로고침한 뒤 확인하세요.");
  } finally {
    craftingBusy = false;
    render();
  }
}
async function reforgePreviewRequest(equipment, quote) {
  if (craftingBusy) return;
  const lockedAffix = document.querySelector(`#reforgeLock${equipment}`)?.value || "";
  craftingBusy = true;
  document.querySelectorAll('#choicePanel button, #choicePanel select').forEach((element) => element.disabled = true);
  try {
    const result = await request("/api/crafting", {
      operation: "reforge_preview", equipment, quote, locked_affix: lockedAffix,
    });
    const preview = result?.reforge_preview;
    if (!result?.ok || !preview) return;
    const fixed = preview.locked_affix ? `고정 옵션: ${preview.locked_affix}\n` : "";
    const accepted = confirm(
      `${preview.before.display_name}\n${fixed}\n` +
      `변경 전: ${preview.before.special_effect}\n${preview.before.description}\n\n` +
      `변경 후: ${preview.after.special_effect}\n${preview.after.description}\n\n` +
      `장비 조각 ${preview.shard_cost}개와 ${preview.gold_cost}G를 사용해 이 결과를 확정할까요?`
    );
    if (accepted) {
      await request("/api/crafting", {
        operation: "reforge_apply", reforge_token: preview.token,
      });
    }
  } catch (_error) {
    showError("재련 결과를 확인하지 못했습니다. 목록을 새로고침한 뒤 다시 시도하세요.");
  } finally {
    craftingBusy = false;
    render();
  }
}
async function bulkDismantleRequest() {
  if (craftingBusy || !gameState.crafting) return;
  const items = gameState.crafting.dismantle.filter((item) => dismantleSelection.has(item.index) && item.bulk_eligible);
  if (!items.length) return;
  const shards = items.reduce((sum, item) => sum + item.shard_yield, 0);
  const names = items.slice(0, 6).map((item) => item.display_name).join(" · ");
  const more = items.length > 6 ? ` 외 ${items.length - 6}개` : "";
  if (!confirm(`${names}${more}\n\n장비 ${items.length}개를 분해해 조각 ${shards}개를 얻을까요?\n분해한 장비는 복구할 수 없습니다.`)) return;
  craftingBusy = true;
  document.querySelectorAll('#choicePanel button, #choicePanel input, #choicePanel select').forEach((element) => element.disabled = true);
  try {
    const result = await request("/api/crafting", {
      operation: "bulk_dismantle",
      equipment_indices: items.map((item) => item.index),
      quote: gameState.crafting.bulk_dismantle_quote,
    });
    if (result?.ok) dismantleSelection.clear();
  } catch (_error) {
    showError("처리 결과를 확인하지 못했습니다. 목록을 새로고침한 뒤 확인하세요.");
  } finally {
    craftingBusy = false;
    render();
  }
}
function innRequest() { request("/api/inn", {}); }
function advancementRequest(member, job) {
  if (confirm("이 2차 직업으로 전직할까요? 전직은 되돌릴 수 없습니다.")) {
    request("/api/advancement", {member, job});
  }
}
function towerRetry() {
  if (confirm(`도전의 탑 ${gameState.tower.next_tier}단계를 개방할까요?`)) {
    request("/api/tower", {operation: "reset"});
  }
}
function dungeonRequest(operation) {
  const messages = {
    enter: `입장 준비금 ${gameState.dungeon.entry_fee}G를 내고 심연 원정을 시작할까요?\n층별 장비 조각 2·4·6·8개가 임시 보관되며 완주 시 ${gameState.dungeon.full_clear_shard_bonus}개를 추가로 얻습니다.`,
    advance: `다음 층으로 내려갈까요?\n전멸하면 ${gameState.dungeon.reward_bank}G와 장비 조각 ${gameState.dungeon.shard_bank}개를 잃습니다.`,
    retreat: `${gameState.dungeon.reward_bank}G와 장비 조각 ${gameState.dungeon.shard_bank}개를 확정하고 마을로 귀환할까요?`,
  };
  if (confirm(messages[operation])) request("/api/dungeon", {operation});
}
function bossRetry() {
  if (confirm(`${gameState.boss_retry.location_name}의 보스에게 다시 도전할까요?`)) {
    request("/api/boss", {operation: "retry"});
  }
}
function equipmentRequest(operation, member, equipment, slot) { request("/api/equipment", {operation, member, equipment, slot}); }
function questRequest(operation, quest) { request("/api/quest", {operation, quest}); }
function travelRequest(target) { request("/api/travel", {target}); }
function commissionRequest(operation) { request("/api/commission", {operation}); }
function saveSlot(slot, exists) {
  if (!exists || confirm(`슬롯 ${slot}에 덮어쓸까요?`)) request("/api/save", {operation: "save", slot});
}
function loadSlot(slot) {
  if (confirm(`현재 진행을 중단하고 슬롯 ${slot}을 불러올까요?`)) request("/api/save", {operation: "load", slot});
}

function renderChoicePanel() {
  const panel = $("#choicePanel");
  if (!pending) {
    panel.classList.add("hidden");
    return;
  }
  panel.classList.remove("hidden");
  if (pending.mode === "enemy") {
    panel.innerHTML = choices("대상을 선택하세요", livingEnemies(), (enemy) => enemy.name, (enemy) => ({target: enemy.index}));
  } else if (pending.mode === "party") {
    panel.innerHTML = choices("대상을 선택하세요", livingParty(), (member) => member.name, (member) => ({target: member.index}));
  } else if (pending.mode === "protect") {
    const candidates = livingParty().filter((member) => member.name !== gameState.current_actor);
    panel.innerHTML = choices("엄호할 파티원을 선택하세요", candidates,
      (member) => member.name, (member) => ({target: member.index}),
      () => "다음 단일 대상 공격을 대신 받고 방어로 피해를 줄입니다");
  } else if (pending.mode === "skill") {
    panel.innerHTML = choices("사용할 스킬을 선택하세요", gameState.skills,
      (skill) => `${skill.name} · MP ${skill.mp_cost}`,
      (skill) => ({skill: skill.index}), (skill) => skill.description);
  } else if (pending.mode === "item") {
    panel.innerHTML = choices("사용할 아이템을 선택하세요", gameState.items,
      (item) => item.name, (item) => ({item: item.index}), (item) => item.description);
  }
}

function choices(title, items, label, value, description = () => "") {
  if (!items.length) return `<p class="choice-title">선택 가능한 항목이 없습니다.</p>`;
  return `<p class="choice-title">${escapeHtml(title)}</p><div class="choice-list">${items.map((item) => {
    const payload = encodeURIComponent(JSON.stringify(value(item)));
    return `<button class="choice-button" onclick="acceptChoice('${payload}')"><strong>${escapeHtml(label(item))}</strong><span>${escapeHtml(description(item))}</span></button>`;
  }).join("")}<button class="choice-button" onclick="clearChoice()"><strong>이전 메뉴</strong><span>행동 선택으로 돌아갑니다</span></button></div>`;
}

function livingEnemies() {
  return gameState.enemies.filter((enemy) => enemy.alive).map((enemy, index) => ({...enemy, index}));
}

function livingParty() {
  return gameState.party.filter((member) => member.alive).map((member, index) => ({...member, index}));
}

function selectAttack() { pending = {mode: "enemy", action: {type: "attack"}}; renderChoicePanel(); }
function selectSkill() { pending = {mode: "skill", action: {type: "skill"}}; renderChoicePanel(); }
function selectItem() { pending = {mode: "item", action: {type: "item"}}; renderChoicePanel(); }
function selectProtect() { pending = {mode: "protect", action: {type: "protect"}}; renderChoicePanel(); }
function clearChoice() { pending = null; renderChoicePanel(); }

function acceptChoice(encoded) {
  const value = JSON.parse(decodeURIComponent(encoded));
  pending.action = {...pending.action, ...value};
  if (pending.mode === "skill") {
    const skill = gameState.skills[value.skill];
    if (skill.aoe) return sendAction(pending.action);
    pending.mode = skill.target_side === "party" ? "party" : "enemy";
    renderChoicePanel();
    return;
  }
  if (pending.mode === "item") {
    pending.mode = "party";
    renderChoicePanel();
    return;
  }
  sendAction(pending.action);
}

function sendAction(action) {
  if (!autoBattleEnabled) request("/api/action", action);
}
function toggleAutoBattle() {
  if (gameState?.phase !== "battle") return;
  autoBattleEnabled = !autoBattleEnabled;
  pending = null;
  if (!autoBattleEnabled) clearTimeout(autoBattleTimer);
  render();
}
function setBattleSpeed(speed) {
  if (![1, 2, 3].includes(speed)) return;
  battleSpeed = speed;
  localStorage.setItem("undefined-legend-battle-speed", String(speed));
  render();
}
function scheduleAutoBattle() {
  clearTimeout(autoBattleTimer);
  if (!autoBattleEnabled || autoRequestInFlight || gameState?.phase !== "battle" || !gameState.current_actor) return;
  autoBattleTimer = setTimeout(runAutoBattleStep, AUTO_BATTLE_DELAYS[battleSpeed]);
}
async function runAutoBattleStep() {
  if (!autoBattleEnabled || autoRequestInFlight || gameState?.phase !== "battle") return;
  autoRequestInFlight = true;
  try {
    const result = await request("/api/auto", {});
    if (!result.ok) autoBattleEnabled = false;
  } catch (_error) {
    autoBattleEnabled = false;
    showError("자동 전투 연결이 끊겼습니다. 수동 전투로 전환했습니다.");
  } finally {
    autoRequestInFlight = false;
    render();
  }
}
function startBattle(id) { request("/api/start", {encounter: id}); }
function moveTo(encoded) { utilityMode = null; request("/api/move", {exit: decodeURIComponent(encoded)}); }
function advanceDialogue(choice) { utilityMode = null; request("/api/dialogue", {choice}); }
function showError(message) {
  $("#errorMessage").textContent = message;
  $("#errorMessage").classList.toggle("hidden", !message);
}

function submitPartySetup() {
  const members = gameState.setup.defaults.map((_, index) => ({
    name: $(`#memberName${index}`).value,
    job: $(`#memberJob${index}`).value
  }));
  request("/api/setup", {members});
}

function playResponseTone(path, before, after) {
  if (after === "battle" && before !== "battle") return playTone("battle");
  if (after === "victory" || after === "ending") return playTone("victory");
  if (after === "dialogue" && before !== "dialogue") return playTone("dialogue");
  if (["/api/action", "/api/shop", "/api/inn", "/api/blacksmith", "/api/crafting", "/api/tower", "/api/dungeon", "/api/boss", "/api/equipment", "/api/quest", "/api/travel", "/api/commission", "/api/advancement", "/api/save"].includes(path)) return playTone("confirm");
  if (path === "/api/move") return playTone("move");
}

function playTone(kind) {
  if (!soundEnabled) return;
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) return;
  const context = new AudioContext();
  const patterns = {
    confirm: [[520, .06]], move: [[330, .05], [440, .07]],
    dialogue: [[420, .06], [560, .08]], battle: [[180, .08], [130, .12]],
    victory: [[440, .08], [554, .08], [659, .14]], error: [[150, .12]]
  };
  let cursor = context.currentTime;
  for (const [frequency, duration] of (patterns[kind] || patterns.confirm)) {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "sine";
    oscillator.frequency.value = frequency;
    gain.gain.setValueAtTime(.0001, cursor);
    gain.gain.exponentialRampToValueAtTime(.08, cursor + .01);
    gain.gain.exponentialRampToValueAtTime(.0001, cursor + duration);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start(cursor);
    oscillator.stop(cursor + duration + .01);
    cursor += duration;
  }
  setTimeout(() => context.close(), Math.max(250, (cursor - context.currentTime + .1) * 1000));
}

$("#soundButton").addEventListener("click", () => {
  soundEnabled = !soundEnabled;
  localStorage.setItem("undefined-legend-sound", soundEnabled ? "on" : "off");
  $("#soundButton").textContent = soundEnabled ? "음향 켜짐" : "음향 꺼짐";
  if (soundEnabled) playTone("confirm");
});

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  installPrompt = event;
  $("#installButton").classList.remove("hidden");
});

$("#installButton").addEventListener("click", async () => {
  if (!installPrompt) return;
  installPrompt.prompt();
  await installPrompt.userChoice;
  installPrompt = null;
  $("#installButton").classList.add("hidden");
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));
}

$("#newGameButton").addEventListener("click", () => {
  if (gameState?.phase === "setup" || confirm("현재 진행을 중단하고 새 게임을 시작할까요?")) {
    autoBattleEnabled = false;
    clearTimeout(autoBattleTimer);
    utilityMode = null;
    request("/api/new", {});
  }
});
request("/api/state")
  .then(restoreBrowserBackups)
  .catch(() => showError("서버에 연결할 수 없습니다. web_app.py가 실행 중인지 확인하세요."));
