// 부품·RMA 공용 (티켓 상세·부품 화면·홈에서 사용)
// parts 문서: { name, pn, fru, qty, case_no, new_sn, old_sn, return_required, return_days, tracking, memo,
//              status: 요청|입고|교체|반납|종결, dates: {요청,입고,교체,반납,종결: 'YYYY-MM-DD'},
//              ticket_id, ticket_title, customer_id, asset_id, asset_host }
// 반납 기한 = 교체일 + return_days (반납 필요한 부품만)
window.Parts = (() => {
  const STAGES = ['요청', '입고', '교체', '반납', '종결'];
  const STAGE_HINT = { '요청': '벤더 RMA 접수', '입고': '새 부품 받음', '교체': '현장 교체 완료', '반납': '불량 부품 발송', '종결': '처리 끝' };
  const DEFAULT_RETURN_DAYS = 10;

  const today = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; };
  const addDays = (ds, n) => { const d = new Date(ds + 'T00:00:00'); d.setDate(d.getDate() + n); return FS.localDate(d); };
  const dayDiff = ds => Math.round((new Date(ds + 'T00:00:00') - today()) / 86400000);

  // 이 부품의 다음 단계 (반납 불필요면 교체 → 종결)
  function next(p) {
    const st = p.status || '요청';
    if (st === '교체' && p.return_required === false) return '종결';
    const i = STAGES.indexOf(st);
    return i >= 0 && i < STAGES.length - 1 ? STAGES[i + 1] : null;
  }
  function deadline(p) {
    const replaced = p.dates && p.dates['교체'];
    if (p.return_required === false || !replaced) return null;
    return addDays(replaced, Number(p.return_days ?? DEFAULT_RETURN_DAYS));
  }
  // 반납 대기(교체 끝, 아직 발송 전) 상태의 기한 표시. {d, cls:'over'|'soon'|'', text}
  function due(p) {
    if ((p.status || '요청') !== '교체') return null;
    const dl = deadline(p);
    if (!dl) return null;
    const d = dayDiff(dl);
    return { d, date: dl, cls: d < 0 ? 'over' : d <= 3 ? 'soon' : '',
             text: d < 0 ? `반납 ${-d}일 지남` : d === 0 ? '오늘 반납' : `반납 D-${d}` };
  }
  const isOpen = p => (p.status || '요청') !== '종결';

  // 단계 점 5개 (지난 단계 채움)
  function stepsHtml(p) {
    const st = p.status || '요청';
    const cur = STAGES.indexOf(st);
    return `<span class="pt-steps" aria-label="단계 ${FS.esc(st)}">${STAGES.map((s, i) => {
      const skip = s === '반납' && p.return_required === false;
      return `<span class="pt-step${i <= cur ? ' on' : ''}${i === cur ? ' cur' : ''}${skip ? ' skip' : ''}" title="${s}${p.dates?.[s] ? ' ' + p.dates[s] : ''}"></span>`;
    }).join('')}</span>`;
  }

  // 한 단계 진행 (날짜 자동 기록). 오프라인이어도 바로 반영
  async function advance(id, list) {
    const p = (list || []).find(x => x.id === id);
    if (!p) return;
    const n = next(p);
    if (!n) return;
    if (n === '교체' && !p.old_sn && !p.new_sn && p.return_required !== false) {
      // S/N은 선택이지만 반납 라벨 확인에 필요하니 한 번 상기
      if (!await Dialog.confirm('불량·새 부품 S/N이 비어 있습니다.\n그대로 교체 완료로 표시할까요? (나중에 수정에서 입력 가능)')) { openModal(id, null, list); return; }
    }
    const date = FS.localDate();
    FS.updateNow('parts', id, { status: n, [`dates.${n}`]: date });
    FS.audit('수정', '부품', id, p.name, `${p.status || '요청'} → ${n}${p.asset_host ? ' · ' + p.asset_host : ''}`);
    p.status = n; p.dates = { ...(p.dates || {}), [n]: date };
    const dl = n === '교체' ? deadline(p) : null;
    Toast.success(`'${p.name}' ${n}${dl ? ` — 반납 기한 ${FS.formatDate(dl)}` : ''}`);
    document.dispatchEvent(new CustomEvent('parts-changed'));
  }

  // ── 등록·수정 창 (body에 한 번 만들어 두고 재사용) ──
  let modal = null, editId = null, preset = null, editList = [];
  function ensureModal() {
    if (modal) return modal;
    modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.id = 'part-modal';
    modal.style.display = 'none';
    modal.innerHTML = `
      <div class="modal" style="max-width:560px;">
        <div class="modal-header"><h3 id="pt-m-title">부품 추가</h3><button class="modal-close" data-close>×</button></div>
        <div class="modal-body">
          <div id="pt-m-link" class="pt-m-link"></div>
          <div class="form-group"><label class="form-label">부품 *</label><input type="text" class="form-input" id="pt-name" placeholder="예: 3.84TB NVMe SSD, PSU 2400W" autocomplete="off"></div>
          <div class="form-row">
            <div class="form-group"><label class="form-label">P/N</label><input type="text" class="form-input pt-mono" id="pt-pn" autocomplete="off" autocapitalize="off" spellcheck="false"></div>
            <div class="form-group"><label class="form-label">FRU</label><input type="text" class="form-input pt-mono" id="pt-fru" autocomplete="off" autocapitalize="off" spellcheck="false"></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label class="form-label">벤더 RMA 케이스번호</label><input type="text" class="form-input pt-mono" id="pt-case" autocomplete="off" autocapitalize="off" spellcheck="false"></div>
            <div class="form-group"><label class="form-label">수량</label><input type="number" class="form-input" id="pt-qty" min="1" value="1" inputmode="numeric"></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label class="form-label">새 부품 S/N</label><input type="text" class="form-input pt-mono" id="pt-new-sn" autocomplete="off" autocapitalize="off" spellcheck="false"></div>
            <div class="form-group"><label class="form-label">불량 부품 S/N</label><input type="text" class="form-input pt-mono" id="pt-old-sn" autocomplete="off" autocapitalize="off" spellcheck="false"></div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">불량 부품 반납</label>
              <select class="form-select" id="pt-return">
                <option value="1">반납 필요 (RMA)</option>
                <option value="0">반납 없음 (구매·재고)</option>
              </select>
            </div>
            <div class="form-group"><label class="form-label">반납 기한 (교체 후 일수)</label><input type="number" class="form-input" id="pt-return-days" min="0" inputmode="numeric"></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label class="form-label">반납 운송장</label><input type="text" class="form-input pt-mono" id="pt-tracking" autocomplete="off"></div>
            <div class="form-group">
              <label class="form-label">단계</label>
              <select class="form-select" id="pt-status">${STAGES.map(s => `<option value="${s}">${s} — ${STAGE_HINT[s]}</option>`).join('')}</select>
            </div>
          </div>
          <div class="form-group"><label class="form-label">교체일</label><input type="date" class="form-input" id="pt-replaced"></div>
          <div class="form-group"><label class="form-label">메모</label><textarea class="form-textarea" id="pt-memo" rows="2"></textarea></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-danger" id="pt-del" style="margin-right:auto;">삭제</button>
          <button class="btn" data-close>취소</button>
          <button class="btn btn-primary" id="pt-save">저장</button>
        </div>
      </div>`;
    document.body.appendChild(modal);
    const close = () => { modal.style.display = 'none'; editId = null; };
    modal.addEventListener('click', e => { if (e.target === modal || e.target.closest('[data-close]')) close(); });
    modal.querySelector('#pt-save').onclick = save;
    modal.querySelector('#pt-del').onclick = del;
    modal.querySelector('#pt-return').onchange = e => { modal.querySelector('#pt-return-days').disabled = e.target.value === '0'; };
    return modal;
  }
  const $ = id => modal.querySelector('#' + id);

  // id: 수정할 부품 (없으면 새로), link: 새 부품의 티켓·장비 연결 {ticket_id, ticket_title, customer_id, asset_id, asset_host}
  function openModal(id, link, list) {
    ensureModal();
    editList = list || editList;
    const p = id ? editList.find(x => x.id === id) : null;
    if (id && !p) { Toast.error('이미 삭제된 항목입니다'); return; }
    editId = id || null;
    preset = p ? null : (link || {});
    const src = p || {};
    const L = p || preset;
    $('pt-m-title').textContent = p ? '부품 수정' : '부품 추가';
    $('pt-m-link').innerHTML = [L.ticket_title ? `티켓 <b>${FS.esc(L.ticket_title)}</b>` : '', L.asset_host ? `장비 <b class="mono">${FS.esc(L.asset_host)}</b>` : '']
      .filter(Boolean).join(' · ') || '<span class="text-hint">연결된 티켓 없음</span>';
    $('pt-name').value = src.name || '';
    $('pt-pn').value = src.pn || '';
    $('pt-fru').value = src.fru || '';
    $('pt-case').value = src.case_no || '';
    $('pt-qty').value = src.qty || 1;
    $('pt-new-sn').value = src.new_sn || '';
    $('pt-old-sn').value = src.old_sn || '';
    $('pt-return').value = src.return_required === false ? '0' : '1';
    $('pt-return-days').value = src.return_days ?? DEFAULT_RETURN_DAYS;
    $('pt-return-days').disabled = src.return_required === false;
    $('pt-tracking').value = src.tracking || '';
    $('pt-status').value = src.status || '요청';
    $('pt-replaced').value = src.dates?.['교체'] || '';
    $('pt-memo').value = src.memo || '';
    $('pt-del').style.display = p ? '' : 'none';
    modal.style.display = 'flex';
    if (!p) $('pt-name').focus();
  }

  function save() {
    const name = $('pt-name').value.trim();
    if (!name) { Toast.error('부품을 입력하세요'); $('pt-name').focus(); return; }
    const status = $('pt-status').value;
    const old = editId ? editList.find(x => x.id === editId) : null;
    const dates = { ...(old?.dates || {}) };
    if (!dates[status]) dates[status] = FS.localDate();   // 단계를 직접 바꾼 경우에도 날짜 남김
    const replaced = $('pt-replaced').value;
    if (replaced) dates['교체'] = replaced; else if (STAGES.indexOf(status) < 2) delete dates['교체'];
    const data = {
      name, pn: $('pt-pn').value.trim(), fru: $('pt-fru').value.trim(), case_no: $('pt-case').value.trim(),
      qty: Math.max(1, parseInt($('pt-qty').value) || 1),
      new_sn: $('pt-new-sn').value.trim(), old_sn: $('pt-old-sn').value.trim(),
      return_required: $('pt-return').value === '1',
      return_days: Math.max(0, parseInt($('pt-return-days').value) || 0),
      tracking: $('pt-tracking').value.trim(), memo: $('pt-memo').value.trim(),
      status, dates,
    };
    if (editId) {
      FS.updateNow('parts', editId, data);
      FS.audit('수정', '부품', editId, name, old?.asset_host || '');
      Object.assign(old, data);
    } else {
      const id = FS.addNow('parts', { ...data, ...preset, ...FS.creator() });
      FS.audit('등록', '부품', id, name, preset.asset_host || '');
    }
    modal.style.display = 'none';
    Toast.success(editId ? '저장되었습니다' : '부품을 추가했습니다');
    editId = null;
    document.dispatchEvent(new CustomEvent('parts-changed'));
  }

  async function del() {
    const p = editList.find(x => x.id === editId);
    if (!p || !await Dialog.confirm(`'${p.name}' 부품 기록을 삭제하시겠습니까?`, true)) return;
    FS.remove('parts', p.id).catch(e => Toast.error('삭제 실패: ' + (e.code || e.message)));
    FS.audit('삭제', '부품', p.id, p.name, p.asset_host || '');
    modal.style.display = 'none';
    editId = null;
    Toast.success('삭제되었습니다');
  }

  return { STAGES, STAGE_HINT, next, deadline, due, isOpen, stepsHtml, advance, openModal };
})();
